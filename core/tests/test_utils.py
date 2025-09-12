import pytest
from django.core.exceptions import ValidationError

from core.utils import normalize_iran_phone, phone_validator


class TestPhoneValidator:
    @pytest.mark.parametrize(
        "valid_phone",
        [
            "+989123456789",
            "09123456789",
            "+989351234567",
            "09351234567",
            "+989011234567",
            "09981234567",
        ],
    )
    def test_valid_phone_numbers(self, valid_phone):
        try:
            phone_validator(valid_phone)
        except ValidationError:
            pytest.fail(f"ValidationError was raised for valid phone: {valid_phone}")

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "9123456789",
            "123456789",
            "+98912345678",
            "0912345678",
            "+9891234567890",
            "091234567890",
            "0912-345-6789",
            "+98 912 345 6789",
            "invalid-number",
            "",
        ],
    )
    def test_invalid_phone_numbers(self, invalid_phone):

        with pytest.raises(ValidationError):
            phone_validator(invalid_phone)


class TestNormalizeIranPhone:
    @pytest.mark.parametrize(
        "input_phone, expected_output",
        [
            ("09123456789", "+989123456789"),
            ("+989123456789", "+989123456789"),
            ("0935 123 4567", "+989351234567"),
            ("+98 901-123-4567", "+989011234567"),
            ("  09981234567  ", "+989981234567"),
            ("989123456789", "+989123456789"),
        ],
    )
    def test_normalization_of_valid_numbers(self, input_phone, expected_output):
        assert normalize_iran_phone(input_phone) == expected_output

    @pytest.mark.parametrize(
        "invalid_input",
        [
            "9123456789",
            "123456789",
            "+98912345678",
            "0912-345-678",
            "invalid-string",
        ],
    )
    def test_normalization_of_invalid_numbers(self, invalid_input):
        assert normalize_iran_phone(invalid_input) == invalid_input

    def test_empty_string_input(self):
        assert normalize_iran_phone("") == ""

    def test_none_input(self):
        assert normalize_iran_phone(None) is None
