import json
from datetime import date, datetime
from decimal import Decimal
from logging import Filter, Formatter


class RequestEdgeEndFilter(Filter):
    def filter(self, record):
        from .context_managers import RequestEdge

        if not getattr(record, "smart", False):
            # non-smart logs always get recorded
            return True

        # Smart logs only get recorded on END
        return record.edge == RequestEdge.END


class ObjectTypeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return {
                # sort values to make reading logs easier as a user
                "value": sorted(obj),
                "type": "set",
            }

        if isinstance(obj, datetime):
            return {
                "value": str(obj),
                "type": "datetime",
            }

        if isinstance(obj, date):
            return {
                "value": str(obj),
                "type": "date",
            }

        if isinstance(obj, Decimal):
            return {
                "value": str(obj),
                "type": "Decimal",
            }

        return super().default(obj)


class JsonFormatter(Formatter):
    def __init__(self, *args, **kwargs):
        self.default_extra = kwargs.pop("default_extra", {})
        super().__init__(*args, **kwargs)

    def format(self, record):
        from .config import config

        if getattr(record, "smart", False):
            log_data = {
                **self.default_extra,
                "msg": super().format(record),
                "start_time": getattr(record, "start_time", ""),
                "end_time": getattr(record, "end_time", ""),
                "response_time_ms": getattr(record, "response_time_ms", ""),
                "request": record.request,
                "response": getattr(record, "response", None),
                "notes": getattr(record, "notes", None),
                **getattr(record, "extra", {}),
            }
        else:
            log_data = {
                **self.default_extra,
                "msg": super().format(record),
                **getattr(record, "extra", {}),
            }

        resp = json.dumps(log_data, cls=ObjectTypeEncoder)
        if config.MAX_JSON_DATA_TO_LOG and len(resp) > config.MAX_JSON_DATA_TO_LOG:
            log_data["max_data_exceeded"] = True
            truncate_length = config.MAX_JSON_DATA_TO_LOG - 50
            response_obj = log_data.get("response")
            if response_obj and truncate_length > 0:
                response_data = str(response_obj.get("data", ""))
                if len(response_data) > truncate_length:
                    # Update mutatable resonse_obj inside mutatable log_data
                    response_obj["data"] = (
                        response_data[:truncate_length] + " **TRUNCATED**"
                    )

            resp = json.dumps(log_data, cls=ObjectTypeEncoder)

        return resp


class SmartFormatter(Formatter):
    def limited_size_repr(self, data, length):
        data = repr(data)
        if len(data) > length:
            data = data[:length] + "..."
        return data

    def format(self, record):
        from .context_managers import RequestDirection, RequestEdge

        log_msg = [super().format(record)]

        if not getattr(record, "smart", False):
            return log_msg[0]

        if (
            record.edge == RequestEdge.START
            and record.direction == RequestDirection.OUTGOING
        ):
            pass
        else:
            from .config import config

            req = record.request

            data = req.get("data")
            if data is not None:
                data = self.limited_size_repr(data, config.MAX_VERBOSE_OUTPUT_LENGTH)
                log_msg.append(f"  Request Data: {data}")

            headers = req.get("headers")
            if headers is not None:
                headers = self.limited_size_repr(
                    headers, config.MAX_VERBOSE_OUTPUT_LENGTH
                )
                log_msg.append(f"  Request Headers: {headers}")

            resp = getattr(record, "response", None)
            if resp is not None:
                data = resp.get("data")
                if data is None:
                    data = "(empty)"
                else:
                    data = self.limited_size_repr(
                        data, config.MAX_VERBOSE_OUTPUT_LENGTH
                    )
                log_msg.append(f"  Response Data: {data}")

            log_msg.append("\n")

        return "\n".join(log_msg)
