from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .utils import normalize_iran_phone

User = get_user_model()


class OTPRequestSerializer(serializers.Serializer):
    target = serializers.CharField(write_only=True)
    purpose = serializers.ChoiceField(write_only=True, choices=["register", "login"])

    def validate_target(self, value):
        value = value.strip().lower()

        if "@" in value:
            serializers.EmailField.run_validation(value)
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
