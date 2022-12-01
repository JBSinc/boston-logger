from logging.config import dictConfig

import pytest
from django.test import Client

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


def test_middleware_disabled(caplog, mocker):
    mocker.patch("boston_logger.config.config.ENABLE_LOGGING_MIDDLEWARE", False)
    c = Client()
    c.get("/")
    assert len(caplog.records) == 0


def test_middleware_blocklist(caplog, mocker):
    mocker.patch("boston_logger.config.config.MIDDLEWARE_BLOCKLIST", ["index"])
    c = Client()
    c.get("/")
    # Blocking index, actually blocks everything, because BLOCKLIST entries are
    # reversed in the url conf, and then checked as prefixes
    c.get("/log_no_resp_data")
    assert len(caplog.records) == 0


@pytest.mark.parametrize(
    "LOG_RESPONSE_CONTENT, expected_response_data",
    [
        (
            False,
            {"status_code": 200},
        ),
        (
            True,
            {
                "status_code": 200,
                "data": {"obj1": {"key1": MASK_STRING}},
            },
        ),
    ],
)
def test_incoming_request(caplog, mocker, LOG_RESPONSE_CONTENT, expected_response_data):
    mocker.patch("boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True)

    mocker.patch(
        "boston_logger.config.config.LOG_RESPONSE_CONTENT", LOG_RESPONSE_CONTENT
    )

    add_mask_processor("Pat1", SensitivePaths("obj1/key1"))

    with SensitivePathContext("Pat1"):
        c = Client()
        c.get("/")

    remove_mask_processor("Pat1")

    assert len(caplog.records) == 2

    expected_start_record = {
        "direction": RequestDirection.INCOMING,
        "edge": RequestEdge.START,
        "end_time": None,
        "exc_info": None,
        "exc_text": None,
        "filename": "context_managers.py",
        "funcName": "log_incoming_request_event",
        "levelname": "INFO",
        "levelno": 20,
        "message": "INCOMING (start): GET /",
        "msg": "INCOMING (start): GET /",
        "name": "boston_logger",
        "notes": None,
        "response": {},
        "response_time_ms": -1,
        "smart": True,
        "stack_info": None,
    }
    # all of expected_start_record is contained in the start log record
    assert expected_start_record.items() <= caplog.records[0].__dict__.items()
    # Can't predict the pathname in all environments
    assert "pathname" in caplog.records[0].__dict__

    expected_start_request = {
        "data": {"raw_body": ""},
        "headers": {"HTTP_COOKIE": ""},
        "method": "GET",
        "path": "/",
        "remote_addr": "127.0.0.1",
        "url_scheme": "http",
    }
    assert expected_start_request.items() <= caplog.records[0].request.items()

    expected_end_record = {
        "direction": RequestDirection.INCOMING,
        "edge": RequestEdge.END,
        "exc_info": None,
        "exc_text": None,
        "filename": "context_managers.py",
        "funcName": "log_incoming_request_event",
        "levelname": "INFO",
        "levelno": 20,
        "message": "INCOMING (end): GET / (200)",
        "module": "context_managers",
        "msg": "INCOMING (end): GET / (200)",
        "name": "boston_logger",
        "notes": None,
        "smart": True,
        "stack_info": None,
    }
    # all of expected_end_record is contained in the end log record
    assert expected_end_record.items() <= caplog.records[1].__dict__.items()

    assert expected_response_data == caplog.records[1].response


@pytest.mark.parametrize(
    "LOG_RESPONSE_CONTENT",
    [
        False,
        True,
    ],
)
def test_incoming_request_no_data(caplog, mocker, LOG_RESPONSE_CONTENT):
    mocker.patch(
        "boston_logger.config.config.LOG_RESPONSE_CONTENT", LOG_RESPONSE_CONTENT
    )

    c = Client()
    c.get("/log_no_resp_data")

    expected_response_data = {
        "data": {"NOT_LOGGED": "_log_data == False"},
        "status_code": 200,
    }
    assert expected_response_data == caplog.records[1].response
