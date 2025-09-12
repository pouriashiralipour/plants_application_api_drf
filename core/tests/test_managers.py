"""
Unit tests for the `CustomManager` in the `CustomUser` model.

This module verifies that the custom manager methods for creating users and
superusers, as well as lookup utilities, behave correctly.

Tested methods include:
    - create_user
    - create_superuser
    - find_by_identifier
    - get_or_create_by_identifier

It also ensures:
    - Proper normalization of email and Iranian phone numbers.
    - Default values for flags (`is_staff`, `is_superuser`, verification flags).
    - Validation errors are raised when required identifiers are missing.
"""

import pytest

from core.models import CustomUser


@pytest.mark.django_db
class TestCustomManager:
    """
    Test suite for `CustomUser`'s custom manager (`CustomManager`).

    Each test validates one aspect of user creation, superuser creation,
    or identifier-based lookup functionality.
    """

    def test_create_user_with_email(self):
        """
        Test creating a user with only an email.

        Ensures:
            - Email is set correctly.
            - Username is auto-generated.
            - Password is hashed correctly.
            - `is_staff` and `is_superuser` are False by default.
        """

        user = CustomUser.objects.create_user(email="test@example.com", password="pw1")
        assert user.email == "test@example.com"
        assert user.username is not None
        assert user.check_password("pw1")
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_with_phone(self):
        """
        Test creating a user with only a phone number.

        Ensures:
            - Phone number is normalized to standard Iranian format.
            - Username is auto-generated.
            - Default flags are correct.
        """

        user = CustomUser.objects.create_user(
            phone_number="09121234567", password="pw1"
        )
        assert user.phone_number == "+989121234567"
        assert user.username is not None
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_no_identifier_raises_error(self):
        """
        Test that creating a user without email or phone number raises a ValueError.
        """

        with pytest.raises(
            ValueError, match="Either Email or Phone number must be set"
        ):
            CustomUser.objects.create_user(password="pw1")

    def test_create_superuser(self):
        """
        Test creating a superuser with proper flags and email set.
        """

        admin = CustomUser.objects.create_superuser(
            email="admin@example.com", password="adminpw"
        )
        assert admin.email == "admin@example.com"
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_missing_identifier_raises_error(self):
        """
        Test that creating a superuser without email or phone raises a ValueError.
        """

        with pytest.raises(
            ValueError, match="Superuser must have an email or phone number"
        ):
            CustomUser.objects.create_superuser(password="adminpw")

    def test_create_superuser_flags_must_be_true(self):
        """
        Test that superuser creation validates `is_staff` and `is_superuser` flags.

        - Raises error if `is_staff` is False.
        - Raises error if `is_superuser` is False.
        """

        with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
            CustomUser.objects.create_superuser(
                email="a@a.com", password="pw", is_staff=False
            )

        with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
            CustomUser.objects.create_superuser(
                email="a@a.com", password="pw", is_superuser=False
            )

    def test_find_by_identifier(self):
        """
        Test the `find_by_identifier` utility method.

        Ensures:
            - Lookup by email returns the correct user.
            - Lookup by phone (even in unformatted form) returns the correct user.
            - Returns None if no matching user exists.
        """

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
        """
        Test that `get_or_create_by_identifier` retrieves an existing user
        and does not create a new instance.
        """

        user = CustomUser.objects.create_user(email="getme@example.com")

        found_user, created = CustomUser.objects.get_or_create_by_identifier(
            "getme@example.com"
        )
        assert found_user == user
        assert created is False

    def test_get_or_create_by_identifier_creates_new_user(self):
        """
        Test that `get_or_create_by_identifier` creates a new user if none exists.

        Verifies:
            - Count of users increases.
            - Correct verification flags are set based on identifier type.
            - Email vs. phone number logic works correctly.
        """

        assert CustomUser.objects.count() == 0

        # Creating new user with email
        new_user_email, created_email = CustomUser.objects.get_or_create_by_identifier(
            "new@example.com"
        )
        assert CustomUser.objects.count() == 1
        assert created_email is True
        assert new_user_email.is_email_verified is True
        assert new_user_email.is_phone_verified is False

        # Creating new user with phone
        new_user_phone, created_phone = CustomUser.objects.get_or_create_by_identifier(
            "09359876543"
        )
        assert CustomUser.objects.count() == 2
        assert created_phone is True
        assert new_user_phone.phone_number == "+989359876543"
        assert new_user_phone.is_email_verified is False
        assert new_user_phone.is_phone_verified is True
