"""
Admin configurations for the core application.

This module registers the CustomUser model with the Django admin site and
customizes its appearance and functionality for better management.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin configuration for the CustomUser model.
    """

    list_display = (
        "id",
        "email",
        "phone_number",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "date_joined",
    )

    list_display_links = ("id", "email", "phone_number")

    search_fields = ("email", "phone_number", "first_name", "last_name")

    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    fieldsets = (
        (None, {"fields": ("email", "phone_number", "password")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "date_of_birth",
                    "gender",
                    "nickname",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Verification", {"fields": ("is_email_verified", "is_phone_verified")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = ("last_login", "date_joined")

    ordering = ("-date_joined",)

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not obj:
            return fieldsets

        return fieldsets + (("Internal", {"fields": ("username",)}),)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            return readonly_fields + ("username",)
        return readonly_fields
