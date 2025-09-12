import pytest
from django.contrib.auth import get_user_model

from core.factories import UserFactory
from core.serializers import (
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordResetRequestSerializer,
    PasswordResetSetPasswordSerializer,
    PasswordResetVerifySerializer,
    ProfileCompletionSerializer,
    UserSerializer,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserSerializer:
    def test_serialization(self):
        user = UserFactory.build()
        serializer = UserSerializer(instance=user)
        data = serializer.data

        assert set(data.keys()) == {
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
        assert data["full_name"] == user.full_name


class TestOTPRequestSerializer:
    def test_register_with_new_email_is_valid(self):
        data = {"target": "newuser@example.com", "purpose": "register"}
        serializer = OTPRequestSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.context["channel"] == "email"

    def test_register_with_existing_email_is_invalid(self):
        UserFactory(email="existing@example.com")
        data = {"target": "existing@example.com", "purpose": "register"}
        serializer = OTPRequestSerializer(data=data)
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "already exists" in str(excinfo.value)

    def test_login_with_existing_phone_is_valid(self):
        UserFactory(phone_number="+989123456789")
        data = {"target": "09123456789", "purpose": "login"}
        serializer = OTPRequestSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.validated_data["target"] == "+989123456789"

    def test_login_with_non_existing_user_is_invalid(self):
        data = {"target": "nouser@example.com", "purpose": "login"}
        serializer = OTPRequestSerializer(data=data)
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "not found" in str(excinfo.value)


class TestOTPVerifySerializer:
    def test_verify_success(self, mocker, rf):
        mock_verify_otp = mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        request = rf.post("/")
        request.session = {"otp_target": "test@example.com", "otp_purpose": "register"}

        serializer = OTPVerifySerializer(
            data={"code": "123456"}, context={"request": request}
        )

        assert serializer.is_valid(raise_exception=True)
        mock_verify_otp.assert_called_once_with(
            target="test@example.com", code="123456", purpose="register"
        )

    def test_verify_failure_invalid_code(self, mocker, rf):
        mocker.patch("core.services.OTPService.verify_otp", return_value=None)

        request = rf.post("/")
        request.session = {"otp_target": "test@example.com", "otp_purpose": "register"}

        serializer = OTPVerifySerializer(
            data={"code": "654321"}, context={"request": request}
        )
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "Invalid or expired OTP" in str(excinfo.value)

    def test_verify_failure_no_session(self, rf):
        request = rf.post("/")
        request.session = {}

        serializer = OTPVerifySerializer(
            data={"code": "123456"}, context={"request": request}
        )
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "No active OTP request found" in str(excinfo.value)


class TestLoginSerializer:
    def test_login_success_with_email(self):
        user = UserFactory(
            password="strongpassword123", email="login@test.com", is_email_verified=True
        )
        data = {"login": "login@test.com", "password": "strongpassword123"}
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)
        assert serializer.validated_data["user"] == user

    def test_login_failure_wrong_password(self):
        UserFactory(password="strongpassword123", email="login@test.com")
        data = {"login": "login@test.com", "password": "wrongpassword"}
        serializer = LoginSerializer(data=data)
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "Invalid credentials" in str(excinfo.value)

    def test_login_failure_unverified_account(self):
        UserFactory(
            password="strongpassword123",
            email="login@test.com",
            is_email_verified=False,
            is_phone_verified=False,
        )
        data = {"login": "login@test.com", "password": "strongpassword123"}
        serializer = LoginSerializer(data=data)
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "Account not verified" in str(excinfo.value)


class TestProfileCompletionSerializer:
    def test_completion_for_user_with_email(self, rf):
        user = UserFactory(phone_number=None, email="profile@test.com")
        request = rf.patch("/")
        request.user = user

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1990-01-01",
            "phone_number": "09129876543",
            "password": "newpassword123",
        }

        serializer = ProfileCompletionSerializer(
            instance=user, data=data, context={"request": request}
        )
        assert serializer.is_valid(raise_exception=True)

        updated_user = serializer.save()
        assert updated_user.first_name == "John"
        assert updated_user.phone_number == "+989129876543"
        assert updated_user.is_phone_verified is True
        assert updated_user.check_password("newpassword123")


class TestPasswordResetSerializers:
    def test_request_serializer_success(self):
        UserFactory(email="reset@test.com")
        serializer = PasswordResetRequestSerializer(data={"target": "reset@test.com"})
        assert serializer.is_valid(raise_exception=True)

    def test_verify_serializer_success(self, mocker, rf):
        user = UserFactory(email="reset@test.com")
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        request = rf.post("/")
        request.session = {"reset_target": "reset@test.com"}

        serializer = PasswordResetVerifySerializer(
            data={"code": "123456"}, context={"request": request}
        )
        assert serializer.is_valid(raise_exception=True)
        assert request.session["reset_user_id"] == user.id

    def test_set_password_serializer_success(self):
        data = {"password": "newpassword123", "password_confirm": "newpassword123"}
        serializer = PasswordResetSetPasswordSerializer(data=data)
        assert serializer.is_valid(raise_exception=True)

    def test_set_password_serializer_mismatch_fails(self):
        data = {"password": "newpassword123", "password_confirm": "differentpassword"}
        serializer = PasswordResetSetPasswordSerializer(data=data)
        with pytest.raises(
            pytest.importorskip("rest_framework").exceptions.ValidationError
        ) as excinfo:
            serializer.is_valid(raise_exception=True)
        assert "Passwords do not match" in str(excinfo.value)
