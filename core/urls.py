from django.urls import path

from .views import LoginView, OTPRequestView, OTPVerifyView, ProfileCompletionView

app_name = "core"

urlpatterns = [
    # OTP-based flows (Registration and Login)
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    # Profile management
    path("profile/complete/", ProfileCompletionView.as_view(), name="profile-complete"),
    # Password-based login
    path("login/", LoginView.as_view(), name="login"),
]
