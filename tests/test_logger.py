import json
import logging

from boston_logger.context_managers import RequestDirection, RequestEdge
from boston_logger.logger import JsonFormatter, RequestEdgeEndFilter, SmartFormatter

request_edge_filter = RequestEdgeEndFilter()


class Fake(object):
    pass


not_smart_keys = {
    "timestamp",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msg",
    "loggerName",
}


smart_keys = not_smart_keys | {
    "end_time",
    "notes",
    "request",
    "response",
    "response_time_ms",
    "start_time",
}


def test_filter_dumb():
    # All non-smart logs pass
    assert request_edge_filter.filter(Fake()) is True


def test_filter_smart_start():
    record = Fake()
    record.smart = True
    record.edge = RequestEdge.START

    assert request_edge_filter.filter(record) is False


def test_filter_smart_end():
    record = Fake()
    record.smart = True
    record.edge = RequestEdge.END

    # Smart logs only pass on the END edge
    assert request_edge_filter.filter(record) is True


def test_json_smart_format():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": True,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
        }
    )
    formatter = JsonFormatter()

    fmt = json.loads(formatter.format(record))
    # Smart logs have expected keys, including from extra
    assert set(fmt.keys()) == smart_keys | {"key"}


def test_json_smart_format_default_extra():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": True,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
        }
    )
    formatter = JsonFormatter(default_extra={"_extra_key": "some value"})

    fmt = json.loads(formatter.format(record))
    # Smart logs have expected keys, including from extra
    assert set(fmt.keys()) == smart_keys | {"key", "_extra_key"}


def test_json_not_smart_format():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": False,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
        }
    )
    formatter = JsonFormatter()

    fmt = json.loads(formatter.format(record))
    # Non-smart logs only have msg and extra
    assert set(fmt.keys()) == not_smart_keys | {"key"}


def test_json_not_smart_format_default_extra():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": False,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
        }
    )
    formatter = JsonFormatter(default_extra={"_extra_key": "some value"})

    fmt = json.loads(formatter.format(record))
    # Non-smart logs only have msg, extra, and default_extra
    assert set(fmt.keys()) == not_smart_keys | {"key", "_extra_key"}


def test_smart_format_not_smart():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": False,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
        }
    )
    formatter = SmartFormatter()

    fmt = formatter.format(record)
    # Not smart is just the msg
    assert fmt == long_msg


def test_smart_format_start_outgoing():
    long_msg = "TEST " * 100

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": True,
            "response": {"data": long_msg},
            "extra": {"key": "value"},
            "edge": RequestEdge.START,
            "direction": RequestDirection.OUTGOING,
        }
    )
    formatter = SmartFormatter()

    fmt = formatter.format(record)
    # Start/Outgoing is just msg
    assert fmt == long_msg
