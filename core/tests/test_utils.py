import pytest
from django.core.exceptions import ValidationError

from core.utils import normalize_iran_phone, phone_validator


@pytest.mark.parametrize(
    "phone_input, expected_output",
    [
        ("09123456789", "+989123456789"),
        ("+989123456789", "+989123456789"),
        ("0935 123 4567", "+989351234567"),
        ("+98 990-123-4567", "+989901234567"),
        ("9123456789", "+989123456789"),
        ("123456789", "123456789"),
        ("0912345678", "0912345678"),
        ("", ""),
        (None, None),
    ],
)
def test_normalize_iran_phone(phone_input, expected_output):
    assert normalize_iran_phone(phone_input) == expected_output


@pytest.mark.parametrize(
    "valid_phone",
    [
        "+989123456789",
        "09123456789",
        "09901234567",
    ],
)
def test_phone_validator_valid(valid_phone):
    assert phone_validator(valid_phone) is None


@pytest.mark.parametrize(
    "invalid_phone",
    [
        "9123456789",
        "0912345678",
        "+98912345678",
        "12345",
        "0912-345-6789",
    ],
)
def test_phone_validator_invalid(invalid_phone):
    with pytest.raises(ValidationError):
        phone_validator(invalid_phone)
