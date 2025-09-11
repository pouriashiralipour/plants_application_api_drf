from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import OTPRequestSerializer, OTPVerifySerializer
from .services import OTPService

User = get_user_model()


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
