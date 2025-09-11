from django.urls import path

from .views import OTPRequestView, OTPVerifyView

app_name = "core"

urlpatterns = [
    # OTP-based flows (Registration and Login)
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
]
