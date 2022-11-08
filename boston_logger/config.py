from configular import Settings
from configular.environ_loader import EnvironLoader

_defaults = {
    "ENABLE_OUTBOUND_REQUEST_LOGGING": True,
    "ENABLE_LOGGING_MIDDLEWARE": True,
    "ENABLE_SENSITIVE_PATHS_PROCESSOR": False,
    "ENABLE_REQUESTS_LOGGING": False,
    "MAX_VERBOSE_OUTPUT_LENGTH": 500,
    "MAX_JSON_DATA_TO_LOG": 0,  # Do not limit json output, by default
    "MIDDLEWARE_BLOCKLIST": ["admin:index", "swagger-docs"],
    "LOGGER_NAME": "boston_logger",
    "LOG_RESPONSE_CONTENT": False,
    "PREFER_TEXT_FALLBACK_MASKING": False,
    "SHOW_NESTED_KEYS_IN_SENSITIVE_PATHS": False,
}


class BlSettings(Settings):
    @property
    def request_logging_enabled(self):
        try:
            return str(self.ENABLE_REQUESTS_LOGGING).lower()[0] in ["y", "t"]
        except Exception:
            return False

    def reconfigure(self, *args, **kwargs):
        super().reconfigure(*args, **kwargs)

        if self.request_logging_enabled:
            from . import requests_monkey_patch  # noqa: F401

        if not isinstance(self.MIDDLEWARE_BLOCKLIST, list):
            raise ValueError("MIDDLEWARE_BLOCKLIST must be a list.")


config = BlSettings(defaults=_defaults, prefix="BOSTON_LOGGER", loaders=[EnvironLoader])
