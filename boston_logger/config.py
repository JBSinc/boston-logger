from configular import Settings
from configular.environ_loader import EnvironLoader

_defaults = {
    "ENABLE_OUTBOUND_REQUEST_LOGGING": True,
    "ENABLE_LOGGING_MIDDLEWARE": True,
    "ENABLE_SENSITIVE_PATHS_PROCESSOR": False,
    "ENABLE_REQUESTS_LOGGING": False,
    "MAX_VERBOSE_OUTPUT_LENGTH": 500,
    "MAX_SUMO_DATA_TO_LOG": 0,  # Do not limit Sumo output, by default
    "SUMO_METADATA": {},
    "MIDDLEWARE_BLOCKLIST": ["admin:index", "swagger-docs"],
    "LOGGER_NAME": "boston_logger",
    "LOG_RESPONSE_CONTENT": False,
    "PREFER_TEXT_FALLBACK_MASKING": False,
    "SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS": False,
}

config = Settings(defaults=_defaults, prefix="BOSTON_LOGGER", loaders=[EnvironLoader])

if config.ENABLE_REQUESTS_LOGGING:
    from . import requests_monkey_patch  # noqa: F401

if not isinstance(config.MIDDLEWARE_BLOCKLIST, list):
    raise Exception("MIDDLEWARE_BLOCKLIST must be a list.")
