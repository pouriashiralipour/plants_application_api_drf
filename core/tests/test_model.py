import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestCustomUserModel:
    def test_email_is_normalized_on_save(self):
        user = User.objects.create_user(email="  TestUSER@EXAMPLE.com  ")
        user.save()
        assert user.email == "testuser@example.com"

    def test_phone_number_is_normalized_on_save(self):
        user = User.objects.create_user(phone_number="09351234567")
        user.save()
        assert user.phone_number == "+989351234567"

    def test_str_representation(self):
        user_with_email = User.objects.create(email="test@example.com")
        user_with_phone = User.objects.create(phone_number="+989123456789")
        user_fallback = User.objects.create()

        assert str(user_with_email) == "test@example.com"
        assert str(user_with_phone) == "+989123456789"
        assert str(user_fallback) == str(user_fallback.id)

    def test_full_name_property(self):
        user = User(first_name="  John  ", last_name="  Doe  ")
        assert user.full_name == "John Doe"

        user_no_name = User()
        assert user_no_name.full_name == ""

    def test_default_verification_status_is_false(self):
        user = User.objects.create_user(email="new@user.com")
        assert user.is_email_verified is False
        assert user.is_phone_verified is False

    def test_username_field_has_bug_with_default_value(self):
        user1 = User.objects.create(email="user1@example.com")
        user2 = User.objects.create(email="user2@example.com")

        assert (
            user1.username != user2.username
        ), "باگ: username برای کاربران جدید یکسان است!"
