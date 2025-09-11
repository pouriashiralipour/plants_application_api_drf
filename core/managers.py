from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomManager(BaseUserManager):
    def create_user(self, password=None, **extra_fields):
        if not extra_fields.get("email") and not extra_fields.get("phone_number"):
            raise ValueError(_("Either Email or Phone number must be set"))

        if email := extra_fields.get("email"):
            extra_fields["email"] = self.normalize_email(email)
        # if phone_number := extra_fields.get("phone_number"):
        #     extra_fields["phone_number"] = self.normalize_email(email)
