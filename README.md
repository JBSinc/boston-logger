# Boston Logger

Smaht logging solutions for Django applications.

## Basic Usage

Add the `RequestResponseLoggerMiddleware` middleware in your Django project's
settings file to log all request/responses that Django handles.

Import the `requests_monkey_patch` (or set the `ENABLE_REQUESTS_LOGGING` flag to
`True` and add the middleware) to log all requests made through the `requests`
library.

## For settings file

If you want to configure in settings.py start with this:

```
BOSTON_LOGGER = {
    "ENABLE_OUTBOUND_REQUEST_LOGGING": True,
    "ENABLE_LOGGING_MIDDLEWARE": True,
    "ENABLE_SENSITIVE_PATHS_PROCESSOR": False,
    "ENABLE_REQUESTS_LOGGING": True,  # Enable the requests monkey patch
    "MAX_VERBOSE_OUTPUT_LENGTH": 500,
    "MAX_SUMO_DATA_TO_LOG": 0,  # Do not limit Sumo output, by default
    "SUMO_METADATA": {},
    "MIDDLEWARE_BLOCKLIST": ["admin:index", "swagger-docs"],
    "LOGGER_NAME": "boston_logger",
    "LOG_RESPONSE_CONTENT": False,
    "PREFER_TEXT_FALLBACK_MASKING": False,
    "SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS": False,
}
```

```
LOGGING = {
    'disable_existing_loggers': True,
    'version': 1,
    'formatters': {
        'sumo_formatter': {
            '()': 'boston_logger.logger.SumoFormatter',
        },
        'smart_formatter': {
            '()': 'boston_logger.logger.SmartFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'smart_formatter',
        },
        'requests': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'sumo_formatter',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
        },
        'boston_logger': {
            'handlers': ['requests'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'DEBUG'),
            'propagate': False,
        },
    },
}
```

## All config options, with defaults

- `ENABLE_OUTBOUND_REQUEST_LOGGING`: True - Requests lib requests will be captured.
- `ENABLE_LOGGING_MIDDLEWARE`: True - The middleware will log START/END events
  for incoming requests.
- `ENABLE_SENSITIVE_PATHS_PROCESSOR`: False - `sensitive_paths.SensitivePaths` objects will mask data
- `ENABLE_REQUESTS_LOGGING`: False - Monkey patches requests lib so
  `ENABLE_OUTBOUND_REQUEST_LOGGING` is possible
- `MAX_VERBOSE_OUTPUT_LENGTH`: 500 - Character length for request, header, and
  response data in SmartFormatter (console logs).
- `MAX_SUMO_DATA_TO_LOG`: 0 - If greater than zero, truncate Sumo payloads to
  this size
- `SUMO_METADATA`: {} - Included in all sumo logs, good to configure your
  category.
- `MIDDLEWARE_BLOCKLIST`: [`admin:index`, `swagger-docs`] - Middleware will not
  log requests that match these named URLs.
- `LOGGER_NAME`: `boston_logger` - Default name of the logger that all request logs
  will be sent to.
- `LOG_RESPONSE_CONTENT`: False - Log the json responses the site is sending.
- `PREFER_TEXT_FALLBACK_MASKING`: False - If parsing text data to sanitize as a
  query string fails, mask the whole value.
- `SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS`: False - When True, the objects in a
  sensitve path will show keys, but all values will be masked. When False, the
  entire object will be replaced with the masked string.

## Filtering Sensitive Data

`ENABLE_SENSITIVE_PATHS_PROCESSOR` is set to `False` by default. If enabled, you
must define filtering rules.

One way rules can be defined is on the request via JSON in the
`_apply_mask_processors` key. Setting this to `ALL` will mask all data. There
are other options if you interact with the `SensitivePaths` class via the
`add_mask_processor` method.

## Reducing Log Size

`MAX_SUMO_DATA_TO_LOG` tries to ensure that Sumo log messages don't get beyond
a certain size. If it is set to a non-zero value, we use it as a message
length limit. If the message is too long, we truncate the response data.


## Middleware

If you're using the `RequestResponseMiddleware` in your Django application, you
can override `BOSTON_LOGGER.MIDDLEWARE_BLOCKLIST` in your settings.py if you
don't want to generate logs for given URLs. The argument expected is a list of
URLs names. By default it won't log admin and swagger requests.


## Log JSONResponses

`LOG_RESPONSE_CONTENT` is set to `False` by default. Setting it to `True` will
add JSON data to the log responses of `django.JsonResponse`.


## Adding Notes

Boston Logger allows you to add custom notes data to log messages.  This can be
any type of data that is JSON serializable (recommended to be a string or simple
dictionary).

To add notes to an `INCOMING` request (i.e. one handled by the middleware),
simply add an attribute to the WSGI request object called `_request_notes`; the
`SumoFormatter` will include it in the JSON log output.

**Note** that if you are using Django REST Framework, the incoming `request`
object in your `ViewSet` or view method(s) will be an abstraction of the
original WSGI request.  You'll need to set the attribute on `request._request`,
e.g.:

```python
setattr(request._request, '_request_notes', 'Some extra log data here.')
```

To add notes to `OUTGOING` requests (i.e. you're using the `requests` library to
send an internal request to another service/system), it's recommend you leverage
the `requests_monkey_patch` functionality described above.  This will allow you
to specify a `notes` keyword argument which will attach your notes metadata onto
the `OUTGOING` log message emitted by the `SumoFormatter`:

```python
requests.post(url, data, notes='Some extra log data here.')
```

Also, remember that you can always use the `RequestLogContext` and attach your
notes that way:

```python
with RequestLogContext(method='post', notes='Some extra log data here.') as log_context:
    response = requests.post(url, data)
    request = response.request

    log_context.request = request
    log_context.response = response
```
