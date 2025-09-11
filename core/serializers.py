from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .services import OTPService
from .utils import normalize_iran_phone

User = get_user_model()


class OTPRequestSerializer(serializers.Serializer):
    target = serializers.CharField(write_only=True)
    purpose = serializers.ChoiceField(write_only=True, choices=["register", "login"])

    def validate_target(self, value):
        value = value.strip().lower()

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

        purpose = self.initial_data.get("purpose")

        if purpose == "register" and user_exists:
            raise serializers.ValidationError(
                _("User with this identifier already exists.")
            )
        if purpose == "login" and not user_exists:
            raise serializers.ValidationError(_("User with this identifier not found."))

        return value


class OTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, write_only=True)

    def validate(self, attrs):
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
