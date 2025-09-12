"""
Custom user model for authentication with email or Iranian phone number.

This module defines a Django `AbstractUser` subclass (`CustomUser`) that replaces
the default username-based authentication system. Instead, users authenticate
using **email** (primary identifier) or **phone number** (Iranian mobile format).

Features:
    - Unique UUID-based username (non-editable, hidden from the user).
    - Authentication via `email` (primary) or `phone_number`.
    - Automatic normalization of `email` (lowercase, trimmed).
    - Automatic normalization of `phone_number` into `+98XXXXXXXXXX` format.
    - Optional profile metadata (nickname, gender, profile picture, date of birth).
    - Email/phone verification flags.
    - Custom manager (`CustomManager`) for flexible user creation.

Example:
    >>> from myapp.models import CustomUser
    >>> user = CustomUser.objects.create_user(
    ...     email="Test@Example.com",
    ...     phone_number="09123456789",
    ...     password="securepassword123"
    ... )
    >>> user.email
    'test@example.com'
    >>> user.phone_number
    '+989123456789'
    >>> user.full_name
    ''
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomManager
from .utils import normalize_iran_phone, phone_validator


class CustomUser(AbstractUser):
    """
    Custom user model with email or Iranian phone number as unique identifiers.

    This model extends Django's `AbstractUser` but modifies its behavior:
        - `email` is the primary login field (`USERNAME_FIELD`).
        - `username` is auto-generated using UUID and hidden from users.
        - Either `email` or `phone_number` must be provided for account creation.
        - Data is normalized before saving (lowercase emails, formatted phone numbers).
        - Additional optional fields: nickname, gender, profile picture, date of birth.

    Attributes:
        username (str): Auto-generated UUID-based identifier (hidden from end users).
        email (str): User's unique email address (primary identifier).
        phone_number (str): User’s unique Iranian phone number. Validated and normalized.
        nickname (str): Optional display name or alias.
        gender (str): Optional gender, choices are "Male" or "Female".
        profile_pic (ImageField): Optional profile picture, stored under `profile_pics/`.
        date_of_birth (date): Optional date of birth.
        is_email_verified (bool): Whether the email address has been verified.
        is_phone_verified (bool): Whether the phone number has been verified.
        USERNAME_FIELD (str): Set to "email" for authentication.
        REQUIRED_FIELDS (list): Empty, since email is the main required field.

    Manager:
        objects (CustomManager): Handles user and superuser creation with proper validation.

    Meta:
        verbose_name (str): Human-readable singular name ("user").
        verbose_name_plural (str): Human-readable plural name ("users").
    """

    GENDER_CHOICE = [("Male", _("Male")), ("Female", _("Female"))]

    username = models.CharField(
        max_length=150,
        unique=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("username"),
    )

    email = models.EmailField(
        max_length=254, unique=True, blank=True, null=True, verbose_name=_("email")
    )
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[phone_validator],
        verbose_name=_("phone_number"),
    )
    nickname = models.CharField(
        max_length=80, blank=True, null=True, verbose_name=_("nickname")
    )
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICE,
        blank=True,
        null=True,
        verbose_name=_("gender"),
    )
    profile_pic = models.ImageField(
        upload_to="profile_pics/",
        blank=True,
        null=True,
        verbose_name=_("profile picture"),
    )
    date_of_birth = models.DateField(
        verbose_name=_("date_of_birth"), blank=True, null=True
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomManager()

    def save(self, *args, **kwargs):
        """
        Normalize and save the user instance.

        - Converts `email` to lowercase and strips spaces.
        - Normalizes `phone_number` into Iranian standard format (`+98XXXXXXXXXX`).
        - Saves the model instance to the database.

        Args:
            *args: Positional arguments passed to the base `save`.
            **kwargs: Keyword arguments passed to the base `save`.
        """

        if self.email:
            self.email = self.email.strip().lower()
        if self.phone_number:
            self.phone_number = normalize_iran_phone(self.phone_number)

        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return a human-readable representation of the user.

        Priority order:
            1. Email (if available)
            2. Phone number (if available)
            3. UUID (as fallback)

        Returns:
            str: Readable identifier for the user.
        """

        return self.email or self.phone_number or str(self.id)

    @property
    def full_name(self):
        """
        Return the user’s full name.

        Concatenates `first_name` and `last_name`, trimming extra spaces.

        Returns:
            str: Full name if available, otherwise an empty string.
        """
        parts = [self.first_name.strip(), self.last_name.strip()]
        return " ".join(part for part in parts if part)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
