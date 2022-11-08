import json
import logging
from datetime import date, datetime
from decimal import Decimal

import pytest

from boston_logger.config import config
from boston_logger.logger import JsonFormatter, ObjectTypeEncoder


def test_format_limit():
    long_msg = "TEST " * 100

    config.MAX_JSON_DATA_TO_LOG = 500

    record = logging.makeLogRecord(
        {
            "msg": long_msg,
            "request": long_msg,
            "smart": True,
            "response": {"data": long_msg},
        }
    )
    formatter = JsonFormatter()

    fmt = formatter.format(record)
    fmt = json.loads(fmt)
    assert fmt["msg"] == long_msg
    assert fmt["request"] == long_msg

    # But because of the min 50, nothing get truncated
    config.MAX_JSON_DATA_TO_LOG = 5

    fmt = formatter.format(record)
    fmt = json.loads(fmt)
    assert fmt["max_data_exceeded"]

    # Trigger response truncation
    config.MAX_JSON_DATA_TO_LOG = 60

    fmt = formatter.format(record)
    fmt = json.loads(fmt)
    assert fmt["max_data_exceeded"]
    assert fmt["response"]["data"].endswith("**TRUNCATED**")

    # Unlimited
    config.MAX_JSON_DATA_TO_LOG = 0

    fmt = formatter.format(record)
    fmt = json.loads(fmt)
    assert fmt["msg"] == long_msg
    assert fmt["request"] == long_msg


@pytest.mark.parametrize(
    "obj,result",
    [
        (
            {2, 3, 1},
            {
                "value": [1, 2, 3],
                "type": "set",
            },
        ),
        (
            datetime(2021, 3, 4, 2, 30, 22),
            {
                "value": str(datetime(2021, 3, 4, 2, 30, 22)),
                "type": "datetime",
            },
        ),
        (
            date(2021, 3, 4),
            {
                "value": str(date(2021, 3, 4)),
                "type": "date",
            },
        ),
        (
            Decimal(1.5),
            {
                "value": str(Decimal(1.5)),
                "type": "Decimal",
            },
        ),
        (
            "String",
            {
                "value": "String",
                "type": None,
            },
        ),
        (
            3,
            {
                "value": 3,
                "type": None,
            },
        ),
    ],
)
def test_json_encoder(obj, result):
    resp = json.loads(json.dumps({"field": obj}, cls=ObjectTypeEncoder))
    if result["type"]:
        assert resp["field"]["value"] == result["value"]
        assert resp["field"]["type"] == result["type"]
    else:
        # Simple fields Don't get wrapped in a typing object
        assert resp["field"] == result["value"]
