"""
Unit tests for phone number utilities.

This module contains tests for two core functionalities:
    1. `phone_validator`: Ensures that phone numbers follow the correct Iranian format.
    2. `normalize_iran_phone`: Normalizes phone numbers into a standard international format.

Testing Strategy:
    - Valid and invalid phone numbers are tested using `pytest.mark.parametrize`
      to cover multiple cases efficiently.
    - Validation tests check whether `ValidationError` is correctly raised
      for invalid inputs.
    - Normalization tests ensure that different formats of valid Iranian
      phone numbers are consistently transformed into the expected `+98...` format.
    - Edge cases like empty strings and `None` values are explicitly handled.

Tools:
    - `pytest`: For parameterized test cases and assertion handling.
    - `django.core.exceptions.ValidationError`: To validate that exceptions
      are correctly raised for invalid inputs.
"""

import pytest
from django.core.exceptions import ValidationError

from core.utils import normalize_iran_phone, phone_validator


class TestPhoneValidator:
    """
    Tests for the `phone_validator` function.

    This class contains tests that verify whether the phone number
    validation function accepts valid numbers and rejects invalid ones.
    """

    @pytest.mark.parametrize(
        "valid_phone",
        [
            "+989123456789",  # Correct international format (mobile prefix 912)
            "09123456789",  # Local Iranian format with 0 prefix
            "+989351234567",  # International format (mobile prefix 935)
            "09351234567",  # Local format (mobile prefix 935)
            "+989011234567",  # International format (mobile prefix 901)
            "09981234567",  # Local format (mobile prefix 998)
        ],
    )
    def test_valid_phone_numbers(self, valid_phone):
        """
        Ensure that valid Iranian phone numbers pass validation.

        Args:
            valid_phone (str): A valid phone number format.

        Expected:
            - No `ValidationError` should be raised.
        """

        try:
            phone_validator(valid_phone)
        except ValidationError:
            # If a ValidationError is raised for a valid number, fail the test
            pytest.fail(f"ValidationError was raised for valid phone: {valid_phone}")

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "9123456789",  # Missing leading 0 or +98
            "123456789",  # Too short
            "+98912345678",  # Too short (only 10 digits after +98)
            "0912345678",  # Too short local format
            "+9891234567890",  # Too long (extra digit)
            "091234567890",  # Too long local format
            "0912-345-6789",  # Contains dashes (invalid characters)
            "+98 912 345 6789",  # Contains spaces (invalid characters)
            "invalid-number",  # Completely invalid string
            "",  # Empty string
        ],
    )
    def test_invalid_phone_numbers(self, invalid_phone):
        """
        Ensure that invalid Iranian phone numbers raise `ValidationError`.

        Args:
            invalid_phone (str): An invalid phone number format.

        Expected:
            - A `ValidationError` should always be raised.
        """

        with pytest.raises(ValidationError):
            phone_validator(invalid_phone)


class TestNormalizeIranPhone:
    """
    Tests for the `normalize_iran_phone` function.

    This class ensures that phone numbers are normalized into the
    correct international format (`+989...`) and that invalid inputs
    remain unchanged.
    """

    @pytest.mark.parametrize(
        "input_phone, expected_output",
        [
            ("09123456789", "+989123456789"),  # Local format → normalized
            ("+989123456789", "+989123456789"),  # Already normalized
            ("0935 123 4567", "+989351234567"),  # Spaces removed and normalized
            ("+98 901-123-4567", "+989011234567"),  # Dashes and spaces removed
            ("  09981234567  ", "+989981234567"),  # Leading/trailing spaces removed
            ("989123456789", "+989123456789"),  # Missing + sign → normalized
        ],
    )
    def test_normalization_of_valid_numbers(self, input_phone, expected_output):
        """
        Ensure that valid phone numbers are normalized correctly.

        Args:
            input_phone (str): Phone number in various formats.
            expected_output (str): Expected normalized format.

        Expected:
            - `normalize_iran_phone` should return `expected_output`.
        """

        assert normalize_iran_phone(input_phone) == expected_output

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "9123456789",  # Missing prefix
            "123456789",  # Too short
            "+98912345678",  # Too short after +98
            "0912-345-678",  # Invalid characters
            "invalid-string",  # Completely invalid input
        ],
    )
    def test_normalization_of_invalid_numbers(self, invalid_input):
        """
        Ensure that invalid phone numbers are not altered.

        Args:
            invalid_input (str): An invalid phone number format.

        Expected:
            - The function should return the input unchanged.
        """
        assert normalize_iran_phone(invalid_input) == invalid_input

    def test_empty_string_input(self):
        """
        Ensure that an empty string returns an empty string.

        Expected:
            - `normalize_iran_phone("")` should return `""`.
        """

        assert normalize_iran_phone("") == ""

    def test_none_input(self):
        """
        Ensure that `None` input returns `None`.

        Expected:
            - `normalize_iran_phone(None)` should return `None`.
        """

        assert normalize_iran_phone(None) is None
