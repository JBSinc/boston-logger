import json
import logging

from boston_logger.context_managers import RequestDirection, RequestEdge
from boston_logger.logger import SmartFormatter, SumoFilter, SumoFormatter

sumo_filter = SumoFilter()


class Fake(object):
    pass


def test_filter_dumb():
    # All non-smart logs go to sumo
    assert sumo_filter.filter(Fake()) is True


def test_filter_smart_start():
    record = Fake()
    record.smart = True
    record.edge = RequestEdge.START

    assert sumo_filter.filter(record) is False


def test_filter_smart_end():
    record = Fake()
    record.smart = True
    record.edge = RequestEdge.END

    # Smart logs only go to sumo on the END edge
    assert sumo_filter.filter(record) is True


def test_sumo_not_smart_format():
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
    formatter = SumoFormatter()

    fmt = json.loads(formatter.format(record))
    # Non-smart logs only have msg and extra
    assert set(fmt.keys()) == set(["msg", "key", "_sumo_metadata"])


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
