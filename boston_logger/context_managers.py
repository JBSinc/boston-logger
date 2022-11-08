"""Context manager to wrap requests."""

import itertools
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Union
from urllib.parse import parse_qs, urlencode

from .sensitive_paths import MASK_STRING, sanitize_data

RequestDirection = Enum("RequestDirection", "INCOMING OUTGOING")
RequestEdge = Enum("RequestEdge", "START END")


# Probably not thread safe
class SensitivePathContext:
    _mask_names = []  # List[Set]

    def __init__(self, paths):
        # You probably didn't mean to pass a single name, but you can
        if isinstance(paths, str):
            paths = set([paths])
        SensitivePathContext._mask_names.append(set(paths))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        SensitivePathContext._mask_names.pop(-1)

    @classmethod
    def get_mask_names(cls):
        return set(itertools.chain(*cls._mask_names))


class RequestLogContext:
    def __init__(
        self,
        *,
        logger=None,
        request=None,
        request_data=None,
        notes=None,
        msg=None,
        method=None,
        url=None,
        direction=RequestDirection.OUTGOING,
        make_log_func,
    ):
        if logger is None:
            # Avoid importing config which might hit django/constance in global scope
            from .config import config

            self.logger = logging.getLogger(config.LOGGER_NAME)
        else:
            self.logger = logger

        self.start_time = datetime.now()
        self.response = None
        self.request = request
        self.request_data = request_data
        self.notes = notes
        self.msg = msg
        self.method = method
        self.url = url
        self.direction = direction
        self.make_log_func = make_log_func

    def __enter__(self):
        self.make_log_func(
            start=self.start_time,
            end=None,
            logger=self.logger,
            request=self.request,
            request_data=self.request_data,
            notes=self.notes,
            msg=self.msg,
            method=self.method,
            url=self.url,
            direction=self.direction,
            edge=RequestEdge.START,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()

        self.make_log_func(
            start=self.start_time,
            end=self.end_time,
            logger=self.logger,
            request=self.request,
            response=self.response,
            request_data=self.request_data,
            exc_info=(exc_type, exc_val, exc_tb) if exc_type else None,
            notes=self.notes,
            msg=self.msg,
            direction=self.direction,
            edge=RequestEdge.END,
        )


def calculate_response_time_ms(start_time: datetime, end_time: datetime):
    if not end_time:
        return -1

    return int((end_time - start_time).total_seconds() * 1000)


def sanitize_request_data(request, data: Union[dict, str]):
    is_str = False
    if isinstance(data, str):
        is_str = True
        try:
            # Dict[str: List[str]]
            data = parse_qs(data, keep_blank_values=True, strict_parsing=True)
        except ValueError:
            from .config import config

            return MASK_STRING if config.PREFER_TEXT_FALLBACK_MASKING else data

    if not isinstance(data, dict):
        # But how?!? We shouldn't be here
        return data

    # Should be a list or set of named mask processors already
    # registered with sensitive_paths.add_mask_processor
    # Or name of a single processor
    mask_names = getattr(request, "_apply_mask_processors", [])

    with SensitivePathContext(mask_names):
        masked_data = sanitize_data(data)

    if is_str:
        # https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlencode
        # doseq turns the list values back into multiple keys
        masked_data = urlencode(masked_data, doseq=True)

    return masked_data


# Expects to handle only requests lib Requests
def log_outgoing_request_event(
    *,
    start,
    end,
    logger,
    request=None,
    response=None,
    request_data=None,
    exc_info=None,
    notes=None,
    msg=None,
    method=None,
    url=None,
    direction=None,  # only exists to match existing interface
    edge=RequestEdge.END,
):
    request_info = {}
    response_info = {}

    log_msg = None
    direction = RequestDirection.OUTGOING

    if edge == RequestEdge.START:
        # We can't get access to the prepared request on the START edge
        # The monkey pass will provide us some information.
        method = (method or "").upper()
        request_info = {
            "method": method,
            "url": url,
        }

        log_msg = f"OUTGOING (start): {method} {url}"

    else:
        # assert edge == RequestEdge.END
        if request:
            request_info = {
                "method": request.method,
            }

            # TODO: parse url to niceify the query string
            request_info["url"] = request.url
            request_info["path"] = request.path_url
            request_info["headers"] = sanitize_request_data(
                request,
                dict(request.headers),
            )

            if request.body:
                if isinstance(request.body, bytes):
                    body = request.body.decode("utf-8", "replace")
                else:
                    body = request.body

                try:
                    request_info["data"] = sanitize_request_data(
                        request, json.loads(body)
                    )
                except json.JSONDecodeError:
                    # But what is body? application/x-www-form-urlencoded I hope
                    request_info["data"] = sanitize_request_data(request, body)

            log_msg = f"OUTGOING (end): {request.method} {request.url}"

        if response is not None:
            log_msg += f" ({response.status_code})"

            response_info = {
                "status_code": response.status_code,
            }

            response_text = getattr(response, "text", "")
            try:
                # See if its json data
                response_info["data"] = sanitize_request_data(
                    request, json.loads(response_text)
                )
            except json.JSONDecodeError:
                response_info["data"] = sanitize_request_data(request, response_text)

    if exc_info:
        log_func = logger.error
    else:
        log_func = logger.info

    extra = {
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "end_time": end and end.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "response_time_ms": calculate_response_time_ms(start, end),
        "request": request_info,
        "response": response_info,
        "notes": notes,
        "smart": True,
        "direction": direction,
        "edge": edge,
    }

    log_func(log_msg, exc_info=exc_info, extra=extra)


# Expects to Handle django request objects
def log_incoming_request_event(
    *,
    start,
    end,
    logger,
    request=None,
    response=None,
    request_data=None,
    exc_info=None,
    notes=None,
    msg=None,
    method=None,
    url=None,
    direction=None,  # only exists to match existing interface
    edge=RequestEdge.END,
):
    from .config import config

    request_info = {}
    response_info = {}

    log_msg = None
    direction = RequestDirection.INCOMING

    if edge == RequestEdge.START:
        if request:
            request_info = {
                "method": request.method,
                "remote_addr": request.META["REMOTE_ADDR"],
                "url_scheme": request.scheme,
                "path": request.path,
                "POST": sanitize_request_data(request, request.POST),
                "GET": sanitize_request_data(request, request.GET),
                "data": sanitize_request_data(request, request_data),
                "headers": sanitize_request_data(
                    request,
                    {h: v for h, v in request.META.items() if h.startswith("HTTP_")},
                ),
            }
            log_msg = f"INCOMING (start): {request.method} {request.path}"
        else:
            # Better to provide a request on a START flow
            log_msg = f"INCOMING (start): {method} {url}"

    else:
        # assert edge == RequestEdge.END
        if request:
            request_info = {
                "method": request.method,
            }

            # This is a django.http.HttpRequest
            request_info["remote_addr"] = request.META.get("REMOTE_ADDR", "")
            request_info["url_scheme"] = request.META.get("wsgi.url_scheme", "https")
            request_info["path"] = request.path
            request_info["POST"] = sanitize_request_data(request, request.POST)
            request_info["GET"] = sanitize_request_data(request, request.GET)
            request_info["data"] = sanitize_request_data(request, request_data)
            request_info["headers"] = sanitize_request_data(
                request,
                {h: v for h, v in request.META.items() if h.startswith("HTTP_")},
            )

            log_msg = f"INCOMING (end): {request.method} {request.path}"

        if response is not None:
            log_msg += f" ({response.status_code})"

            response_info = {
                "status_code": response.status_code,
            }

            # Set _log_data to False on any Django response object before your
            # view returns it to prevent the response being logged.
            if getattr(response, "_log_data", True):
                response_headers = getattr(response, "headers", {})
                is_json_response = (
                    response_headers.get("Content-Type", "") == "application/json"
                )

                # We only ever log json responses
                if config.LOG_RESPONSE_CONTENT and is_json_response:
                    response_info["data"] = sanitize_request_data(
                        request, json.loads(response.content)
                    )
            else:
                response_info["data"] = {"NOT_LOGGED": "_log_data == False"}

    if exc_info:
        log_func = logger.error
    else:
        log_func = logger.info

    extra = {
        "start_time": start.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "end_time": end and end.strftime("%Y-%m-%d %H:%M:%S.%f"),
        "response_time_ms": calculate_response_time_ms(start, end),
        "request": request_info,
        "response": response_info,
        "notes": notes,
        "smart": True,
        "direction": direction,
        "edge": edge,
    }

    log_func(log_msg, exc_info=exc_info, extra=extra)
