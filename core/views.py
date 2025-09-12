"""
Authentication and user management viewsets.

This module provides REST API endpoints for handling authentication and
account management using Django REST Framework (DRF) and JWT (SimpleJWT).
It supports OTP-based registration/login, traditional email/phone + password
login, password reset workflows, and profile completion.

Components:
    - get_tokens_for_user(user): Utility to issue JWT tokens for a given user.
    - AuthViewSet: ViewSet for handling authentication-related endpoints
      (OTP, login, password reset, profile completion).
    - UserViewSet: Admin-only viewset for retrieving user data.

Workflow:
    1. OTP Request: User requests OTP for registration or login.
    2. OTP Verify: User enters OTP, and tokens are issued upon success.
    3. Login: Traditional login with email/phone + password.
    4. Password Reset: Request → Verify OTP → Set new password.
    5. Profile Completion: Fill in or update missing user information.
"""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
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
    """

    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class AuthViewSet(ViewSet):
    """
    A ViewSet that handles authentication and account management.

    Endpoints:
        - otp_request: Request a one-time password (OTP) via email or SMS.
        - otp_verify: Verify the OTP for registration or login.
        - login: Authenticate using email/phone and password.
        - password_reset_request: Request a password reset OTP.
        - password_reset_verify: Verify OTP for password reset.
        - password_reset_set: Set a new password after OTP verification.
        - profile_complete: Update or complete the user profile.

    Session Keys Used:
        - "otp_target": Identifier for OTP (email or phone).
        - "otp_purpose": Purpose of the OTP ("register" or "login").
        - "reset_target": Identifier for password reset.
        - "reset_user_id": User ID associated with a password reset.
    """

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def otp_request(self, request):
        """
        Handle OTP request for registration or login.

        Validates the target identifier (email or phone), ensures it is
        allowed for the given purpose, and triggers OTP sending. A cooldown
        mechanism prevents repeated requests within the timeout period.

        Request body:
            - target (str): Email or phone number.
            - purpose (str): "register" or "login".

        Returns:
            Response: 200 OK if OTP sent successfully,
                      429 Too Many Requests if cooldown active.
        """

        serializer = OTPRequestSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data["target"]
        purpose = serializer.validated_data["purpose"]
        channel = serializer.context["channel"]

        otp_sent = OTPService.send_otp(target=target, purpose=purpose, channel=channel)
        if not otp_sent:
            return Response(
                {"detail": _("Please wait before requesting a new OTP.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        request.session["otp_target"] = target
        request.session["otp_purpose"] = purpose

        return Response({"detail": "OTP sent successfully."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def otp_verify(self, request):
        """
        Verify OTP for registration or login.

        For registration, a new user is created if one does not exist.
        For login, the existing user is retrieved. Upon successful verification,
        JWT tokens are returned.

        Request body:
            - code (str): OTP code.

        Returns:
            Response: 200 OK with tokens and user ID,
                      404 Not Found if user does not exist,
                      400 Bad Request if OTP invalid.
        """

        serializer = OTPVerifySerializer(
            data=request.data, context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        target = request.session.get("otp_target")
        purpose = request.session.get("otp_purpose")

        if purpose == "register":
            identifier = "email" if "@" in target else "phone_number"
            user, created = User.objects.get_or_create(
                **{identifier: target},
                defaults={
                    "is_email_verified": identifier == "email",
                    "is_phone_verified": identifier == "phone_number",
                }
            )
        else:
            user = (
                User.objects.filter(email=target).first()
                or User.objects.filter(phone_number=target).first()
            )

        if not user:
            return Response(
                {"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        del request.session["otp_target"]
        del request.session["otp_purpose"]

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
            Response: 200 OK with tokens and user ID,
                      400 Bad Request if credentials are invalid.
        """

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
        Request a password reset OTP via email or SMS.

        Request body:
            - target (str): Email or phone number.

        Returns:
            Response: 200 OK if OTP sent,
                      429 Too Many Requests if cooldown active.
        """

        serializer = PasswordResetRequestSerializer(data=request.data, context={})
        serializer.is_valid(raise_exception=True)

        target = serializer.validated_data["target"]
        channel = serializer.context["channel"]

        otp_sent = OTPService.send_otp(
            target=target, purpose="reset_password", channel=channel
        )

        if not otp_sent:
            return Response(
                {"detail": _("Please wait before requesting a new OTP.")},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        return Response(
            {"detail": _("Code verified. You can now set a new password.")},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def password_reset_set(self, request):
        """
        Set a new password after OTP verification.

        Request body:
            - password (str): New password.
            - password_confirm (str): Password confirmation.

        Returns:
            Response: 200 OK if password reset successfully,
                      403 Forbidden if verification not completed,
                      404 Not Found if user not found.
        """

        user_id = request.session.get("reset_user_id")
        if not user_id:
            return Response(
                {"detail": _("Verification is required first.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PasswordResetSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": _("User not found.")}, status=status.HTTP_404_NOT_FOUND
            )

        password = serializer.validated_data["password"]
        user.set_password(password)
        user.save()

        del request.session["reset_target"]
        del request.session["reset_user_id"]

        return Response(
            {"detail": _("Password has been reset successfully.")},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def profile_complete(self, request):
        """
        Update or complete the authenticated user's profile.

        Allows partial updates for fields such as name, nickname,
        gender, date of birth, and identifiers (email/phone).

        Request body (example):
            {
                "first_name": "Ali",
                "last_name": "Rezaei",
                "nickname": "AliR",
                "gender": "Male"
            }

        Returns:
            Response: 200 OK on success with updated profile data.
        """

        serializer = ProfileCompletionSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        response_data = UserSerializer(instance=serializer.instance).data
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

    http_method_names = ["get", "head", "options"]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
