import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomManager:
    def test_create_user_with_email_successful(self):
        user = User.objects.create_user(
            email="test@example.com", password="somepassword123"
        )
        assert user.email == "test@example.com"
        assert user.username is not None
        assert user.check_password("somepassword123")
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_with_phone_successful(self):
        user = User.objects.create_user(
            phone_number="09123456789", password="somepassword123"
        )
        assert user.phone_number == "+989123456789"
        assert user.check_password("somepassword123")

    def test_create_user_without_identifier_raises_error(self):
        with pytest.raises(
            ValueError, match="Either Email or Phone number must be set"
        ):
            User.objects.create_user(password="somepassword123")

    def test_create_superuser_successful(self):
        admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpassword"
        )
        assert admin_user.email == "admin@example.com"
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
        assert admin_user.is_active is True
        assert admin_user.check_password("adminpassword")

    def test_create_superuser_not_staff_raises_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            User.objects.create_superuser(
                email="admin@example.com", password="pw", is_staff=False
            )

    def test_create_superuser_not_superuser_raises_error(self):
        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            User.objects.create_superuser(
                email="admin@example.com", password="pw", is_superuser=False
            )

    def test_create_superuser_without_identifier_raises_error(self):
        with pytest.raises(
            ValueError, match="Superuser must have an email or phone number."
        ):
            User.objects.create_superuser(password="pw")
