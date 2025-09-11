from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import OTPRequestSerializer
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
