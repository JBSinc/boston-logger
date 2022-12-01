from django.http import JsonResponse


def index(request):
    return JsonResponse({"obj1": {"key1": "value"}})


def log_no_resp_data(request):
    resp = JsonResponse({"obj1": {"key1": "value"}})
    resp._log_data = False
    return resp
