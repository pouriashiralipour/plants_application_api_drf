"""
Unit tests for user-related DRF serializers in the `core` app.

This module covers serializers responsible for:
    - User representation (`UserSerializer`)
    - OTP requests and verification (`OTPRequestSerializer`, `OTPVerifySerializer`)
    - Profile completion (`ProfileCompletionSerializer`)
    - Login (`LoginSerializer`)
    - Password reset workflows (`PasswordResetRequestSerializer`, `PasswordResetVerifySerializer`, `PasswordResetSetPasswordSerializer`)
    - Identifier changes (`IdentifierChangeRequestSerializer`, `IdentifierChangeVerifySerializer`)

Fixtures:
    - `user_factory`: Creates users with default or custom fields.
    - `api_request_factory`: Provides a DRF-compatible request factory for testing serializers requiring request context.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from core.serializers import (
    IdentifierChangeRequestSerializer,
    IdentifierChangeVerifySerializer,
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordResetRequestSerializer,
    PasswordResetSetPasswordSerializer,
    PasswordResetVerifySerializer,
    ProfileCompletionSerializer,
    UserSerializer,
)

# Get the active user model
User = get_user_model()


@pytest.fixture
def user_factory():
    """
    Factory fixture to create user instances for tests.

    Usage:
        user = user_factory(email="custom@example.com")
    """

    def _create_user(**kwargs):
        defaults = {"email": "default@example.com", "password": "strong-password-123"}
        defaults.update(kwargs)
        return User.objects.create_user(**defaults)

    return _create_user


@pytest.fixture
def api_request_factory():
    """Fixture providing a DRF APIRequestFactory for creating request objects."""
    return APIRequestFactory()


@pytest.mark.django_db
class TestUserSerializer:
    """Tests for the `UserSerializer`."""

    def test_serializer_contains_expected_fields(self, user_factory):
        """Ensure serializer exposes the correct fields and full_name is formatted properly."""
        user = user_factory(
            first_name="Test", last_name="User", phone_number="09121112233"
        )
        serializer = UserSerializer(instance=user)
        data = serializer.data
        expected_keys = {
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_pic",
            "date_of_birth",
            "nickname",
            "gender",
            "is_email_verified",
            "is_phone_verified",
        }
        assert set(data.keys()) == expected_keys
        assert data["full_name"] == "Test User"


@pytest.mark.django_db
class TestOTPRequestSerializer:
    """Tests for the `OTPRequestSerializer`."""

    def test_register_with_new_email_is_valid(self):
        """A registration OTP request with a new email should be valid."""
        data = {"target": "new.user@example.com", "purpose": "register"}
        serializer = OTPRequestSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.context["channel"] == "email"

    def test_register_with_existing_email_is_invalid(self, user_factory):
        """OTP registration request should fail if the email already exists."""
        user_factory(email="existing@example.com")
        data = {"target": "existing@example.com", "purpose": "register"}
        serializer = OTPRequestSerializer(data=data)
        with pytest.raises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_login_with_existing_phone_is_valid(self, user_factory):
        """OTP login request with existing phone should be valid."""
        user_factory(phone_number="09129998877", email=None)
        data = {"target": "0912-999-8877", "purpose": "login"}
        serializer = OTPRequestSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.validated_data["target"] == "+989129998877"

    def test_login_with_non_existent_phone_is_invalid(self):
        """OTP login request with a non-existent phone should fail."""
        data = {"target": "09120000000", "purpose": "login"}
        serializer = OTPRequestSerializer(data=data)
        with pytest.raises(ValidationError):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestOTPVerifySerializer:
    """Tests for `OTPVerifySerializer`."""

    def test_valid_otp_succeeds(self, mocker, api_request_factory):
        """Valid OTP code should pass verification."""
        mock_request = api_request_factory.get("/")
        mock_request.session = {"otp_target": "+989121234567", "otp_purpose": "login"}
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )
        serializer = OTPVerifySerializer(
            data={"code": "123456"}, context={"request": Request(mock_request)}
        )
        assert serializer.is_valid(raise_exception=True)

    def test_invalid_otp_fails(self, mocker, api_request_factory):
        """Invalid OTP code should raise a validation error."""
        mock_request = api_request_factory.get("/")
        mock_request.session = {"otp_target": "+989121234567", "otp_purpose": "login"}
        mocker.patch("core.services.OTPService.verify_otp", return_value=None)
        serializer = OTPVerifySerializer(
            data={"code": "654321"}, context={"request": Request(mock_request)}
        )
        with pytest.raises(ValidationError, match="Invalid or expired OTP."):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestProfileCompletionSerializer:
    """Tests for the ProfileCompletionSerializer."""

    def test_completion_for_user_with_phone(self, user_factory, api_request_factory):
        """
        Tests profile completion for a user who initially registered with a phone number.
        They must provide an email.
        """
        user = user_factory(
            phone_number="09121112233", email=None, is_phone_verified=True
        )

        wsgi_request = api_request_factory.patch("/")

        force_authenticate(wsgi_request, user=user)

        drf_request = Request(wsgi_request)

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "email": "john.doe@example.com",
            "password": "new-strong-password",
        }

        serializer = ProfileCompletionSerializer(
            instance=user,
            data=data,
            context={"request": drf_request},
        )

        assert serializer.is_valid(raise_exception=True)
        updated_user = serializer.save()

        assert updated_user.full_name == "John Doe"
        assert updated_user.email == "john.doe@example.com"
        assert updated_user.is_email_verified is True
        assert updated_user.check_password("new-strong-password")


@pytest.mark.django_db
class TestLoginSerializer:
    """Tests for the standard LoginSerializer."""

    def test_login_with_correct_email_and_pass_is_valid(self, user_factory):
        """Tests successful login with a valid email and password."""
        user = user_factory(
            email="login@example.com", password="pw123", is_email_verified=True
        )
        serializer = LoginSerializer(
            data={"login": "login@example.com", "password": "pw123"}
        )
        assert serializer.is_valid(raise_exception=True)
        assert serializer.validated_data["user"] == user

    def test_login_with_incorrect_password_is_invalid(self, user_factory):
        """Tests that login fails with an incorrect password."""
        user_factory(
            email="login@example.com", password="pw123", is_email_verified=True
        )
        serializer = LoginSerializer(
            data={"login": "login@example.com", "password": "wrong-pw"}
        )
        with pytest.raises(
            ValidationError, match="The login information was incorrect."
        ):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestPasswordResetRequestSerializer:
    """Tests for the PasswordResetRequestSerializer."""

    def test_request_with_existing_user_is_valid(self, user_factory):
        """Tests a valid password reset request for an existing user."""
        user_factory(email="reset@example.com")
        serializer = PasswordResetRequestSerializer(
            data={"target": "reset@example.com"}
        )
        assert serializer.is_valid(raise_exception=True)
        assert serializer.context["channel"] == "email"

    def test_request_with_non_existent_user_is_invalid(self):
        """Tests that a request for a non-existent user fails."""
        serializer = PasswordResetRequestSerializer(
            data={"target": "no-one@example.com"}
        )
        with pytest.raises(
            ValidationError, match="No user found with this identifier."
        ):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestPasswordResetVerifySerializer:
    """Tests for the PasswordResetVerifySerializer."""

    def test_verification_with_valid_code_succeeds(
        self, user_factory, mocker, api_request_factory
    ):
        """Tests that reset verification succeeds and sets user ID in session."""
        user = user_factory(email="reset@example.com")
        mock_request = api_request_factory.post("/")
        mock_request.session = {"reset_target": "reset@example.com"}
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )
        serializer = PasswordResetVerifySerializer(
            data={"code": "123456"}, context={"request": Request(mock_request)}
        )

        assert serializer.is_valid(raise_exception=True)
        assert mock_request.session["reset_user_id"] == user.id


@pytest.mark.django_db
class TestPasswordResetSetPasswordSerializer:
    """Tests for the PasswordResetSetPasswordSerializer."""

    def test_matching_passwords_are_valid(self):
        """Tests that matching passwords pass validation."""
        data = {
            "password": "new-pass-123",
            "password_confirm": "new-pass-123",
            "reset_token": "dummy",
        }
        serializer = PasswordResetSetPasswordSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)

    def test_mismatched_passwords_are_invalid(self):
        """Tests that mismatched passwords fail validation."""
        data = {
            "password": "new-pass-123",
            "password_confirm": "different-pass",
            "reset_token": "dummy",
        }
        serializer = PasswordResetSetPasswordSerializer(data=data)
        with pytest.raises(ValidationError, match="Passwords do not match."):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestIdentifierChangeRequestSerializer:
    """Tests for the IdentifierChangeRequestSerializer."""

    def test_request_with_available_email_is_valid(
        self, user_factory, api_request_factory
    ):
        """Tests a change request to a new, unused email address."""
        user = user_factory()
        mock_request = api_request_factory.post("/")
        mock_request.user = user
        serializer = IdentifierChangeRequestSerializer(
            data={"target": "new-email@example.com"},
            context={"request": Request(mock_request)},
        )
        assert serializer.is_valid(raise_exception=True)

    def test_request_with_taken_email_is_invalid(
        self, user_factory, api_request_factory
    ):
        """Tests that a change request to an already used email fails."""
        user_factory(email="taken@example.com")  # The email that is already in use
        current_user = user_factory(email="current@example.com")
        mock_request = api_request_factory.post("/")
        mock_request.user = current_user
        serializer = IdentifierChangeRequestSerializer(
            data={"target": "taken@example.com"},
            context={"request": Request(mock_request)},
        )
        with pytest.raises(
            ValidationError, match="This email is already in use by another account."
        ):
            serializer.is_valid(raise_exception=True)


@pytest.mark.django_db
class TestIdentifierChangeVerifySerializer:
    """Tests for the IdentifierChangeVerifySerializer."""

    def test_verification_with_valid_code_succeeds(self, mocker, api_request_factory):
        """A simple test to ensure the verification logic is wired up correctly."""
        mock_request = api_request_factory.post("/")
        # The view would put the target and purpose in the session
        mock_request.session = {
            "change_target": "new@example.com",
            "change_purpose": "change_email",
        }
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )
        serializer = IdentifierChangeVerifySerializer(
            data={"code": "123456"}, context={"request": Request(mock_request)}
        )
        # This serializer does not have custom validation logic, so we just check it runs
        # The main OTP verification logic is already tested in TestOTPVerifySerializer
        assert serializer.is_valid(raise_exception=True)
