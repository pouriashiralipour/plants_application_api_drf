import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import CustomUser as User
from core.views import get_tokens_for_user


@pytest.fixture
def client():
    """Provides a DRF API client for making requests in tests."""
    return APIClient()


@pytest.fixture
def user_factory():
    """A factory to create user instances."""

    def _create_user(**kwargs):
        defaults = {
            "email": "test@example.com",
            "password": "strong-password-123",
            "is_email_verified": True,
        }
        defaults.update(kwargs)
        if "is_staff" in defaults or "is_superuser" in defaults:
            return User.objects.create_superuser(**defaults)
        return User.objects.create_user(**defaults)

    return _create_user


@pytest.mark.django_db
class TestAuthViewSet:
    """
    Comprehensive tests for the AuthViewSet, covering all custom actions.
    """

    def test_otp_request_success(self, client, mocker):
        """
        Ensures a valid OTP request successfully triggers OTP sending and sets session.
        """
        # Mock the OTP service to prevent actual sending
        mock_send_otp = mocker.patch(
            "core.services.OTPService.send_otp", return_value=True
        )

        url = reverse("auth-otp-request")
        data = {"target": "new.user@example.com", "purpose": "register"}

        response = client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["detail"] == "OTP sent successfully."

        # Verify the service was called with correct parameters
        mock_send_otp.assert_called_once_with(
            target="new.user@example.com", purpose="register", channel="email"
        )

        # Verify session is populated
        assert client.session["otp_target"] == "new.user@example.com"
        assert client.session["otp_purpose"] == "register"

    def test_otp_request_throttled(self, client, user_factory, mocker):
        """
        Ensures the view returns 429 if the OTP service indicates a cooldown.
        """
        user_factory(email="another.user@example.com")

        # Mock the OTP service to simulate a rate-limit hit
        mocker.patch("core.services.OTPService.send_otp", return_value=False)

        url = reverse("auth-otp-request")
        data = {"target": "another.user@example.com", "purpose": "login"}

        response = client.post(url, data)

        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Please wait" in response.data["detail"]

    def test_otp_verify_register_success(self, client, mocker):
        """
        Tests successful OTP verification for a new user registration.
        """
        # Setup session and mock the OTP service
        session = client.session
        session["otp_target"] = "register.me@example.com"
        session["otp_purpose"] = "register"
        session.save()

        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        url = reverse("auth-otp-verify")
        response = client.post(url, {"code": "123456"})

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]

        # Verify that a new user was created
        assert User.objects.filter(email="register.me@example.com").exists()

    def test_otp_verify_login_success(self, client, user_factory, mocker):
        """
        Tests successful OTP verification for an existing user login.
        """
        user = user_factory(email="login.me@example.com")

        session = client.session
        session["otp_target"] = "login.me@example.com"
        session["otp_purpose"] = "login"
        session.save()

        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        url = reverse("auth-otp-verify")
        response = client.post(url, {"code": "123456"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["user_id"] == user.id
        assert User.objects.count() == 1  # No new user should be created

    def test_login_success(self, client, user_factory):
        """
        Tests traditional login with correct credentials.
        """
        user = user_factory(email="login@example.com", password="password123")
        url = reverse("auth-login")
        data = {"login": "login@example.com", "password": "password123"}

        response = client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert response.data["user_id"] == user.id

    def test_login_failure_wrong_password(self, client, user_factory):
        """
        Tests traditional login with incorrect credentials.
        """
        user_factory(email="login@example.com", password="password123")
        url = reverse("auth-login")
        data = {"login": "login@example.com", "password": "wrong-password"}

        response = client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_full_flow(self, client, user_factory, mocker):
        """
        Tests the entire password reset flow from request to setting a new password.
        """
        user = user_factory(email="reset.my.password@example.com")

        # 1. Request Reset
        mocker.patch("core.services.OTPService.send_otp", return_value=True)
        request_url = reverse("auth-password-reset-request")
        client.post(request_url, {"target": "reset.my.password@example.com"})

        # 2. Verify OTP
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )
        verify_url = reverse("auth-password-reset-verify")
        verify_response = client.post(verify_url, {"code": "123456"})

        assert verify_response.status_code == status.HTTP_200_OK
        reset_token = verify_response.data["reset_token"]

        # 3. Set New Password
        set_url = reverse("auth-password-reset-set")
        set_data = {
            "reset_token": reset_token,
            "password": "new-secure-password",
            "password_confirm": "new-secure-password",
        }
        set_response = client.post(set_url, set_data)

        assert set_response.status_code == status.HTTP_200_OK

        # Verify the password was actually changed
        user.refresh_from_db()
        assert user.check_password("new-secure-password") is True

    def test_profile_complete_success(self, client, user_factory):
        """
        Tests that an authenticated user can complete their profile.
        """
        user = user_factory(email="profile@example.com", first_name="")
        client.force_authenticate(user=user)

        url = reverse("auth-profile-complete")
        data = {"first_name": "Updated", "last_name": "Name"}

        response = client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["full_name"] == "Updated Name"

        user.refresh_from_db()
        assert user.first_name == "Updated"

    def test_logout_success(self, client, user_factory, mocker):
        """
        Tests that a user can successfully log out by blacklisting their refresh token.
        """
        user = user_factory()
        client.force_authenticate(user=user)

        # Mock the RefreshToken blacklisting process
        mock_blacklist = mocker.patch(
            "rest_framework_simplejwt.tokens.RefreshToken.blacklist"
        )

        tokens = get_tokens_for_user(user)
        refresh_token = tokens["refresh"]

        url = reverse("auth-logout")
        data = {"refresh": refresh_token}

        response = client.post(url, data)

        assert response.status_code == status.HTTP_200_OK
        mock_blacklist.assert_called_once()


@pytest.mark.django_db
class TestUserViewSet:
    """

    Tests for the UserViewSet, focusing on permissions.
    """

    def test_admin_can_list_users(self, client, user_factory):
        """
        Ensures that a user with admin/staff privileges can list all users.
        """
        user_factory(email="user1@example.com")
        user_factory(email="user2@example.com")

        admin_user = user_factory(email="admin@example.com", is_staff=True)
        client.force_authenticate(user=admin_user)

        url = reverse("users-list")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3  # All three users should be listed

    def test_regular_user_cannot_list_users(self, client, user_factory):
        """
        Ensures that a non-admin user receives a 403 Forbidden error.
        """
        regular_user = user_factory(email="regular@example.com")
        client.force_authenticate(user=regular_user)

        url = reverse("users-list")
        response = client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_user_cannot_list_users(self, client):
        """
        Ensures that an unauthenticated user receives a 403 Forbidden error.
        """
        url = reverse("users-list")
        response = client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
