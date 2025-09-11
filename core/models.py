from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    email = models.EmailField(
        max_length=254, unique=True, blank=True, null=True, verbose_name=_("email")
    )
