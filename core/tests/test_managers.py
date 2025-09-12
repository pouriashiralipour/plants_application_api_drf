import pytest

from core.models import CustomUser


@pytest.mark.django_db
class TestCustomManager:

    def test_create_user_with_email(self):
        user = CustomUser.objects.create_user(email="test@example.com", password="pw1")
        assert user.email == "test@example.com"
        assert user.username is not None
        assert user.check_password("pw1")
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_with_phone(self):
        user = CustomUser.objects.create_user(
            phone_number="09121234567", password="pw1"
        )
        assert user.phone_number == "+989121234567"
        assert user.username is not None
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_no_identifier_raises_error(self):
        with pytest.raises(
            ValueError, match="Either Email or Phone number must be set"
        ):
            CustomUser.objects.create_user(password="pw1")

    def test_create_superuser(self):
        admin = CustomUser.objects.create_superuser(
            email="admin@example.com", password="adminpw"
        )
        assert admin.email == "admin@example.com"
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_missing_identifier_raises_error(self):
        with pytest.raises(
            ValueError, match="Superuser must have an email or phone number"
        ):
            CustomUser.objects.create_superuser(password="adminpw")

    def test_create_superuser_flags_must_be_true(self):
        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            CustomUser.objects.create_superuser(
                email="a@a.com", password="pw", is_staff=False
            )

        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            CustomUser.objects.create_superuser(
                email="a@a.com", password="pw", is_superuser=False
            )

    def test_find_by_identifier(self):
        user = CustomUser.objects.create_user(
            email="findme@example.com", phone_number="09121112233"
        )

        found_by_email = CustomUser.objects.find_by_identifier("findme@example.com")
        assert found_by_email == user

        found_by_phone = CustomUser.objects.find_by_identifier("0912-111-2233")
        assert found_by_phone == user

        not_found = CustomUser.objects.find_by_identifier("no-one@example.com")
        assert not_found is None

    def test_get_or_create_by_identifier_gets_existing_user(self):
        user = CustomUser.objects.create_user(email="getme@example.com")

        found_user, created = CustomUser.objects.get_or_create_by_identifier(
            "getme@example.com"
        )
        assert found_user == user
        assert created is False

    def test_get_or_create_by_identifier_creates_new_user(self):
        assert CustomUser.objects.count() == 0

        new_user_email, created_email = CustomUser.objects.get_or_create_by_identifier(
            "new@example.com"
        )
        assert CustomUser.objects.count() == 1
        assert created_email is True
        assert new_user_email.is_email_verified is True
        assert new_user_email.is_phone_verified is False

        new_user_phone, created_phone = CustomUser.objects.get_or_create_by_identifier(
            "09359876543"
        )
        assert CustomUser.objects.count() == 2
        assert created_phone is True
        assert new_user_phone.phone_number == "+989359876543"
        assert new_user_phone.is_email_verified is False
        assert new_user_phone.is_phone_verified is True
