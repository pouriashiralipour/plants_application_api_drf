import re

from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

phone_validator = RegexValidator(
    regex=r"^(\+98|0)?9\d{9}$",
    message=_(
        "Enter a valid Iranian phone number (e.g. +98912xxxxxxx or 0912xxxxxxx)."
    ),
)


def normalize_iran_phone(value: str) -> str:
    if not value:
        return value

    digits = re.sub(r"\D", "", value)

    if digits.startswith("0"):
        digits = digits[1:]
    if digits.startswith("98"):
        digits = digits[2:]
    if not digits.startswith("9"):
        return value

    return f"+98{digits}"
