import pytest

from core.services import MAX_OTP_ATTEMPTS, OTP_TTL_SECONDS, OTPService


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

    def test_send_otp_success(self, mocker):
        mocker.patch("core.services.OTPService._generate_code", return_value="123456")
        mock_cache_get = mocker.patch("core.services.cache.get", return_value=None)
        mock_cache_set = mocker.patch("core.services.cache.set")

        target = "+989123456789"
        purpose = "login"
        result = OTPService.send_otp(target=target, purpose=purpose, channel="sms")

        assert result is True

        mock_cache_get.assert_called_once_with(f"otp:{target}")

        expected_otp_data = {
            "code": "123456",
            "purpose": purpose,
            "attempts": 0,
        }

        mock_cache_set.assert_called_once_with(
            f"otp:{target}", expected_otp_data, timeout=OTP_TTL_SECONDS
        )

    def test_send_otp_fails_if_active_otp_exists(self, mocker):
        target = "+989123456789"
        mock_cache_get = mocker.patch(
            "core.services.cache.get", return_value={"code": "987654"}
        )
        mock_cache_set = mocker.patch("core.services.cache.set")

        result = OTPService.send_otp(target=target, purpose="login", channel="sms")

        assert result is False

        mock_cache_get.assert_called_once_with(f"otp:{target}")

        mock_cache_set.assert_not_called()
