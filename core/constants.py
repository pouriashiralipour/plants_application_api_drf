"""
This module defines enumerations for OTP (One-Time Password) purposes and delivery channels.
It is intended to be used across the project wherever OTP logic is required, such as in
authentication, password reset, and verification flows.

By using Django's `models.TextChoices`, we ensure:
- Better readability of database values.
- Enforced consistency (only predefined choices are allowed).
- Easy integration with forms, serializers, and admin panel.
"""

from django.db import models


class OTPPurpose(models.TextChoices):
    """
    Enumeration of possible OTP (One-Time Password) purposes.

    This class defines the context in which an OTP is issued. By using
    this as a `TextChoices` subclass, we get:
      - A clear mapping between database values and human-readable labels.
      - Built-in validation when used as a field choice in Django models.
      - Developer-friendly constants for use in the codebase.

    Attributes:
        REGISTER (str): OTP is used for user registration.
        LOGIN (str): OTP is used for user login authentication.
        RESET_PASSWORD (str): OTP is used for resetting a user's password.
    """

    REGISTER = "register", "Register"
    LOGIN = "login", "Login"
    RESET_PASSWORD = "reset_password", "Reset Password"


class OTPChannel(models.TextChoices):
    """
    Enumeration of OTP (One-Time Password) delivery channels.

    This class specifies the medium through which an OTP is delivered to the user.
    Using `TextChoices` ensures only supported delivery channels can be stored
    in the database or used in the system.

    Attributes:
        SMS (str): OTP delivered via SMS (mobile text message).
        EMAIL (str): OTP delivered via email.
    """

    SMS = "sms", "SMS"
    EMAIL = "email", "Email"
