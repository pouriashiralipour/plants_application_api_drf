"""
Custom user manager for handling user creation with email or phone number.

This module provides a custom `BaseUserManager` implementation (`CustomManager`)
that supports authentication using either an email address or an Iranian phone
number. It ensures that user data is normalized and consistent during creation.

Features:
    - Users can be created with either email, phone number, or both.
    - Emails are normalized using Django’s built-in utilities.
    - Iranian phone numbers are normalized using a custom utility (`normalize_iran_phone`).
    - Automatically generates a UUID-based username if none is provided.
    - Superusers must always have either an email or phone number.

Example:
    >>> from myapp.models import CustomUser
    >>> user = CustomUser.objects.create_user(
    ...     email="test@example.com", password="securepassword123"
    ... )
    >>> user.email
    'test@example.com'

    >>> su = CustomUser.objects.create_superuser(
    ...     phone_number="09123456789", password="supersecure"
    ... )
    >>> su.phone_number
    '+989123456789'
"""

import uuid

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

from .utils import normalize_iran_phone


class CustomManager(BaseUserManager):
    """
    Custom manager for handling user creation with email or phone number.

    This manager overrides Django's default user creation logic to support
    both email and phone number as identifiers. It ensures consistency in
    user data and enforces proper validation for superusers.

    Methods:
        create_user(password=None, **extra_fields):
            Creates and saves a regular user. Requires at least one of
            `email` or `phone_number`.

        create_superuser(password, **extra_fields):
            Creates and saves a superuser. Enforces that `is_staff` and
            `is_superuser` are set to True, and requires at least one
            identifier (email or phone number).
    """

    def create_user(self, password=None, **extra_fields):
        """
        Create and return a new user with the given credentials.

        Args:
            password (str, optional): The raw password for the user.
                If None, the user will be created without a password.
            **extra_fields: Additional fields for the user model, which may include:
                - email (str, optional): The user’s email address.
                - phone_number (str, optional): The user’s Iranian phone number.
                - username (str, optional): If not provided, a UUID-based username will be assigned.
                - Any other fields required by the custom user model.

        Raises:
            ValueError: If neither `email` nor `phone_number` is provided.

        Returns:
            CustomUser: The created user instance.
        """

        if not extra_fields.get("email") and not extra_fields.get("phone_number"):
            raise ValueError(_("Either Email or Phone number must be set"))

        if email := extra_fields.get("email"):
            extra_fields["email"] = self.normalize_email(email)
        if phone_number := extra_fields.get("phone_number"):
            extra_fields["phone_number"] = normalize_iran_phone(phone_number)

        if "username" not in extra_fields:
            extra_fields["username"] = str(uuid.uuid4())

        user = self.model(**extra_fields)

        if password:
            user.set_password(password)

        user.save(using=self._db)
        return user

    def create_superuser(self, password, **extra_fields):
        """
        Create and return a new superuser with the given credentials.

        Superusers must always have either an email or phone number,
        and must have `is_staff=True` and `is_superuser=True`.

        Args:
            password (str): The raw password for the superuser.
            **extra_fields: Additional fields for the superuser model, such as:
                - email (str, optional): The superuser’s email address.
                - phone_number (str, optional): The superuser’s Iranian phone number.
                - username (str, optional): Auto-generated if not provided.
                - is_staff (bool): Must be True.
                - is_superuser (bool): Must be True.
                - is_active (bool): Defaults to True.

        Raises:
            ValueError:
                - If `is_staff` is not True.
                - If `is_superuser` is not True.
                - If neither `email` nor `phone_number` is provided.

        Returns:
            CustomUser: The created superuser instance.
        """

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        # A superuser must have a primary identifier to log into the admin panel
        if not extra_fields.get("email") and not extra_fields.get("phone_number"):
            raise ValueError(_("Superuser must have an email or phone number."))

        return self.create_user(password, **extra_fields)
