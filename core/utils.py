from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

phone_validator = RegexValidator(
    regex=r"^(\+98|0)?9\d{9}$",
    message=_(
        "Enter a valid Iranian phone number (e.g. +98912xxxxxxx or 0912xxxxxxx)."
    ),
)
