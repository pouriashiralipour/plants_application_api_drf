from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
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
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class OTPRequestView(APIView):
    def post(self, request):
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


class OTPVerifyView(APIView):
    def post(self, request):
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


class ProfileCompletionView(generics.UpdateAPIView):
    serializer_class = ProfileCompletionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = get_tokens_for_user(user)

        return Response(
            {"detail": "Login successful.", "tokens": tokens, "user_id": user.id},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    def post(self, request):
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


class PasswordResetVerifyView(APIView):
    def post(self, request):
        serializer = PasswordResetVerifySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        return Response(
            {"detail": _("Code verified. You can now set a new password.")},
            status=status.HTTP_200_OK,
        )


class PasswordResetSetPasswordView(APIView):
    def post(self, request):
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


class UserViewSet(ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
