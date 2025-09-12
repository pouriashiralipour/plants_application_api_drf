import pytest
from django.core.cache import cache

from core.services import MAX_OTP_ATTEMPTS, OTPService

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache_before_each_test():
    cache.clear()
    yield
    cache.clear()


class TestOTPService:
    def test_generate_code_default_length(self):

        code = OTPService._generate_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_custom_length(self):

        code = OTPService._generate_code(length=8)

        assert len(code) == 8
        assert code.isdigit()

    def test_send_otp_success(self):

        target = "test@example.com"
        purpose = "register"

        result = OTPService.send_otp(target=target, purpose=purpose, channel="email")

        assert result is True
        cached_data = cache.get(f"otp:{target}")
        assert cached_data is not None
        assert "code" in cached_data
        assert cached_data["purpose"] == purpose
        assert cached_data["attempts"] == 0

    def test_send_otp_fails_if_active_otp_exists(self):

        target = "test@example.com"
        purpose = "register"

        cache.set(f"otp:{target}", {"code": "111111"})

        result = OTPService.send_otp(target=target, purpose=purpose, channel="email")

        assert result is False

        assert cache.get(f"otp:{target}")["code"] == "111111"

    def test_verify_otp_success(self):

        target = "+989123456789"
        purpose = "login"
        code = "123456"
        otp_data = {"code": code, "purpose": purpose, "attempts": 0}
        cache.set(f"otp:{target}", otp_data)

        result = OTPService.verify_otp(target=target, code=code, purpose=purpose)

        assert result is not None
        assert result["code"] == code

        assert cache.get(f"otp:{target}") is None

    def test_verify_otp_invalid_code(self):

        target = "+989123456789"
        purpose = "login"
        correct_code = "123456"
        wrong_code = "654321"
        otp_data = {"code": correct_code, "purpose": purpose, "attempts": 0}
        cache.set(f"otp:{target}", otp_data)

        result = OTPService.verify_otp(target=target, code=wrong_code, purpose=purpose)

        assert result is None
        cached_data = cache.get(f"otp:{target}")
        assert cached_data is not None
        assert cached_data["attempts"] == 1

    def test_verify_otp_invalid_purpose(self):

        target = "test@example.com"
        code = "123456"
        stored_purpose = "register"
        verify_purpose = "login"
        otp_data = {"code": code, "purpose": stored_purpose, "attempts": 0}
        cache.set(f"otp:{target}", otp_data)

        result = OTPService.verify_otp(target=target, code=code, purpose=verify_purpose)

        assert result is None

        assert cache.get(f"otp:{target}")["attempts"] == 0

    def test_verify_otp_not_found(self):

        result = OTPService.verify_otp(
            target="nonexistent@example.com", code="123456", purpose="login"
        )

        assert result is None

    def test_verify_otp_max_attempts_exceeded(self):

        target = "+989123456789"
        purpose = "login"
        code = "123456"
        otp_data = {
            "code": code,
            "purpose": purpose,
            "attempts": MAX_OTP_ATTEMPTS,
        }
        cache.set(f"otp:{target}", otp_data)

        result = OTPService.verify_otp(
            target=target, code="wrong_code", purpose=purpose
        )

# assert result is None

        assert cache.get(f"otp:{target}") is None
