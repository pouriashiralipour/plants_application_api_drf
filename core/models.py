from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .utils import phone_validator


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=254, unique=True, blank=True, null=True, verbose_name=_("email")
    )
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[phone_validator],
        verbose_name=_("phone_number"),
    )
