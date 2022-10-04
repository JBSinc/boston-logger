from datetime import datetime
from time import sleep
from unittest.mock import MagicMock

import pytest
import requests

from boston_logger.context_managers import (
    RequestDirection,
    RequestEdge,
    RequestLogContext,
    SensitivePathContext,
    log_incoming_request_event,
    log_outgoing_request_event,
    sanitize_request_data,
)
from boston_logger.sensitive_paths import (
    MASK_STRING,
    SensitivePaths,
    add_mask_processor,
    remove_mask_processor,
    sanitize_data,
)

payload = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3",
}


class Fake(object):
    pass


class ExceptionContext:
    def __init__(self):
        self.exc_info = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exc_info = (exc_type, exc_val, exc_tb)
        return True


class TestSensitivePathContext:
    @pytest.fixture(autouse=True, scope="class")
    def setup(self, class_mocker):
        class_mocker.patch(
            "boston_logger.config.config.ENABLE_SENSITIVE_PATHS_PROCESSOR", True
        )
        add_mask_processor("Pat1", SensitivePaths("key1"))
        add_mask_processor("Pat2", SensitivePaths("key2"))
        add_mask_processor("Pat3", SensitivePaths("key3"))
        yield
        remove_mask_processor("Pat1")
        remove_mask_processor("Pat2")
        remove_mask_processor("Pat3")

    def test_request_post_body(self):
        logger = MagicMock()
        start = datetime.now()
        end = datetime.now()

        s = requests.Session()
        request = s.prepare_request(
            requests.Request("POST", "https://example.com", data={"key1": "hide"})
        )

        with SensitivePathContext("Pat1"):
            log_outgoing_request_event(
                start=start,
                end=end,
                logger=logger,
                request=request,
            )

        # First positional is the message
        assert (
            logger.info.call_args[0][0] == "OUTGOING (end): POST https://example.com/"
        )
        # kwargs extra meets expectations
        extra = logger.info.call_args[1]["extra"]
        # Masked and form encoded
        assert extra["request"]["data"] == "key1=%2A%2A%2A+masked+%2A%2A%2A"

    def test_request_post_body_json(self):
        logger = MagicMock()
        start = datetime.now()
        end = datetime.now()

        s = requests.Session()
        request = s.prepare_request(
            requests.Request(
                "POST",
                "https://example.com",
                json={"key1": "hide"},
            )
        )

        with SensitivePathContext("Pat1"):
            log_outgoing_request_event(
                start=start,
                end=end,
                logger=logger,
                request=request,
            )

        # First positional is the message
        assert (
            logger.info.call_args[0][0] == "OUTGOING (end): POST https://example.com/"
        )
        # kwargs extra meets expectations
        extra = logger.info.call_args[1]["extra"]
        # Masked and form encoded
        assert extra["request"]["data"]["key1"] == MASK_STRING

    def test_path_context_single(self):
        with SensitivePathContext("Pat1"):
            sanitized = sanitize_data(payload)
            assert sanitized["key1"] == MASK_STRING
            assert sanitized["key2"] != MASK_STRING
            assert sanitized["key3"] != MASK_STRING

    def test_path_context_list(self):
        with SensitivePathContext(["Pat1", "Pat2"]):
            sanitized = sanitize_data(payload)
            assert sanitized["key1"] == MASK_STRING
            assert sanitized["key2"] == MASK_STRING
            assert sanitized["key3"] != MASK_STRING

    def test_path_context_nested(self):
        with SensitivePathContext("Pat1"):
            sanitized = sanitize_data(payload)
            assert sanitized["key1"] == MASK_STRING
            assert sanitized["key2"] != MASK_STRING
            assert sanitized["key3"] != MASK_STRING
            with SensitivePathContext("Pat2"):
                sanitized = sanitize_data(payload)
                assert sanitized["key1"] == MASK_STRING
                assert sanitized["key2"] == MASK_STRING
                assert sanitized["key3"] != MASK_STRING

    def test_sanitize_request_data_dict(self):
        request = Fake()
        request._apply_mask_processors = "Pat1"
        sanitized = sanitize_request_data(request, payload)
        assert sanitized["key1"] == MASK_STRING
        assert sanitized["key2"] != MASK_STRING
        assert sanitized["key3"] != MASK_STRING

    def test_sanitize_request_data_str_no_parse_no_mask(self, mocker):
        mocker.patch("boston_logger.config.config.PREFER_TEXT_FALLBACK_MASKING", False)
        request = Fake()
        data = "not a query string"
        sanitized = sanitize_request_data(request, data)
        assert sanitized == data

    def test_sanitize_request_data_str_no_parse_mask(self, mocker):
        mocker.patch("boston_logger.config.config.PREFER_TEXT_FALLBACK_MASKING", True)
        request = Fake()
        data = "not a query string"
        sanitized = sanitize_request_data(request, data)
        assert sanitized == MASK_STRING

    def test_sanitize_request_data_str_parse(self):
        request = Fake()
        request._apply_mask_processors = "Pat1"
        data = "key1=hide&key2=show"
        sanitized = sanitize_request_data(request, data)
        # Masked and encoded
        assert sanitized == "key1=%2A%2A%2A+masked+%2A%2A%2A&key2=show"

    def test_sanitize_request_data_absurd(self):
        request = Fake()
        sanitized = sanitize_request_data(request, [])
        # Not a dict or str, just gets returned
        assert sanitized == []


@pytest.mark.parametrize(
    "test_func",
    [
        log_incoming_request_event,
        log_outgoing_request_event,
    ],
)
class TestRequestLogContext:
    def test_defaults(self, test_func):
        # For coverage of config logger lookup
        with RequestLogContext(make_log_func=test_func):
            pass

    def test_logger(self, test_func):
        logger = MagicMock()

        with RequestLogContext(
            logger=logger,
            make_log_func=test_func,
        ):
            pass

        # Log start and end
        assert logger.info.call_count == 2


class Test_log_request_event:
    @pytest.mark.parametrize(
        "test_func",
        [
            log_incoming_request_event,
            log_outgoing_request_event,
        ],
    )
    def test_info(self, test_func):
        logger = MagicMock()
        start = datetime.now()
        sleep(0.01)
        end = datetime.now()
        delta = int((end - start).total_seconds() * 1000)

        test_func(
            start=start,
            end=end,
            logger=logger,
        )

        logger.info.assert_called_once()
        assert logger.info.call_args[1]["extra"]["response_time_ms"] == delta
        logger.error.assert_not_called()

    @pytest.mark.parametrize(
        "test_func",
        [
            log_incoming_request_event,
            log_outgoing_request_event,
        ],
    )
    def test_error(self, test_func):
        logger = MagicMock()
        start = datetime.now()
        end = datetime.now()

        with ExceptionContext() as context:
            raise ValueError("I don't like it.")

        # WHEN logging an Exception
        test_func(
            start=start,
            end=end,
            logger=logger,
            exc_info=context.exc_info,
        )

        # THEN exc_info gets passed to logger.error
        logger.error.assert_called_once()
        assert logger.error.call_args[1]["exc_info"] == context.exc_info
        # AND logger.info is not called
        logger.info.assert_not_called()

    def test_incoming_start(self):
        logger = MagicMock()
        start = datetime.now()
        end = datetime.now()
        edge = RequestEdge.START
        direction = RequestDirection.INCOMING

        request = Fake()
        request.method = ("GET",)
        request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_HEADER": "orly"}
        request.scheme = "https"
        request.path = "/index/"
        request.POST = {}
        request.GET = {}

        # WHEN logging an INCOMING request
        log_incoming_request_event(
            start=start,
            end=end,
            logger=logger,
            request=request,
            edge=edge,
        )

        # First positional is the message
        assert logger.info.call_args[0][0] == "INCOMING (start): ('GET',) /index/"
        # kwargs extra meets expectations
        extra = logger.info.call_args[1]["extra"]
        assert extra["direction"] == direction
        assert extra["edge"] == edge

    def test_incoming_end(self):
        logger = MagicMock()
        start = datetime.now()
        end = datetime.now()
        edge = RequestEdge.END
        direction = RequestDirection.INCOMING

        request = Fake()
        request.method = ("GET",)
        request.body = "Some Payload"
        request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_HEADER": "orly"}
        request.scheme = "https"
        request.path = "/index/"
        request.POST = {}
        request.GET = {}

        # WHEN logging an INCOMING request
        log_incoming_request_event(
            start=start,
            end=end,
            logger=logger,
            request=request,
            edge=edge,
        )

        # First positional is the message
        assert logger.info.call_args[0][0] == "INCOMING (end): ('GET',) /index/"
        # kwargs extra meets expectations
        extra = logger.info.call_args[1]["extra"]
        assert extra["direction"] == direction
        assert extra["edge"] == edge
