"""
Admin configurations for the core application.

This module registers the `CustomUser` model with the Django admin site and
customizes its appearance and functionality for better management.

The configuration extends Django's built-in `UserAdmin` to:
    - Display important user information in the list view.
    - Provide search, filter, and ordering capabilities.
    - Organize fields into logical groups for easier navigation.
    - Handle additional fields defined in the `CustomUser` model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin configuration for the `CustomUser` model.

    Extends the default `UserAdmin` to support custom fields such as
    `phone_number`, `nickname`, `date_of_birth`, and verification flags.

    Key customizations:
        - `list_display`: Defines which fields are shown in the user list view.
        - `list_filter`: Provides filters in the sidebar for quick segmentation.
        - `search_fields`: Enables searching by email, phone number, and name.
        - `fieldsets`: Organizes fields into meaningful sections.
        - `readonly_fields`: Marks certain fields as non-editable.
        - `ordering`: Sets the default ordering of user records.
        - `get_fieldsets`: Dynamically alters fieldsets based on whether
          the user is being created or updated.
        - `get_readonly_fields`: Adds conditional readonly fields for updates.
    """

    # Fields displayed in the admin list view for quick reference

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    list_display = (
        "id",
        "email",
        "phone_number",
        "full_name",
        "is_staff",
        "is_active",
        "date_joined",
    )

    # Fields that act as hyperlinks to the user detail page
    list_display_links = ("id", "email", "phone_number")

    # Fields that can be searched in the admin panel
    search_fields = ("email", "phone_number", "first_name", "last_name")

    # Filters shown in the right sidebar for segmenting users
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    # Field grouping and layout in the admin form
    fieldsets = (
        # Basic login-related fields
        (None, {"fields": ("id", "email", "phone_number", "password")}),
        # Personal user information
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
        # Permissions and access-related fields
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
        # Verification status for email and phone
        ("Verification", {"fields": ("is_email_verified", "is_phone_verified")}),
        # Login and registration timestamps
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone_number", "password1", "password2"),
            },
        ),
    )
    # Fields that cannot be edited in the admin interface
    readonly_fields = ("last_login", "date_joined")

    # Default ordering for the user list view (newest users first)
    ordering = ("-date_joined",)

    def get_fieldsets(self, request, obj=None):
        """
        Customize the fieldsets shown in the admin form.

        - On user creation: Show the default fieldsets.
        - On user update: Add an "Internal" section with the `username` field.
          This is useful if `username` exists as a legacy/internal identifier.

        Args:
            request (HttpRequest): The current admin request.
            obj (CustomUser or None): The user object being edited, or None if creating.

        Returns:
            tuple: The modified fieldsets.
        """

        fieldsets = super().get_fieldsets(request, obj)
        if not obj:
            return fieldsets

        # Append "Internal" section only when editing an existing user
        return fieldsets + (("Internal", {"fields": ("username",)}),)

    def get_readonly_fields(self, request, obj=None):
        """
        Define which fields are readonly in the admin form.

        - Always: `last_login`, `date_joined`
        - On user update: Add `username` as readonly to prevent modification.

        Args:
            request (HttpRequest): The current admin request.
            obj (CustomUser or None): The user object being edited, or None if creating.

        Returns:
            tuple: The list of readonly fields.
        """

        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            return readonly_fields + ("username",)
        return readonly_fields
