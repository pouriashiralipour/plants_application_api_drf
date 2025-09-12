import pytest
from django.db.utils import IntegrityError

from core.models import CustomUser


@pytest.mark.django_db
class TestCustomUserModel:

    def test_user_creation(self):
        user = CustomUser.objects.create_user(
            email="test@example.com",
            phone_number="09123456789",
            password="password123",
        )
        assert user.email == "test@example.com"
        assert user.phone_number == "+989123456789"
        assert user.check_password("password123")
        assert user.is_staff is False
        assert user.is_superuser is False
        assert CustomUser.objects.count() == 1

    def test_normalization_on_save(self):
        user = CustomUser.objects.create_user(
            email="  TestCapital@EXAMPLE.COM  ",
            phone_number="0935-123-4567",
            password="password123",
        )
        assert user.email == "testcapital@example.com"
        assert user.phone_number == "+989351234567"

    def test_str_representation(self):
        user_with_email = CustomUser.objects.create(email="email@test.com")
        user_with_phone = CustomUser.objects.create(phone_number="09121112233")
        user_with_id_only = CustomUser.objects.create()

        assert str(user_with_email) == "email@test.com"
        assert str(user_with_phone) == "+989121112233"
        assert str(user_with_id_only) == str(user_with_id_only.id)

    def test_full_name_property(self):
        user = CustomUser(first_name="  John ", last_name="  Doe  ")
        assert user.full_name == "John Doe"

        user_no_lastname = CustomUser(first_name="Jane")
        assert user_no_lastname.full_name == "Jane"

        user_no_names = CustomUser()
        assert user_no_names.full_name == ""

    def test_email_uniqueness(self):
        CustomUser.objects.create_user(email="unique@example.com", password="p1")

        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(email="unique@example.com", password="p2")

    def test_phone_number_uniqueness(self):
        CustomUser.objects.create_user(phone_number="09129876543", password="p1")

        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(phone_number="09129876543", password="p2")

    def test_superuser_creation(self):
        admin = CustomUser.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.email == "admin@example.com"
