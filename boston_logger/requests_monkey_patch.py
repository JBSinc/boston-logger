import requests

original_request_method = requests.request


def logged_request(method, url, **kwargs):
    from .config import config

    notes = kwargs.pop("notes") if "notes" in kwargs else None

    if not config.ENABLE_OUTBOUND_REQUEST_LOGGING:
        return original_request_method(method, url, **kwargs)

    # TODO allow/block lists here for remote URLs

    from .context_managers import RequestLogContext, log_outgoing_request_event

    with RequestLogContext(
        method=method,
        url=url,
        make_log_func=log_outgoing_request_event,
    ) as log_context:
        response = original_request_method(method, url, **kwargs)
        request = response.request

        log_context.request = request
        log_context.response = response
        log_context.notes = notes

    return response


requests.api.request = logged_request
requests.request = logged_request
