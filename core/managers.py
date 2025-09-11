import uuid

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

from .utils import normalize_iran_phone


class CustomManager(BaseUserManager):
    def create_user(self, password=None, **extra_fields):
        if not extra_fields.get("email") and not extra_fields.get("phone_number"):
            raise ValueError(_("Either Email or Phone number must be set"))

        if email := extra_fields.get("email"):
            extra_fields["email"] = self.normalize_email(email)
        if phone_number := extra_fields.get("phone_number"):
            extra_fields["phone_number"] = self.normalize_iran_phone(phone_number)

        if "username" not in extra_fields:
            extra_fields["username"] = str(uuid.uuid4)

        user = self.model(**extra_fields)

        if password:
            user.set_password(password)

        user.save(using=self._db)

        return user
