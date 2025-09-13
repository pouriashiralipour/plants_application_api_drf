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
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "OTP Request for Registration (Email) - JSON",
            value={"target": "new.user@example.com", "purpose": "register"},
            description="Use JSON for API calls or form-data for file uploads (if needed).",
        ),
        OpenApiExample(
            "OTP Request for Login (Phone) - Form Data",
            value={
                "target": "09123456789",
                "purpose": "login",
            },
            description="Supports both JSON and form-data inputs. Phone numbers are normalized to +98 format.",
            media_type="multipart/form-data",
        ),
    ],
)
class OTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP codes (registration or login).

    **Input Format**:
    - JSON: `{"target": "email@domain.com", "purpose": "register"}`
    - Form-Data: `target=email@domain.com&purpose=register`

    **Validation Flow**:
    1. Normalize email (lowercase) or phone (+98XXXXXXXXX).
    2. Detect channel: "email" for @-containing, "sms" for phones.
    3. For "register": Target must NOT exist (prevents duplicates).
    4. For "login": Target MUST exist (user lookup).

    **Security Notes**:
    - Rate-limited (5/hour) to prevent abuse.
    - Generic response hides existence to avoid enumeration attacks.
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
            raise serializers.ValidationError(
                _("A user with this identifier already exists.")
            )

        # Login: ensure user exists by raising an error
        elif purpose == OTPPurpose.LOGIN and not user_exists:
            raise serializers.ValidationError(_("No user found with this identifier."))

        return value


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "OTP Verification - JSON",
            value={"code": "123456"},
            description="6-digit code received via email/SMS. Supports JSON only (short input).",
        ),
        OpenApiExample(
            "OTP Verification - Form Data",
            value={"code": "123456"},
            description="Use form-data if integrating with file uploads.",
            media_type="multipart/form-data",
        ),
    ],
)
class OTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP codes.

    **Input Format**:
    - JSON: `{"code": "123456"}`
    - Form-Data: `code=123456`

    **Validation Flow**:
    1. Retrieve `otp_target` and `otp_purpose` from session.
    2. Verify code using OTPService (expires after 5 minutes).
    3. On success: Clear session and proceed to auth.

    **Security Notes**:
    - OTPs are single-use and time-bound.
    - Invalid/expired codes return generic error.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Profile Completion - JSON (Email User Adding Phone)",
            value={
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-15",
                "gender": "Male",
                "nickname": "Johnny",
                "phone_number": "09123456789",  # Required if registered with email
                "password": "StrongPass123!",
            },
            description="For users registered via OTP with email only; phone is required.",
        ),
        OpenApiExample(
            "Profile Update - Form Data (Phone User Adding Email)",
            value={
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "email": "ali@example.com",  # Required if registered with phone
                "password": "NewPass456@",
            },
            description="Partial update (PATCH); supports form-data for profile pics if extended.",
            media_type="multipart/form-data",
        ),
    ],
)
class ProfileCompletionSerializer(serializers.ModelSerializer):
    """
    Serializer for completing a user profile after registration.

    **Input Format**:
    - JSON: Full/partial object as shown.
    - Form-Data: Key-value pairs (useful for future file uploads like profile_pic).

    **Required Fields** (dynamic based on registration method):
    - Always: `first_name`, `last_name`, `date_of_birth`, `password` (min 8 chars).
    - If registered with email: `phone_number` required.
    - If registered with phone: `email` required.
    - Optional: `nickname`, `gender`.

    **Business Rules**:
    1. Existing identifiers are read-only.
    2. New identifiers checked for uniqueness.
    3. Provided identifiers auto-marked as verified.
    4. Password hashed securely.

    **Security Notes**:
    - Requires authentication (JWT).
    - Partial updates allowed (PATCH).
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Login with Email - JSON",
            value={"login": "user@example.com", "password": "StrongPass123!"},
            description="Email-based login. Tokens returned for subsequent requests.",
        ),
        OpenApiExample(
            "Login with Phone - Form Data",
            value={
                "login": "09123456789",
                "password": "StrongPass123!",
            },
            description="Phone normalized automatically. Requires verified account.",
            media_type="multipart/form-data",
        ),
    ],
)
class LoginSerializer(serializers.Serializer):
    """
    Serializer for logging in a user with email or phone.

    **Input Format**:
    - JSON: `{"login": "user@domain.com", "password": "..."}`
    - Form-Data: `login=user@domain.com&password=...`

    **Validation Flow**:
    1. Normalize identifier (email lowercase, phone +98).
    2. Lookup user by email or phone.
    3. Check password hash.
    4. Ensure at least one identifier is verified.

    **Output**: JWT access/refresh tokens + user ID.

    **Security Notes**:
    - Failed logins return generic error (no enumeration).
    - Access token: 60min, Refresh: 1day.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Password Reset Request - JSON (Email)",
            value={"target": "user@example.com"},
            description="Initiates reset; OTP sent if user exists.",
        ),
        OpenApiExample(
            "Password Reset Request - Form Data (Phone)",
            value={"target": "09123456789"},
            description="Generic success hides user existence.",
            media_type="multipart/form-data",
        ),
    ],
)
class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a password reset via OTP.

    **Input Format**:
    - JSON: `{"target": "user@domain.com"}`
    - Form-Data: `target=user@domain.com`

    **Validation Flow**:
    1. Normalize target.
    2. Check user exists (but respond generically).
    3. Send OTP via channel (email/sms).

    **Security Notes**:
    - Rate-limited.
    - Success message is vague to prevent enumeration.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Password Reset Verify - JSON",
            value={"code": "123456"},
            description="Verifies OTP; returns short-lived reset_token (5min).",
        ),
    ],
)
class PasswordResetVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying a password reset OTP.

    **Input Format**: JSON only (simple input): `{"code": "123456"}`

    **Validation Flow**:
    1. Retrieve `reset_target` from session.
    2. Verify OTP for "reset_password" purpose.
    3. Store user ID in session.
    4. Generate signed reset_token (TimestampSigner, 5min expiry).

    **Output**: `reset_token` for next step.

    **Security Notes**:
    - Token is time-bound and signed.
    - Session cleared after use.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Set New Password - JSON",
            value={
                "password": "NewStrongPass123!",
                "password_confirm": "NewStrongPass123!",
                "reset_token": "signed-userid-timestamp",
            },
            description="Must match passwords; token from verify step.",
        ),
    ],
)
class PasswordResetSetPasswordSerializer(serializers.Serializer):
    """
    Serializer for setting a new password after a reset.

    **Input Format**: JSON: `{"password": "...", "password_confirm": "...", "reset_token": "..."}`

    **Validation Flow**:
    1. Ensure passwords match (min 8 chars).
    2. Unsign token (max_age=5min).
    3. Fetch user by ID from token.
    4. Hash and set new password.

    **Security Notes**:
    - Token expires quickly.
    - No session needed here.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Request Identifier Change - JSON (New Email)",
            value={"target": "new.email@example.com"},
            description="Authenticated user only; checks uniqueness.",
        ),
        OpenApiExample(
            "Request Identifier Change - Form Data (New Phone)",
            value={"target": "09876543210"},
            description="OTP sent to NEW identifier.",
            media_type="multipart/form-data",
        ),
    ],
)
class IdentifierChangeRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting identifier (email/phone) change.

    **Input Format**:
    - JSON: `{"target": "new@domain.com"}`
    - Form-Data: `target=new@domain.com`

    **Validation Flow**:
    1. Authenticated user only.
    2. Normalize new target.
    3. Check uniqueness (exclude current user).
    4. Send OTP to NEW target.

    **Security Notes**:
    - Rate-limited.
    - OTP verifies ownership of new identifier.
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Verify Identifier Change - JSON",
            value={"code": "123456"},
            description="Updates identifier if OTP matches; returns updated profile.",
        ),
    ],
)
class IdentifierChangeVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying identifier (email/phone) change.

    **Input Format**: JSON: `{"code": "123456"}`

    **Validation Flow**:
    1. Retrieve pending target from session.
    2. Verify OTP for "change_identifier".
    3. Update user's email/phone and mark verified.
    4. Clear session.

    **Output**: Updated user profile.

    **Security Notes**:
    - Authenticated user only.
    - OTP single-use.
    """

    code = serializers.CharField(max_length=6, write_only=True)
