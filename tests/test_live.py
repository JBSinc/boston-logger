import os
from logging.config import dictConfig

import pytest
import requests

from boston_logger.config import config

# from boston_logger import requests_monkey_patch  # NOQA
from boston_logger.context_managers import (
    RequestDirection,
    RequestEdge,
    SensitivePathContext,
)
from boston_logger.sensitive_paths import (
    MASK_STRING,
    SensitivePaths,
    add_mask_processor,
    remove_mask_processor,
)

dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {"": {"level": "INFO", "propagate": True}},
    }
)


@pytest.fixture(autouse=True, scope="module")
def setup(module_mocker):
    module_mocker.patch(
        "boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True
    )

    # Test the reconfigure feature triggering monkey patch
    orig_request = requests.request
    assert config.ENABLE_REQUESTS_LOGGING is False
    os.environ["BOSTON_LOGGER_ENABLE_REQUESTS_LOGGING"] = "yes"
    config.reconfigure()
    assert config.request_logging_enabled is True
    assert requests.request is not orig_request
    yield
    os.environ.pop("BOSTON_LOGGER_ENABLE_REQUESTS_LOGGING")
    config.reconfigure()
    # The monkey patch can not be undone, use `ENABLE_OUTBOUND_REQUEST_LOGGING`
    # To avoid logging after patching
    assert requests.request is not orig_request


def test_csv_api(caplog):
    requests.get("https://ip4.me/api/")
    assert "OUTGOING (start): GET https://ip4.me/api/" in caplog.text
    assert "OUTGOING (end): GET https://ip4.me/api/ (200)" in caplog.text


def test_csv_api_nolog(caplog, mocker):
    mocker.patch("boston_logger.config.config.ENABLE_OUTBOUND_REQUEST_LOGGING", False)
    requests.get("https://ip4.me/api/")
    assert len(caplog.records) == 0


def test_json_api(caplog):
    add_mask_processor("Facts", SensitivePaths("fact"))

    with SensitivePathContext("Facts"):
        requests.get("https://catfact.ninja/fact")

    remove_mask_processor("Facts")

    assert "OUTGOING (start): GET https://catfact.ninja/fact" in caplog.text
    assert "OUTGOING (end): GET https://catfact.ninja/fact (200)" in caplog.text
    # Two logs happened
    assert len(caplog.records) == 2

    expected_start_record = {
        "direction": RequestDirection.OUTGOING,
        "edge": RequestEdge.START,
        "end_time": None,
        "exc_info": None,
        "exc_text": None,
        "filename": "context_managers.py",
        "funcName": "log_outgoing_request_event",
        "levelname": "INFO",
        "message": "OUTGOING (start): GET https://catfact.ninja/fact",
        "module": "context_managers",
        "msg": "OUTGOING (start): GET https://catfact.ninja/fact",
        "name": "boston_logger",
        "notes": None,
        "request": {"method": "GET", "url": "https://catfact.ninja/fact"},
        "response": {},
        "response_time_ms": -1,
        "smart": True,
        "stack_info": None,
    }
    # all of expected_start_record is contained in the start log record
    assert expected_start_record.items() <= caplog.records[0].__dict__.items()

    expected_end_record = {
        "direction": RequestDirection.OUTGOING,
        "edge": RequestEdge.END,
        "exc_info": None,
        "exc_text": None,
        "filename": "context_managers.py",
        "funcName": "log_outgoing_request_event",
        "levelname": "INFO",
        "message": "OUTGOING (end): GET https://catfact.ninja/fact (200)",
        "module": "context_managers",
        "msg": "OUTGOING (end): GET https://catfact.ninja/fact (200)",
        "name": "boston_logger",
        "notes": None,
        "smart": True,
        "stack_info": None,
    }
    # all of expected_end_record is contained in the end log record
    assert expected_end_record.items() <= caplog.records[1].__dict__.items()

    expected_end_request = {
        "method": "GET",
        "path": "/fact",
        "url": "https://catfact.ninja/fact",
    }
    assert expected_end_request.items() <= caplog.records[1].request.items()

    # Masking works
    assert caplog.records[1].response["data"]["fact"] == MASK_STRING
