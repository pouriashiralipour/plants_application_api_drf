from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .utils import phone_validator


class CustomUser(AbstractUser):
    GENDER_CHOICE = [("Male", _("Male")), ("Female", _("Female"))]
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
    nickname = models.CharField(
        max_length=80, blank=True, null=True, verbose_name=_("nickname")
    )
    gender = models.CharField(
        max_length=6,
        choices=GENDER_CHOICE,
        blank=True,
        null=True,
        verbose_name=_("gender"),
    )
    profile_pic = models.ImageField(
        upload_to="profile_pics/",
        blank=True,
        null=True,
        verbose_name=_("profile picture"),
    )
    date_of_birth = models.DateField(
        verbose_name=_("date_of_birth"), blank=True, null=True
    )
