"""
Authentication and user management viewsets.

This module provides REST API endpoints for handling authentication and
account management using Django REST Framework (DRF) and JWT (SimpleJWT).
It supports OTP-based registration/login, traditional email/phone + password
login, password reset workflows, identifier (email/phone) changes, and
profile completion.

Components:
    - get_tokens_for_user(user): Utility to issue JWT tokens for a given user.
    - OTPThrottle: Custom rate limiter for OTP endpoints.
    - AuthViewSet: ViewSet for handling authentication-related endpoints
      (OTP, login, password reset, profile completion, identifier change).
    - UserViewSet: Admin-only viewset for retrieving user data.

Workflow:
    1. OTP Request → User requests OTP for registration or login.
    2. OTP Verify → User enters OTP, and tokens are issued upon success.
    3. Login → Traditional login with email/phone + password.
    4. Password Reset → Request → Verify OTP → Set new password.
    5. Profile Completion → Fill in or update missing user information.
    6. Identifier Change → Request OTP → Verify → Update email/phone.

This module heavily relies on:
    - Django sessions (for temporary OTP storage).
    - DRF serializers (for validation).
    - OTPService (custom service layer for OTP generation/verification).
    - JWT tokens (for stateless authentication).
"""

from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action, throttle_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .constants import OTPPurpose
from .serializers import (
    IdentifierChangeRequestSerializer,
    IdentifierChangeVerifySerializer,
    LoginSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PasswordResetRequestSerializer,
    PasswordResetSetPasswordSerializer,
    PasswordResetVerifySerializer,
    ProfileCompletionSerializer,
    UserSerializer,
)
from .services import OTPService

# Fetch the custom User model .
User = get_user_model()


def get_tokens_for_user(user):
    """
    Generate JWT refresh and access tokens for the given user.

    Args:
        user (User): The user instance.

    Returns:
        dict: A dictionary containing:
            - "refresh" (str): The refresh token.
            - "access" (str): The access token.

    Example:
        >>> user = User.objects.first()
        >>> tokens = get_tokens_for_user(user)
        >>> tokens["access"]
        'eyJ0eXAiOiJKV1QiLCJhbGci...'
    """

    # Create a new refresh token for the given user
    refresh = RefreshToken.for_user(user)

    # Return both refresh + access token as strings
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class OTPThrottle(AnonRateThrottle):
    """
    Custom rate throttle for OTP requests.

    This prevents abuse of the OTP system by limiting how often
    anonymous users can request new OTP codes.
    """

    # DRF will look for this key in the settings to apply limits (e.g., "otp": "5/minute")
    scope = "otp"


class AuthViewSet(ViewSet):
    """
    A ViewSet that handles authentication and account management.

    Endpoints:
        - otp_request → Request a one-time password (OTP) via email or SMS.
        - otp_verify → Verify the OTP for registration or login.
        - login → Authenticate using email/phone and password.
        - password_reset_request → Request a password reset OTP.
        - password_reset_verify → Verify OTP for password reset.
        - password_reset_set → Set a new password after OTP verification.
        - profile_complete → Update or complete the user profile.
        - logout → Blacklist a refresh token (logout).
        - change_identifier_request → Request OTP for changing email/phone.
        - change_identifier_verify → Verify OTP and update identifier.

    Session Keys Used:
        - "otp_target": Identifier for OTP (email or phone).
        - "otp_purpose": Purpose of the OTP ("register" or "login").
        - "reset_target": Identifier for password reset.
        - "reset_user_id": User ID associated with a password reset.
        - "change_identifier_target": Pending identifier change request.
    """

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    @throttle_classes([OTPThrottle])
    def otp_request(self, request):
        """
        Handle OTP request for registration or login.

        Steps:
            1. Validate target (email/phone) and purpose.
            2. If valid, trigger OTP sending via SMS/Email.
            3. Store target + purpose in session.
            4. Enforce cooldown (rate-limited).

        Request body:
            - target (str): Email or phone number.
            - purpose (str): "register" or "login".

        Returns:
            - 200 OK if OTP sent successfully.
            - 429 Too Many Requests if cooldown active.
        """

        # Validate input using serializer (ensures correct target + purpose)
        serializer = OTPRequestSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)

        # Respond with generic message if user exists/does not exist
        # (to avoid exposing whether an identifier is registered)
        if serializer.context.get("user_exists"):
            return Response(
                {
                    "detail": _(
                        "If an account with these details exists, a verification code will be sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        if serializer.context.get("user_does_not_exist"):
            return Response(
                {
                    "detail": _(
                        "If an account with these details exists, a verification code will be sent."
                    )
                },
                status=status.HTTP_200_OK,
            )

        # Extract validated data
        target = serializer.validated_data["target"]
        purpose = serializer.validated_data["purpose"]
        channel = serializer.context["channel"]

        # Send OTP via service layer
        otp_sent = OTPService.send_otp(target=target, purpose=purpose, channel=channel)
        if not otp_sent:
            return Response(
                {"detail": _("Please wait before requesting a new OTP.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Store OTP request in session (used later in otp_verify)
        request.session["otp_target"] = target
        request.session["otp_purpose"] = purpose

        return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    @throttle_classes([OTPThrottle])
    def otp_verify(self, request):
        """
        Verify OTP for registration or login.

        Steps:
            1. Validate OTP code.
            2. Fetch target + purpose from session.
            3. Register → Create new user if none exists.
            4. Login → Fetch existing user.
            5. On success → Return JWT tokens.

        Request body:
            - code (str): OTP code.

        Returns:
            - 200 OK with tokens and user ID.
            - 404 Not Found if user does not exist (login case).
            - 400 Bad Request if OTP invalid.
        """

        # Validate OTP input
        serializer = OTPVerifySerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        # Retrieve stored session values
        target = request.session.get("otp_target")
        purpose = request.session.get("otp_purpose")

        # Registration flow → create user if not exists
        if purpose == OTPPurpose.REGISTER:
            user, _ = User.objects.get_or_create_by_identifier(target)

        # Login flow → find existing user
        else:
            user = User.objects.find_by_identifier(target)

        if not user:
            # Edge case: login attempted but user does not exist
            return Response(
                {"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        # Clear session (OTP)
        del request.session["otp_target"]
        del request.session["otp_purpose"]

        # Generate JWT tokens
        tokens = get_tokens_for_user(user)

        return Response(
            {
                "detail": "OTP verified successfully.",
                "tokens": tokens,
                "user_id": user.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def login(self, request):
        """
        Traditional login using email/phone and password.

        Request body:
            - login (str): Email or phone number.
            - password (str): User password.

        Returns:
            - 200 OK with tokens and user ID.
            - 400 Bad Request if credentials are invalid.
        """

        # Validate login credentials
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response(
            {"detail": "Login successful.", "tokens": tokens, "user_id": user.id},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def password_reset_request(self, request):
        """
        Request a password reset OTP.

        Request body:
            - target (str): Email or phone number.

        Returns:
            - 200 OK if OTP sent successfully.
            - 429 Too Many Requests if cooldown active.
        """

        serializer = PasswordResetRequestSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data["target"]
        channel = serializer.context["channel"]

        # Send OTP for password reset
        otp_sent = OTPService.send_otp(
            target=target, purpose="reset_password", channel=channel
        )

        if not otp_sent:
            return Response(
                {"detail": _("Please wait before requesting a new OTP.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Store identifier for reset flow
        request.session["reset_target"] = target

        return Response(
            {"detail": _("Password reset OTP sent.")}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def password_reset_verify(self, request):
        """
        Verify OTP for password reset.

        Request body:
            - code (str): OTP code.

        Returns:
            Response: 200 OK if OTP is valid,
                      400 Bad Request if OTP invalid or expired.
        """

        serializer = PasswordResetVerifySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # Lookup user ID from session
        user_id = request.session.get("reset_user_id")

        # Sign a temporary reset token (valid for 5 min by default)
        signer = TimestampSigner(salt="password-reset-salt")
        reset_token = signer.sign(str(user_id))

        # Clean up session
        request.session.pop("reset_target", None)
        request.session.pop("reset_user_id", None)

        return Response(
            {
                "detail": _("Code verified. You can now set a new password."),
                "reset_token": reset_token,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def password_reset_set(self, request):
        """
        Set a new password after OTP verification.

        Request body:
            - password (str): New password.
            - password_confirm (str): Confirmation.
            - reset_token (str): Token from verify step.

        Returns:
            - 200 OK if password updated successfully.
            - 400 Bad Request if token invalid/expired.
            - 404 Not Found if user not found.
        """

        serializer = PasswordResetSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reset_token = serializer.validated_data["reset_token"]
        password = serializer.validated_data["password"]

        signer = TimestampSigner(salt="password-reset-salt")

        try:
            # Unsign token → extract user ID
            user_id = signer.unsign(reset_token, max_age=300)
        except SignatureExpired:
            return Response(
                {"detail": _("Password reset link has expired.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except BadSignature:
            return Response(
                {"detail": _("Invalid password reset link.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch user by ID
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        # Update password securely
        user.set_password(password)
        user.save()

        return Response(
            {"detail": _("Password has been reset successfully.")},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def profile_complete(self, request):
        """
        Update or complete the authenticated user's profile.

        Allows partial updates (PATCH) for fields such as:
        - first_name, last_name, nickname
        - gender, date_of_birth
        - email / phone number

        Request body example:
            {
                "first_name": "Ali",
                "last_name": "Rezaei",
                "nickname": "AliR",
                "gender": "Male"
            }

        Returns:
            - 200 OK with updated profile data.
        """

        serializer = ProfileCompletionSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return updated user profile
        response_data = UserSerializer(instance=serializer.instance).data
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Blacklist refresh token (logout).

        Request body:
            - refresh (str): Refresh token.

        Returns:
            - 200 OK if successfully blacklisted.
            - 400 Bad Request if token invalid.
        """

        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": _("Refresh token is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Invalidate the refresh token (so it cannot be reused)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": _("Successfully logged out.")}, status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"detail": _("Invalid or expired refresh token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_identifier_request(self, request):
        """
        Request OTP for changing email/phone identifier.

        Steps:
            1. Validate target (new email/phone).
            2. Send OTP to new identifier.
            3. Save request in session.

        Returns:
            - 200 OK if OTP sent successfully.
        """

        serializer = IdentifierChangeRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data["target"]
        channel = serializer.context["channel"]

        # Send OTP for identifier changec
        otp_sent = OTPService.send_otp(
            target=target, purpose="change_identifier", channel=channel
        )
        if not otp_sent:
            return Response(
                {"detail": _("Please wait before requesting a new OTP.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Store target in session
        request.session["change_identifier_target"] = target
        return Response(
            {"detail": f"An OTP has been sent to {target}."}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_identifier_verify(self, request):
        """
        Verify OTP for changing email/phone identifier.

        Steps:
            1. Fetch pending identifier target from session.
            2. Validate OTP.
            3. Update user’s email/phone.
            4. Clear session.

        Returns:
            - 200 OK with updated user profile.
            - 400 Bad Request if OTP/session invalid.
        """

        serializer = IdentifierChangeVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        target = request.session.get("change_identifier_target")

        if not target:
            return Response(
                {"detail": _("No active change request found. Please start over.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify OTP
        otp_data = OTPService.verify_otp(
            target=target, code=code, purpose="change_identifier"
        )
        if not otp_data:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update email or phone field
        user = request.user
        is_email = "@" in target

        if is_email:
            user.email = target
            user.is_email_verified = True
        else:
            user.phone_number = target
            user.is_phone_verified = True

        user.save()

        # Clear session
        del request.session["change_identifier_target"]

        # Return updated profile
        response_data = UserSerializer(instance=user).data
        return Response(response_data, status=status.HTTP_200_OK)


class UserViewSet(ModelViewSet):
    """
    Admin-only viewset for managing users.

    Supported methods:
        - GET /users/        → List all users.
        - GET /users/{id}/   → Retrieve a specific user.

    Permissions:
        - Restricted to staff/admin users (IsAdminUser).
    """

    # Restrict methods → only allow read operations
    http_method_names = ["get", "head", "options"]

    # Use User serializer for output
    serializer_class = UserSerializer

    # Fetch all users
    queryset = User.objects.all()

    # Only staff/admin can access
    permission_classes = [IsAdminUser]
