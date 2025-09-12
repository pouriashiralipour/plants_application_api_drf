from django.db import models


class OTPPurpose(models.TextChoices):
    REGISTER = "register", "Register"
    LOGIN = "login", "Login"
    RESET_PASSWORD = "reset_password", "Reset Password"


class OTPChannel(models.TextChoices):
    SMS = "sms", "SMS"
    EMAIL = "email", "Email"
