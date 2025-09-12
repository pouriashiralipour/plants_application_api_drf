"""
Unit tests for the OTPService in `core.services`.

This module tests all key functionalities of the OTPService, which is responsible for:
    - Generating OTP codes.
    - Sending OTP codes to users (via cache and channels like SMS/email).
    - Verifying OTP codes against stored values.
    - Enforcing retry attempt limits and expiration rules.

The tests cover:
    - OTP code generation with default and custom lengths.
    - Successful OTP sending when no active OTP exists.
    - Prevention of new OTPs when an active one already exists.
    - Successful OTP verification.
    - Handling of OTP verification failures:
        * No OTP in cache.
        * Purpose mismatch.
        * Incorrect codes with attempt increment.
        * Exceeding maximum allowed attempts.
    - Ensuring cache operations (`get`, `set`, `delete`, `ttl`) are called properly.

Tools:
    - `pytest` for test structure and assertions.
    - `pytest-mock` for mocking cache operations and service internals.
"""

from core.services import MAX_OTP_ATTEMPTS, OTP_TTL_SECONDS, OTPService


class TestServices:
    """
    Test suite for `OTPService`.

    Each method validates one specific behavior of the service.
    """

    def test_generate_code(self):
        """
        Test that `_generate_code` produces a valid 6-digit numeric string.
        """

        code = OTPService._generate_code()

        # OTP must be a string
        assert isinstance(code, str)

        # Default length is 6
        assert len(code) == 6

        # Must contain only digits
        assert code.isdigit()

    def test_generate_code_custom_length(self):
        """
        Test that `_generate_code` supports custom length codes.
        """

        custom_length = 8

        code = OTPService._generate_code(length=custom_length)

        assert len(code) == custom_length
        assert code.isdigit()

    def test_send_otp_success(self, mocker):
        """
        Test that `send_otp` successfully generates and stores an OTP
        when no active OTP exists in the cache.
        """

        # Force _generate_code to return a known value
        mocker.patch("core.services.OTPService._generate_code", return_value="123456")
        mock_cache_get = mocker.patch("core.services.cache.get", return_value=None)
        mock_cache_set = mocker.patch("core.services.cache.set")

        target = "+989123456789"
        purpose = "login"

        # Act: send OTP
        result = OTPService.send_otp(target=target, purpose=purpose, channel="sms")

        # Assert: OTP was created and stored
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
        """
        Test that `send_otp` fails if there is already an active OTP
        for the target (prevents OTP spamming).
        """

        target = "+989123456789"

        # Simulate an active OTP already in cache
        mock_cache_get = mocker.patch(
            "core.services.cache.get", return_value={"code": "987654"}
        )
        mock_cache_set = mocker.patch("core.services.cache.set")

        result = OTPService.send_otp(target=target, purpose="login", channel="sms")

        assert result is False

        mock_cache_get.assert_called_once_with(f"otp:{target}")

        mock_cache_set.assert_not_called()

    def test_verify_otp_success(self, mocker):
        """
        Test that `verify_otp` succeeds when code and purpose match,
        and the OTP is then deleted from cache.
        """

        target = "+989123456789"
        purpose = "login"
        code = "123456"

        otp_data = {"code": code, "purpose": purpose, "attempts": 0}
        mocker.patch("core.services.cache.get", return_value=otp_data)
        mock_cache_delete = mocker.patch("core.services.cache.delete")

        result = OTPService.verify_otp(target=target, code=code, purpose=purpose)

        # OTP verified and returned
        assert result == otp_data

        # OTP removed after successful verification
        mock_cache_delete.assert_called_once_with(f"otp:{target}")

    def test_verify_otp_no_otp_in_cache(self, mocker):
        """
        Test that `verify_otp` returns None if no OTP exists in cache.
        """

        mocker.patch("core.services.cache.get", return_value=None)

        result = OTPService.verify_otp(target="any", code="any", purpose="any")

        assert result is None

    def test_verify_otp_purpose_mismatch(self, mocker):
        """
        Test that `verify_otp` returns None if the stored purpose
        does not match the provided one.
        """
        otp_data = {"code": "123456", "purpose": "password_reset", "attempts": 0}
        mocker.patch("core.services.cache.get", return_value=otp_data)

        result = OTPService.verify_otp(target="any", code="123456", purpose="login")

        assert result is None

    def test_verify_otp_incorrect_code_increments_attempts(self, mocker):
        """
        Test that when an incorrect code is provided:
            - The attempts counter is incremented.
            - OTP remains in cache with updated attempts.
        """

        target = "+989123456789"
        key = f"otp:{target}"

        otp_data = {"code": "123456", "purpose": "login", "attempts": 0}
        mocker.patch("core.services.cache.get", return_value=otp_data)

        mocker.patch("core.services.cache.ttl", return_value=100)
        mock_cache_set = mocker.patch("core.services.cache.set")

        result = OTPService.verify_otp(target=target, code="654321", purpose="login")

        # Incorrect OTP → verification fails
        assert result is None

        # Attempts incremented
        updated_otp_data = otp_data.copy()
        updated_otp_data["attempts"] = 1

        mock_cache_set.assert_called_once_with(key, updated_otp_data, timeout=100)

    def test_verify_otp_max_attempts_exceeded(self, mocker):
        """
        Test that OTP is deleted if maximum attempts are exceeded.
        """
        target = "+989123456789"

        otp_data = {"code": "123456", "purpose": "login", "attempts": MAX_OTP_ATTEMPTS}
        mocker.patch("core.services.cache.get", return_value=otp_data)
        mock_cache_delete = mocker.patch("core.services.cache.delete")

        result = OTPService.verify_otp(target=target, code="123456", purpose="login")

        # OTP invalid due to max attempts exceeded
        assert result is None
        mock_cache_delete.assert_called_once_with(f"otp:{target}")
