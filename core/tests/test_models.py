"""
Unit tests for the `CustomUser` model in the core application.

This module verifies:
    - User creation with email and/or phone number.
    - Normalization of email and Iranian phone numbers on save.
    - String representation of the user instance.
    - Full name property behavior.
    - Uniqueness constraints on email and phone number.
    - Superuser creation with proper permissions.

Tools:
    - `pytest` for test structure and assertions.
    - `pytest.mark.django_db` to allow database access for tests.
    - `IntegrityError` to test uniqueness constraints.
"""

import pytest
from django.db.utils import IntegrityError

from core.models import CustomUser


@pytest.mark.django_db
class TestCustomUserModel:
    """
    Test suite for `CustomUser` model.

    Each test validates one specific behavior of the user model,
    including creation, normalization, properties, and constraints.
    """

    def test_user_creation(self):
        """
        Test that a user can be created with email, phone number, and password,
        and that default flags (`is_staff`, `is_superuser`) are False.
        """

        user = CustomUser.objects.create_user(
            email="test@example.com",
            phone_number="09123456789",
            password="password123",
        )

        # Verify that email and phone are correctly saved
        assert user.email == "test@example.com"
        assert user.phone_number == "+989123456789"

        # Verify password hashing
        assert user.check_password("password123")

        # Default staff and superuser flags
        assert user.is_staff is False
        assert user.is_superuser is False

        # Only one user should exist in DB
        assert CustomUser.objects.count() == 1

    def test_normalization_on_save(self):
        """
        Test that email and phone numbers are normalized when a user is saved.

        - Email should be lowercased and trimmed.
        - Iranian phone numbers should be converted to standard format (+98XXXXXXXXXX).
        """

        user = CustomUser.objects.create_user(
            email="  TestCapital@EXAMPLE.COM  ",
            phone_number="0935-123-4567",
            password="password123",
        )
        assert user.email == "testcapital@example.com"
        assert user.phone_number == "+989351234567"

    def test_str_representation(self):
        """
        Test the string representation (`__str__`) of the user model.

        - Uses email if available.
        - Falls back to phone number if email is not set.
        - Uses user ID if neither email nor phone is set.
        """

        user_with_email = CustomUser.objects.create(email="email@test.com")
        user_with_phone = CustomUser.objects.create(phone_number="09121112233")
        user_with_id_only = CustomUser.objects.create()

        assert str(user_with_email) == "email@test.com"
        assert str(user_with_phone) == "+989121112233"
        assert str(user_with_id_only) == str(user_with_id_only.id)

    def test_full_name_property(self):
        """
        Test the `full_name` property.

        - Combines first and last names with proper stripping.
        - Handles cases when only first name or neither name is provided.
        """

        user = CustomUser(first_name="  John ", last_name="  Doe  ")
        assert user.full_name == "John Doe"

        user_no_lastname = CustomUser(first_name="Jane")
        assert user_no_lastname.full_name == "Jane"

        user_no_names = CustomUser()
        assert user_no_names.full_name == ""

    def test_email_uniqueness(self):
        """
        Test that creating two users with the same email raises an IntegrityError.
        """

        CustomUser.objects.create_user(email="unique@example.com", password="p1")

        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(email="unique@example.com", password="p2")

    def test_phone_number_uniqueness(self):
        """
        Test that creating two users with the same phone number raises an IntegrityError.
        """

        CustomUser.objects.create_user(phone_number="09129876543", password="p1")

        with pytest.raises(IntegrityError):
            CustomUser.objects.create_user(phone_number="09129876543", password="p2")

    def test_superuser_creation(self):
        """
        Test that creating a superuser sets `is_staff` and `is_superuser` to True
        and stores the provided email correctly.
        """

        admin = CustomUser.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.email == "admin@example.com"
