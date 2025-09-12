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
