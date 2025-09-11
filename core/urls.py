from django.urls import path

from .views import OTPRequestView

app_name = "core"

urlpatterns = [
    # OTP-based flows (Registration and Login)
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
]
