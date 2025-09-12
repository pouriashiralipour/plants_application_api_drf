import pytest

from core.services import MAX_OTP_ATTEMPTS, OTPService


class TestServices:
    def test_generate_code(self):
        code = OTPService._generate_code()

        assert isinstance(code, str)

        assert len(code) == 6

        assert code.isdigit()

    def test_generate_code_custom_length(self):
        custom_length = 8

        code = OTPService._generate_code(length=custom_length)

        assert len(code) == custom_length
        assert code.isdigit()
