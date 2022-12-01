from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("log_no_resp_data", views.log_no_resp_data, name="log_no_resp_data"),
]
