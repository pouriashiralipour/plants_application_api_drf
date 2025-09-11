from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
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


class ProfileCompletionSerializer(serializers.ModelSerializer):
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
        super().__init__(*args, **kwargs)
        if "request" in self.context:
            user = self.context["request"].user

            if user.email:
                self.fields["email"].read_only = True
                self.fields["phone_number"].required = True

            elif user.phone_number:
                self.fields["phone_number"].read_only = True
                self.fields["email"].required = True

    def validate(self, attrs):
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
        instance.set_password(validated_data.pop("password"))

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if "email" in validated_data and not instance.is_email_verified:
            instance.is_email_verified = True
        if "phone_number" in validated_data and not instance.is_phone_verified:
            instance.is_phone_verified = True

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        login = attrs["login"].strip().lower()
        password = attrs["password"]

        if "@" in login:
            user = User.objects.filter(email=login).first()
        else:
            phone_normalize = normalize_iran_phone(login)
            user = User.objects.filter(phone_number=phone_normalize).first()

        if not user or not user.check_password(password):
            raise ValidationError(_("Invalid credentials."))

        if not (user.is_email_verified or user.is_phone_verified):
            raise ValidationError(_("Account not verified."))

        attrs["user"] = user
        return attrs
