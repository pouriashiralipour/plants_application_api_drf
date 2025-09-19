"""
Custom permissions for the e-commerce API.

This module defines reusable Django REST Framework (DRF) permission classes
to restrict access to certain resources based on user role, authentication
status, and HTTP method.

Classes
-------
IsAdminOrReadOnly
    Grants read-only access to all users but restricts write operations
    to admin (staff) users.

ReviewPermission
    Grants read-only access to everyone, allows authenticated users to
    create reviews, and restricts update/delete operations to staff users.

Usage
-----
Add these permissions to DRF views or viewsets using the `permission_classes`
attribute. For example::

    from rest_framework.viewsets import ModelViewSet
    from .permissions import IsAdminOrReadOnly, ReviewPermission
    from .models import Product, Review
    from .serializers import ProductSerializer, ReviewSerializer

    class ProductViewSet(ModelViewSet):
        queryset = Product.objects.all()
        serializer_class = ProductSerializer
        permission_classes = [IsAdminOrReadOnly]

    class ReviewViewSet(ModelViewSet):
        queryset = Review.objects.all()
        serializer_class = ReviewSerializer
        permission_classes = [ReviewPermission]
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Permission class that allows read-only access for everyone
    but write access only for staff users.

    Rules
    -----
    - SAFE methods (GET, HEAD, OPTIONS) are always allowed.
    - Non-SAFE methods (POST, PUT, PATCH, DELETE) require the user
      to be authenticated as staff (`is_staff=True`).

    Example
    -------
    >>> permission = IsAdminOrReadOnly()
    >>> request.method = "GET"   # allowed for all
    >>> permission.has_permission(request, view)
    True

    >>> request.method = "POST"
    >>> request.user.is_staff = False  # denied
    >>> permission.has_permission(request, view)
    False
    """

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or (request.user and request.user.is_staff)
        )


class ReviewPermission(BasePermission):
    """
    Permission class for managing access to reviews.

    Rules
    -----
    - SAFE methods (GET, HEAD, OPTIONS) are allowed for everyone.
    - Authenticated users can create reviews (POST).
    - Only staff users can update or delete existing reviews.

    Methods
    -------
    has_permission(request, view)
        Checks access for the entire view (e.g., listing, creating).
    has_object_permission(request, view, obj)
        Checks access for individual review objects (e.g., editing, deleting).

    Example
    -------
    >>> permission = ReviewPermission()
    >>> request.method = "POST"
    >>> request.user.is_authenticated = True  # allowed to create review
    >>> permission.has_permission(request, view)
    True

    >>> request.method = "DELETE"
    >>> request.user.is_staff = False  # denied
    >>> permission.has_object_permission(request, view, obj)
    False
    """

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS
            or (request.user and request.user.is_authenticated)
        )

    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in SAFE_METHODS or (request.user and request.user.is_staff)
        )
