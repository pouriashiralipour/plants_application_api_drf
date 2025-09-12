import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


class TestAuthViewSet:

    def test_otp_request_register_success(self, api_client, mocker):
        mock_send_otp = mocker.patch(
            "core.services.OTPService.send_otp", return_value=True
        )
        url = reverse("auth-otp-request")
        data = {"target": "newuser@example.com", "purpose": "register"}

        response = api_client.post(url, data)

        assert response.status_code == 200
        assert "OTP sent successfully" in response.data["detail"]
        mock_send_otp.assert_called_once()
        assert api_client.session["otp_target"] == "newuser@example.com"
        assert api_client.session["otp_purpose"] == "register"

    def test_otp_request_cooldown_failure(self, api_client, mocker):
        UserFactory(email="test@example.com")

        mocker.patch("core.services.OTPService.send_otp", return_value=False)
        url = reverse("auth-otp-request")
        data = {"target": "test@example.com", "purpose": "login"}

        response = api_client.post(url, data)

        assert response.status_code == 429
        assert "Please wait before requesting a new OTP" in response.data["detail"]

    def test_otp_verify_register_success(self, api_client, mocker):
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        session = api_client.session
        session["otp_target"] = "verify@example.com"
        session["otp_purpose"] = "register"
        session.save()

        url = reverse("auth-otp-verify")
        data = {"code": "123456"}

        response = api_client.post(url, data)

        assert response.status_code == 200
        assert "tokens" in response.data
        assert "user_id" in response.data
        assert "otp_target" not in api_client.session

    def test_otp_verify_login_success(self, api_client, mocker):
        user = UserFactory(email="login@example.com")
        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )

        session = api_client.session
        session["otp_target"] = "login@example.com"
        session["otp_purpose"] = "login"
        session.save()

        url = reverse("auth-otp-verify")
        data = {"code": "123456"}

        response = api_client.post(url, data)

        assert response.status_code == 200
        assert response.data["user_id"] == user.id

    def test_login_success(self, api_client):
        user = UserFactory(
            password="strongpass123", email="login@example.com", is_email_verified=True
        )
        url = reverse("auth-login")
        data = {"login": "login@example.com", "password": "strongpass123"}

        response = api_client.post(url, data)

        assert response.status_code == 200
        assert "tokens" in response.data
        assert response.data["user_id"] == user.id

    def test_login_failure_wrong_password(self, api_client):
        UserFactory(password="strongpass123", email="login@example.com")
        url = reverse("auth-login")
        data = {"login": "login@example.com", "password": "wrongpassword"}

        response = api_client.post(url, data)

        assert response.status_code == 400
        assert "Invalid credentials" in str(response.data)

    def test_password_reset_flow_success(self, api_client, mocker):
        user = UserFactory(email="reset@example.com", password="oldpassword")

        mocker.patch("core.services.OTPService.send_otp", return_value=True)
        request_url = reverse("auth-password-reset-request")
        response = api_client.post(request_url, {"target": "reset@example.com"})
        assert response.status_code == 200
        assert api_client.session["reset_target"] == "reset@example.com"

        mocker.patch(
            "core.services.OTPService.verify_otp", return_value={"code": "123456"}
        )
        verify_url = reverse("auth-password-reset-verify")
        response = api_client.post(verify_url, {"code": "123456"})
        assert response.status_code == 200
        assert api_client.session["reset_user_id"] == user.id

        set_url = reverse("auth-password-reset-set")
        data = {
            "password": "newstrongpassword",
            "password_confirm": "newstrongpassword",
        }
        response = api_client.post(set_url, data)
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.check_password("newstrongpassword") is True
        assert "reset_user_id" not in api_client.session

    def test_profile_complete_success(self, api_client):
        user = UserFactory()
        api_client.force_authenticate(user=user)

        url = reverse("auth-profile-complete")
        data = {"first_name": "Updated Name", "nickname": "UpdatedNick"}

        response = api_client.patch(url, data)

        user.refresh_from_db()
        assert response.status_code == 200
        assert user.first_name == "Updated Name"
        assert user.nickname == "UpdatedNick"

    def test_profile_complete_unauthenticated_fails(self, api_client):
        url = reverse("auth-profile-complete")
        data = {"first_name": "Updated Name"}

        response = api_client.patch(url, data)

        assert response.status_code == 401


class TestUserViewSet:

    def test_list_users_as_admin_success(self, api_client):
        UserFactory.create_batch(3)
        admin_user = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin_user)

        url = reverse("users-list")
        response = api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) == 4

    def test_list_users_as_normal_user_fails(self, api_client):
        normal_user = UserFactory()
        api_client.force_authenticate(user=normal_user)

        url = reverse("users-list")
        response = api_client.get(url)

        assert response.status_code == 403

    def test_retrieve_user_as_admin_success(self, api_client):
        user_to_view = UserFactory()
        admin_user = UserFactory(is_staff=True)
        api_client.force_authenticate(user=admin_user)

        url = reverse("users-detail", kwargs={"pk": user_to_view.pk})
        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["id"] == user_to_view.id
