from django.urls import path

from .views import (
    LoginView,
    OTPRequestView,
    OTPVerifyView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    ProfileCompletionView,
)

app_name = "core"

urlpatterns = [
    # OTP-based flows (Registration and Login)
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    # Profile management
    path("profile/complete/", ProfileCompletionView.as_view(), name="profile-complete"),
    # Password-based login
    path("login/", LoginView.as_view(), name="login"),
    # 3-step Password reset flow
    path(
        "password/reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password/reset/verify/",
        PasswordResetVerifyView.as_view(),
        name="password-reset-verify",
    ),
]
