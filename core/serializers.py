"""
Serializers for user authentication, OTP handling, and profile management.

This module provides a set of Django REST Framework serializers to handle:
    - User profile serialization
    - OTP request and verification
    - Profile completion after registration
    - Standard login with email/phone + password
    - Password reset flow (request, verify, set new password)
    - Identifier (email/phone) change request and verification

Key services/utilities used:
    - OTPService: For generating and verifying OTP codes.
    - normalize_iran_phone: For standardizing Iranian phone numbers.
    - Django sessions: For storing temporary OTP/Reset identifiers.

Each serializer enforces proper validation and business rules, ensuring
secure user authentication and profile management.

Example:
    >>> serializer = OTPRequestSerializer(data={"target": "09123456789", "purpose": "login"})
    >>> serializer.is_valid()
    True
    >>> serializer.validated_data
    {'target': '+989123456789', 'purpose': 'login'}
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .constants import OTPPurpose
from .services import OTPService
from .utils import normalize_iran_phone

# Fetch the custom User model .
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for reading user profile information.

    Exposes a subset of user fields for profile display or API consumption.
    Typically used for returning authenticated user data.

    Meta:
        model (CustomUser): The user model in use.
        fields (list): The user fields exposed via API.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone_number",
            "profile_pic",
            "date_of_birth",
            "nickname",
            "gender",
            "is_email_verified",
            "is_phone_verified",
        ]


class OTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP codes (registration or login).

    Fields:
        target (str): Email or phone number identifier for the OTP.
        purpose (str): The purpose of the OTP (register/login).

    Validation flow:
        - Normalize email/phone input.
        - Detect delivery channel ("email" or "sms").
        - For "register": target must not already exist.
        - For "login": target must already exist.
    """

    target = serializers.CharField(write_only=True)
    purpose = serializers.ChoiceField(write_only=True, choices=OTPPurpose.choices)

    def validate_target(self, value):
        """
        Validate and normalize the target identifier.

        - For emails: validation via DRF's `EmailField`.
        - For phones: normalization into +98XXXXXXXXXX.
        - Save channel in context for later use.
        - Enforce "register" or "login" rules.

        Raises:
            serializers.ValidationError: If validation fails.
        """

        value = value.strip().lower()

        # Detect whether it's an email or phone number
        if "@" in value:
            serializers.EmailField().run_validation(value)
            self.context["channel"] = "email"
        else:
            value = normalize_iran_phone(value)
            self.context["channel"] = "sms"

        # Check if user exists with this identifier
        user_exists = (
            User.objects.filter(email=value).exists()
            or User.objects.filter(phone_number=value).exists()
        )

        purpose = self.initial_data.get("purpose")

        # Register: prevent duplicate identifiers
        if purpose == OTPPurpose.REGISTER and user_exists:
            if user_exists:
                self.context["user_exists"] = True
            else:
                self.context["user_exists"] = False

        # Login: ensure user exists
        elif purpose == OTPPurpose.LOGIN:
            if not user_exists:
                self.context["user_does_not_exist"] = True
            else:
                self.context["user_does_not_exist"] = False

        return value


class OTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP codes.

    Fields:
        code (str): The 6-digit OTP entered by the user.

    Validation flow:
        - Read `otp_target` and `otp_purpose` from session.
        - Verify OTP using `OTPService`.
        - Reject if invalid or expired.
    """

    code = serializers.CharField(max_length=6, write_only=True)

    def validate(self, attrs):
        """
        Validate the OTP code.

        Raises:
            serializers.ValidationError: If OTP is invalid, expired, or missing.

        Returns:
            dict: Validated attributes (if OTP is correct).
        """

        request = self.context["request"]
        code = attrs["code"]

        target = request.session.get("otp_target")
        purpose = request.session.get("otp_purpose")

        if not target or not purpose:
            raise serializers.ValidationError(
                _("No active OTP request found. Please request a new code.")
            )

        otp_data = OTPService.verify_otp(target=target, code=code, purpose=purpose)
        if not otp_data:
            raise serializers.ValidationError(_("Invalid or expired OTP."))

        return attrs


class ProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Serializer for completing a user profile after registration.

    Required fields:
        - first_name, last_name, date_of_birth, password
    Optional fields:
        - nickname, gender
        - email/phone_number (depending on what was initially used)

    Business rules:
        - If email already exists → make email read-only, require phone.
        - If phone already exists → make phone read-only, require email.
        - Ensure uniqueness of identifiers.
        - Mark identifiers as verified once provided.
    """

    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "date_of_birth",
            "gender",
            "nickname",
            "email",
            "phone_number",
            "password",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "date_of_birth": {"required": True},
            "email": {"required": False},
            "phone_number": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        """
        Customize field requirements based on the authenticated user.

        - If user has email, make it read-only and require phone_number.
        - If user has phone_number, make it read-only and require email.
        """

        super().__init__(*args, **kwargs)

        if "request" in self.context:
            user = self.context["request"].user

            # If user already has email → require phone
            if user.email:
                self.fields["email"].read_only = True
                self.fields["phone_number"].required = True

            # If user already has phone → require email
            elif user.phone_number:
                self.fields["phone_number"].read_only = True
                self.fields["email"].required = True

    def validate(self, attrs):
        """Ensure email/phone uniqueness if being added."""

        user = self.context["request"].user
        email = attrs.get("email", "").strip().lower()
        phone = normalize_iran_phone(attrs.get("phone_number", ""))

        if email and not user.email:
            if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                raise serializers.ValidationError(
                    {"email": "This email is already in use."}
                )

        if phone and not user.phone_number:
            if User.objects.filter(phone_number=phone).exclude(pk=user.pk).exists():
                raise serializers.ValidationError(
                    {"phone_number": "This phone number is already in use."}
                )
        return attrs

    def update(self, instance, validated_data):
        """
        Update user profile and set password.

        - Hash password if provided.
        - Update fields.
        - Mark email/phone as verified if added.
        """

        password = validated_data.pop("password", None)

        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if "email" in validated_data and not instance.is_email_verified:
            instance.is_email_verified = True
        if "phone_number" in validated_data and not instance.is_phone_verified:
            instance.is_phone_verified = True

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """
    Serializer for logging in a user with email or phone.

    Fields:
        login (str): Email or phone number.
        password (str): User password.

    Validation:
        - Normalize identifier.
        - Lookup user.
        - Validate password.
        - Ensure account is verified.
    """

    login = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Validate login credentials and attach `user` to validated data."""

        login = attrs["login"].strip().lower()
        password = attrs["password"]

        # Try email login
        if "@" in login:
            user = User.objects.filter(email=login).first()
        else:
            # Try phone login
            phone_normalize = normalize_iran_phone(login)
            user = User.objects.filter(phone_number=phone_normalize).first()

        if user is None or not user.check_password(password):
            raise ValidationError(_("The login information was incorrect."))

        if not (user.is_email_verified or user.is_phone_verified):
            raise ValidationError(_("Account not verified."))

        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset via OTP.

    Fields:
        target (str): Email or phone of the account.

    Validation:
        - Normalize identifier.
        - Ensure user exists.
    """

    target = serializers.CharField(write_only=True)

    def validate_target(self, value):
        """Ensure reset target belongs to a valid user."""

        if "@" in value:
            serializers.EmailField().run_validation(value)
            self.context["channel"] = "email"
        else:
            value = normalize_iran_phone(value)
            self.context["channel"] = "sms"

        user_exists = (
            User.objects.filter(email=value).exists()
            or User.objects.filter(phone_number=value).exists()
        )
        if not user_exists:
            raise serializers.ValidationError(_("No user found with this identifier."))

        return value


class PasswordResetVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a password reset OTP.

    Fields:
        code (str): 6-digit OTP code.

    Validation:
        - Verify OTP correctness.
        - Ensure target exists.
        - Store user ID in session for next step.
    """

    code = serializers.CharField(max_length=6, write_only=True)

    def validate(self, attrs):
        """Verify reset OTP and bind reset user ID to session."""

        request = self.context["request"]
        code = attrs["code"]
        target = request.session.get("reset_target")

        if not target:
            raise serializers.ValidationError(
                _("No active password reset request found.")
            )

        otp_data = OTPService.verify_otp(
            target=target, code=code, purpose="reset_password"
        )
        if not otp_data:
            raise serializers.ValidationError(_("Invalid or expired OTP."))

        # Ensure a user exists with this identifier
        user = (
            User.objects.filter(email=target).first()
            or User.objects.filter(phone_number=target).first()
        )
        if not user:
            raise serializers.ValidationError(_("User not found."))

        # Store user ID in session for use in set-password step
        request.session["reset_user_id"] = user.id
        return attrs


class PasswordResetSetPasswordSerializer(serializers.Serializer):
    """
    Serializer for setting a new password after a reset.

    Fields:
        password (str): New password (min. 8 chars).
        password_confirm (str): Confirm password.
        reset_token (str): A reset token (for additional verification).
    """

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    reset_token = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Ensure both passwords match."""

        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": _("Passwords do not match.")}
            )

        return attrs


class IdentifierChangeRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting identifier (email/phone) change.

    Fields:
        target (str): New email or phone number.

    Validation:
        - Ensure proper format (email or normalized phone).
        - Ensure uniqueness (no other account uses it).
    """

    target = serializers.CharField(write_only=True)

    def validate_target(self, value):
        """Normalize and ensure new identifier is unique."""
        value = value.strip().lower()
        user = self.context["request"].user

        if "@" in value:
            # Validate email
            serializers.EmailField().run_validation(value)
            if User.objects.filter(email=value).exclude(pk=user.pk).exists():
                raise serializers.ValidationError(
                    _("This email is already in use by another account.")
                )
            self.context["channel"] = "email"
        else:
            # Validate phone
            value = normalize_iran_phone(value)
            if User.objects.filter(phone_number=value).exclude(pk=user.pk).exists():
                raise serializers.ValidationError(
                    _("This phone number is already in use by another account.")
                )
            self.context["channel"] = "sms"

        return value


class IdentifierChangeVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying identifier (email/phone) change.

    Fields:
        code (str): 6-digit OTP code.
    """

    code = serializers.CharField(max_length=6, write_only=True)
