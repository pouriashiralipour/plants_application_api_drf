"""
URL routing configuration for authentication and user management APIs.

This module registers API endpoints for authentication and user profile
management using Django REST Framework's `DefaultRouter`.

Registered routes:
    - /auth/   → Handled by AuthViewSet (OTP, login, password reset, etc.)
    - /users/  → Handled by UserViewSet (profile viewing, updating, etc.)

Each ViewSet is automatically mapped to REST-style routes such as:
    - list (GET)
    - retrieve (GET <id>)
    - create (POST)
    - update (PUT/PATCH)
    - destroy (DELETE)

Example:
    >>> # Auth endpoints
    >>> /auth/request-otp/   # Request OTP for login/registration
    >>> /auth/verify-otp/    # Verify OTP
    >>> /auth/login/         # Login with password
    >>> /auth/reset-password/ # Password reset flow
    >>>
    >>> # User endpoints
    >>> /users/              # List or create users
"""

from rest_framework.routers import DefaultRouter

from .views import AuthViewSet, UserViewSet

# Initialize DRF's DefaultRouter.
# The router automatically generates URL patterns for registered ViewSets.
router = DefaultRouter()

# Register the authentication routes under the prefix "auth".
# Example: /auth/login/, /auth/request-otp/, etc.
# `basename="auth"` ensures that reverse lookups work properly
# even if the ViewSet does not define a queryset.
router.register("auth", AuthViewSet, basename="auth")

# Register the user management routes under the prefix "users".
# Example: /users/
# `basename="users"` allows referencing these routes in reverse() calls.
router.register("users", UserViewSet, basename="users")

# The final URL patterns include all the automatically generated routes
# for both AuthViewSet and UserViewSet.
urlpatterns = router.urls
