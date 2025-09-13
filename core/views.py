"""
Authentication and User Management ViewSets.

This module provides comprehensive REST API endpoints for user authentication,
account management, and profile operations using Django REST Framework (DRF)
and SimpleJWT.

The authentication system is highly flexible, supporting:
- OTP-based registration and login (via email or SMS).
- Traditional login with an identifier (email/phone) and password.
- A secure, multi-step password reset workflow.
- A secure, multi-step process for changing primary identifiers (email/phone).
- Profile completion and updates for authenticated users.

Key Components:
    - AuthViewSet: A single ViewSet that consolidates all authentication and
      account-related actions for a clean and organized URL structure.
    - UserViewSet: An admin-only ViewSet for viewing and managing user data.
    - get_tokens_for_user: A utility function to generate JWT access and refresh tokens.
    - OTPThrottle: A custom throttle to prevent abuse of OTP-related endpoints.

Core Workflows:
    1.  **Registration/Login via OTP**:
        - POST /auth/otp-request/ -> User provides email/phone and purpose ('register'/'login').
        - POST /auth/otp-verify/ -> User submits the received OTP to get JWT tokens.
    2.  **Standard Login**:
        - POST /auth/login/ -> User provides email/phone and password to get JWT tokens.
    3.  **Password Reset**:
        - POST /auth/password-reset/request/ -> User requests a reset OTP.
        - POST /auth/password-reset/verify/ -> User verifies the OTP to get a secure reset token.
        - POST /auth/password-reset/set/ -> User sets a new password using the reset token.
    4.  **Profile Management**:
        - PATCH /auth/profile/complete/ -> Authenticated user completes or updates their profile.
    5.  **Identifier Change**:
        - POST /auth/change-identifier/request/ -> User requests to change their email/phone.
        - POST /auth/change-identifier/verify/ -> User verifies the OTP sent to the new identifier.
"""

from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import action, throttle_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=["Authentication"],
        summary="1. Request One-Time Password (OTP)",
        description="""
        **Endpoint**: POST /auth/otp-request/

        Initiates the OTP-based login or registration process.
        The user provides their email or phone number (`target`) and the intended action (`purpose`).

        **Step-by-Step Workflow**:
        1. Validate and normalize input (email/phone).
        2. Check existence based on purpose:
           - **register**: Target must be unique (no existing user).
           - **login**: Target must exist (user lookup).
        3. Send 6-digit OTP via detected channel (email/SMS).
        4. Store in session for verification.

        **Request Formats**:
        - JSON: `{"target": "09123456789", "purpose": "login"}`
        - Form-Data: `target=09123456789&purpose=login`

        **Response Notes**:
        - Always generic success to prevent user enumeration.
        - OTP expires in 5 minutes; single-use.

        **Error Handling**:
        - 400: Invalid input (e.g., malformed phone).
        - 429: Rate limit (5/hour per IP).

        **Security Best Practices**:
        - Use HTTPS in production.
        - Monitor for brute-force attempts.
        """,
        request=OTPRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="OTP processed (generic response for security).",
                examples={
                    "success": OpenApiExample(
                        "OTP Sent",
                        value={
                            "detail": "If an account with these details exists, a verification code will be sent."
                        },
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Validation error (e.g., duplicate for register).",
                examples={
                    "invalid": OpenApiExample(
                        "Invalid Target",
                        value={
                            "target": ["A user with this identifier already exists."]
                        },
                    )
                },
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
                description="Rate limit exceeded.",
                examples={
                    "throttled": OpenApiExample(
                        "Rate Limit",
                        value={"detail": "Please wait before requesting a new OTP."},
                    )
                },
            ),
        },
    )
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

    @extend_schema(
        tags=["Authentication"],
        summary="2. Verify OTP and Authenticate",
        description="""
        **Endpoint**: POST /auth/otp-verify/

        Verifies the OTP from the previous request and authenticates the user.

        **Step-by-Step Workflow**:
        1. Validate 6-digit code.
        2. Retrieve target/purpose from session.
        3. For 'register': Create user if not exists (minimal profile).
        4. For 'login': Fetch existing user.
        5. Generate JWT tokens.
        6. Clear session.

        **Request Formats**:
        - JSON: `{"code": "123456"}`
        - Form-Data: `code=123456`

        **Output**:
        - Tokens: Use `access` for requests, `refresh` to renew.
        - User ID for reference.

        **Error Handling**:
        - 400: Invalid/expired code or no session.
        - 404: User not found (rare for login).

        **Next Steps**:
        - Use tokens in `Authorization: Bearer <access_token>`.
        - Complete profile via /auth/profile/complete/ if new user.
        """,
        request=OTPVerifySerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Authentication successful.",
                examples={
                    "success": OpenApiExample(
                        "Tokens Issued",
                        value={
                            "detail": "OTP verified successfully.",
                            "tokens": {
                                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCJ9...",
                                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsInRva2VuX3R5cGUiOiJhY2Nlc3MifQ...",
                            },
                            "user_id": 123,
                        },
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid OTP.",
                examples={
                    "invalid": OpenApiExample(
                        "Bad Code",
                        value={"detail": "Invalid or expired OTP."},
                    )
                },
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="User not found.",
                examples={
                    "not_found": OpenApiExample(
                        "No User",
                        value={"detail": "User not found."},
                    )
                },
            ),
        },
    )
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

    @extend_schema(
        tags=["Authentication"],
        summary="Login with Password",
        description="""
        **Endpoint**: POST /auth/login/

        Handles traditional authentication using identifier + password.

        **Step-by-Step Workflow**:
        1. Normalize login (email/phone).
        2. Lookup user.
        3. Validate password.
        4. Check verification status.
        5. Issue tokens.

        **Request Formats**:
        - JSON: `{"login": "user@example.com", "password": "pass123"}`
        - Form-Data: `login=user@example.com&password=pass123`

        **Output**: Same as OTP verify (tokens + user ID).

        **Error Handling**:
        - 400: Wrong credentials or unverified account.

        **Security Best Practices**:
        - Enforce strong passwords (min 8 chars, validators active).
        - Log failed attempts for monitoring.
        """,
        request=LoginSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Login successful.",
                examples={
                    "success": OpenApiExample(
                        "Logged In",
                        value={
                            "detail": "Login successful.",
                            "tokens": {
                                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            },
                            "user_id": 123,
                        },
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid credentials.",
                examples={
                    "invalid": OpenApiExample(
                        "Bad Creds",
                        value={"detail": "The login information was incorrect."},
                    )
                },
            ),
        },
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

    @extend_schema(
        tags=["Authentication"],
        summary="Logout (Blacklist Token)",
        description="""
        **Endpoint**: POST /auth/logout/

        Invalidates the refresh token to log out the user.

        **Step-by-Step Workflow**:
        1. Extract refresh token from request.
        2. Blacklist it (SimpleJWT blacklist app).
        3. Access token remains valid until expiry.

        **Request Format**: JSON: `{"refresh": "your.refresh.token"}`

        **Notes**:
        - Requires authentication (use access token).
        - Blacklisted tokens can't refresh access.

        **Error Handling**:
        - 400: Missing/invalid token.
        """,
        request={
            "application/json": {
                "example": {"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}
            }
        },
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Logged out successfully.",
                examples={
                    "success": OpenApiExample(
                        "Blacklisted",
                        value={"detail": "Successfully logged out."},
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid token.",
                examples={
                    "invalid": OpenApiExample(
                        "Bad Token",
                        value={"detail": "Invalid or expired refresh token."},
                    )
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="No auth provided.",
                examples={
                    "unauth": OpenApiExample(
                        "No Auth",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                },
            ),
        },
    )
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

    @extend_schema(
        tags=["Password Management"],
        summary="1. Request Password Reset OTP",
        description="""
        **Endpoint**: POST /auth/password-reset/request/

        Starts the password reset by sending OTP to email/phone.

        **Step-by-Step Workflow**:
        1. Validate/normalize target.
        2. Confirm user exists (generic response).
        3. Send OTP for "reset_password".
        4. Store target in session.

        **Request Formats**:
        - JSON: `{"target": "user@example.com"}`
        - Form-Data: `target=user@example.com`

        **Notes**:
        - Similar to OTP request but purpose="reset_password".

        **Error Handling**:
        - 400: No user (but generic).
        - 429: Rate limit.
        """,
        request=PasswordResetRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="OTP sent.",
                examples={
                    "sent": OpenApiExample(
                        "Reset Started",
                        value={"detail": "Password reset OTP sent."},
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid target.",
                examples={
                    "no_user": OpenApiExample(
                        "No Account",
                        value={"detail": "No user found with this identifier."},
                    )
                },
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
                description="Rate limit.",
                examples={
                    "throttled": OpenApiExample(
                        "Wait",
                        value={"detail": "Please wait before requesting a new OTP."},
                    )
                },
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    @throttle_classes([OTPThrottle])
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

    @extend_schema(
        tags=["Password Management"],
        summary="2. Verify Password Reset OTP",
        description="""
        **Endpoint**: POST /auth/password-reset/verify/

        Confirms OTP and issues a short-lived reset_token.

        **Step-by-Step Workflow**:
        1. Validate code.
        2. Verify against session target.
        3. Sign user ID with TimestampSigner (5min expiry).
        4. Store user ID in session.
        5. Clear target from session.

        **Request Format**: JSON: `{"code": "123456"}`

        **Output**: `reset_token` – use in next step.

        **Error Handling**:
        - 400: Invalid code or no session.

        **Security Notes**:
        - Token prevents replay; expires fast.
        """,
        request=PasswordResetVerifySerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Verified; token issued.",
                examples={
                    "verified": OpenApiExample(
                        "Token Ready",
                        value={
                            "detail": "Code verified. You can now set a new password.",
                            "reset_token": "ts~eyJ1c2VyX2lkIjo...~timestamp",
                        },
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Bad OTP.",
                examples={
                    "invalid": OpenApiExample(
                        "Expired",
                        value={"detail": "Invalid or expired OTP."},
                    )
                },
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    @throttle_classes([OTPThrottle])
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

    @extend_schema(
        tags=["Password Management"],
        summary="3. Set New Password",
        description="""
        **Endpoint**: POST /auth/password-reset/set/

        Finalizes reset by updating password.

        **Step-by-Step Workflow**:
        1. Validate passwords match.
        2. Unsign token (check expiry/signature).
        3. Fetch user by ID.
        4. Set hashed password.
        5. Save user.

        **Request Format**: JSON: `{"password": "newpass", "password_confirm": "newpass", "reset_token": "..."}`

        **Notes**:
        - No auth needed; token secures it.

        **Error Handling**:
        - 400: Mismatch or expired token.
        - 404: User not found.
        """,
        request=PasswordResetSetPasswordSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="Password updated.",
                examples={
                    "updated": OpenApiExample(
                        "Reset Complete",
                        value={"detail": "Password has been reset successfully."},
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Token or password error.",
                examples={
                    "expired": OpenApiExample(
                        "Expired Token",
                        value={"detail": "Password reset link has expired."},
                    ),
                    "mismatch": OpenApiExample(
                        "No Match",
                        value={"password_confirm": "Passwords do not match."},
                    ),
                },
            ),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="User invalid.",
                examples={
                    "not_found": OpenApiExample(
                        "No User",
                        value={"detail": "User not found."},
                    )
                },
            ),
        },
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

    @extend_schema(
        tags=["Profile"],
        summary="Complete or Update User Profile",
        description="""
        **Endpoint**: PATCH /auth/profile/complete/

        Updates profile for authenticated user (partial allowed).

        **Step-by-Step Workflow**:
        1. Dynamic validation: Require missing identifier (email/phone).
        2. Check uniqueness for new identifiers.
        3. Hash password if provided.
        4. Mark verified if added.
        5. Save and return updated profile.

        **Request Formats**:
        - JSON: Partial object, e.g., `{"first_name": "John", "phone_number": "0912..."}`
        - Form-Data: For future extensions (e.g., profile_pic upload).

        **Notes**:
        - PATCH: Only send changed fields.
        - New users must set password here.

        **Error Handling**:
        - 400: Duplicate or missing required.
        - 401: Unauthenticated.

        **Output**: Full updated profile.
        """,
        request=ProfileCompletionSerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Validation errors.",
                examples={
                    "duplicate": OpenApiExample(
                        "Email Taken",
                        value={"email": ["This email is already in use."]},
                    ),
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="No auth.",
                examples={
                    "unauth": OpenApiExample(
                        "Auth Required",
                        value={
                            "detail": "Authentication credentials were not provided."
                        },
                    )
                },
            ),
        },
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

    @extend_schema(
        tags=["Identifier Change"],
        summary="1. Request Identifier Change OTP",
        description="""
        **Endpoint**: POST /auth/change-identifier/request/

        Authenticated user requests to update email/phone.

        **Step-by-Step Workflow**:
        1. Validate new target (unique, format).
        2. Send OTP to NEW target (purpose="change_identifier").
        3. Store in session.

        **Request Formats**:
        - JSON: `{"target": "new@example.com"}`
        - Form-Data: `target=new@example.com`

        **Notes**:
        - OTP sent to new, not old, for verification.

        **Error Handling**:
        - 400: Duplicate target.
        - 401: Unauthenticated.
        - 429: Rate limit.
        """,
        request=IdentifierChangeRequestSerializer,
        responses={
            status.HTTP_200_OK: OpenApiResponse(
                description="OTP sent to new identifier.",
                examples={
                    "sent": OpenApiExample(
                        "Change Started",
                        value={
                            "detail": "An OTP has been sent to new.email@example.com."
                        },
                    )
                },
            ),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Invalid target.",
                examples={
                    "duplicate": OpenApiExample(
                        "Taken",
                        value={
                            "detail": "This email is already in use by another account."
                        },
                    )
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="Auth required.",
            ),
            status.HTTP_429_TOO_MANY_REQUESTS: OpenApiResponse(
                description="Rate limit.",
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    @throttle_classes([OTPThrottle])
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

    @extend_schema(
        tags=["Identifier Change"],
        summary="2. Verify Identifier Change OTP",
        description="""
        **Endpoint**: POST /auth/change-identifier/verify/

        Completes the change by verifying OTP.

        **Step-by-Step Workflow**:
        1. Validate code.
        2. Verify against session target.
        3. Update user's email/phone.
        4. Mark as verified.
        5. Clear session.

        **Request Format**: JSON: `{"code": "123456"}`

        **Output**: Updated profile.

        **Error Handling**:
        - 400: Invalid OTP or no session.
        - 401: Unauthenticated.

        **Notes**:
        - Re-login may be needed if changing login identifier.
        """,
        request=IdentifierChangeVerifySerializer,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(
                description="Bad OTP.",
                examples={
                    "invalid": OpenApiExample(
                        "Expired",
                        value={"detail": "Invalid or expired OTP."},
                    ),
                    "no_session": OpenApiExample(
                        "No Request",
                        value={
                            "detail": "No active change request found. Please start over."
                        },
                    ),
                },
            ),
            status.HTTP_401_UNAUTHORIZED: OpenApiResponse(
                description="Auth required.",
            ),
        },
    )
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    @throttle_classes([OTPThrottle])
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

    @extend_schema(
        tags=["Admin"],
        summary="List All Users",
        description="""
        **Endpoint**: GET /users/

        Returns paginated list of all users (admin only).

        **Query Params** (optional):
        - search: Filter by name/email/phone.
        - page: Pagination.

        **Output**: Array of user profiles.

        **Security**: IsAdminUser permission.
        """,
        responses={
            status.HTTP_200_OK: UserSerializer(many=True),
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["Admin"],
        summary="Retrieve a Specific User",
        description="""
        **Endpoint**: GET /users/{id}/

        Returns detailed profile for a user (admin only).

        **Path Param**: id (int) - User ID.

        **Output**: Single user profile.

        **Security**: IsAdminUser; no sensitive data exposed.
        """,
        responses={
            status.HTTP_200_OK: UserSerializer,
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="User not found.",
                examples={
                    "not_found": OpenApiExample(
                        "Missing",
                        value={"detail": "Not found."},
                    )
                },
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
