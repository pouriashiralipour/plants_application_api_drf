"""
Phone number validation and normalization utilities for Iranian mobile numbers.

This module provides:
- A reusable Django `RegexValidator` (`phone_validator`) to ensure that
  user-submitted phone numbers follow the Iranian mobile number format.
- A normalization helper (`normalize_iran_phone`) that standardizes
  phone numbers into a consistent international format (`+98XXXXXXXXXX`).

Examples:
    >>> phone_validator("+989123456789")  # Valid
    >>> phone_validator("09123456789")    # Valid
    >>> phone_validator("9123456789")     # Invalid

    >>> normalize_iran_phone("09123456789")
    '+989123456789'
    >>> normalize_iran_phone("+98 912-345-6789")
    '+989123456789'
    >>> normalize_iran_phone("09351234567")
    '+989351234567'
"""

import re

from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

#: A Django validator for Iranian phone numbers.
#:
#: Valid formats:
#: - International with country code: ``+989XXXXXXXXX`` (e.g., ``+989123456789``)
#: - Local with leading zero: ``09XXXXXXXXX`` (e.g., ``09123456789``)
#:
#: Invalid formats:
#: - Missing leading +98 or 0 (e.g., ``9123456789``)
#: - Non-numeric characters (excluding optional +)
#: - Incorrect length
#:
#: Raises:
#:     django.core.exceptions.ValidationError: If the input does not match the pattern.


phone_validator = RegexValidator(
    regex=r"^(\+98|0)9\d{9}$",
    message=_(
        "Enter a valid Iranian phone number (e.g. +98912xxxxxxx or 0912xxxxxxx)."
    ),
)


def normalize_iran_phone(value: str) -> str:
    """
    Normalize a given Iranian phone number to the standard international format.

    This function removes non-digit characters and converts valid Iranian
    mobile numbers into the canonical format ``+98XXXXXXXXXX``.

    Transformation rules:
        - Remove all non-digit characters.
        - Strip leading '0' (local format).
        - Strip leading '98' (country code without '+').
        - Ensure the number starts with '9' (valid mobile prefix).
        - Prepend '+98' to produce a normalized international format.

    Args:
        value (str): The phone number to normalize. Can include spaces,
            dashes, parentheses, or be in local/international format.

    Returns:
        str: The normalized phone number in ``+98XXXXXXXXXX`` format if valid,
        otherwise returns the original input.

    Examples:
        >>> normalize_iran_phone("09123456789")
        '+989123456789'
        >>> normalize_iran_phone("+98 912-345-6789")
        '+989123456789'
        >>> normalize_iran_phone("9123456789")
        '9123456789'  # Not normalized, invalid input
    """

    if not value:
        return value

    digits = re.sub(r"\D", "", value)

    if digits.startswith("0"):
        digits = digits[1:]

    if digits.startswith("98"):
        digits = digits[2:]

    if len(digits) == 10 and digits.startswith("9"):
        return f"+98{digits}"

    return f"+98{digits}"
