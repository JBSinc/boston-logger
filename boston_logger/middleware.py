"""Middleware for request/response logging."""

import json

from django.urls import NoReverseMatch, reverse

from .config import config
from .context_managers import (
    RequestDirection,
    RequestLogContext,
    log_incoming_request_event,
    sanitize_request_data,
)


class RequestResponseLoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not config.ENABLE_LOGGING_MIDDLEWARE:
            return self.get_response(request)

        if self._should_ignore(request):
            return self.get_response(request)

        # Store request content now because it'll be too late to access later on.
        request.body

        if request.FILES:
            # TODO - when there's files, there's nothing else to add to req_data?
            req_data = {
                "file_list": [
                    request.FILES[filename].name
                    for filename, _ in request.FILES.items()
                ]
            }
        else:
            req_data = request.body.decode("utf-8", "replace")
            try:
                # TODO - no attempt at using content negotiation headers
                # this will fail on form encoded POSTs, yeah?
                req_data = json.loads(req_data)
            except json.JSONDecodeError:
                req_data = {"raw_body": sanitize_request_data(request, req_data)}

        with RequestLogContext(
            request=request,
            request_data=req_data,
            direction=RequestDirection.INCOMING,
            make_log_func=log_incoming_request_event,
        ) as log_context:
            # Could be django.http.response.HttpResponse
            response = self.get_response(request)
            log_context.notes = getattr(request, "_request_notes", None)
            log_context.response = response

        return response

    @staticmethod
    def _should_ignore(request):
        """
        Checks if the requested url should logged or not
        By default it will ignore admin and swagger requests
        """
        for url_name in config.MIDDLEWARE_BLOCKLIST:
            try:
                if request.path.startswith(reverse(url_name)):
                    return True
            except NoReverseMatch:
                pass
        return False
