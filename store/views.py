"""
E-commerce API Views
====================

This module defines the API layer of the e-commerce application using Django REST Framework (DRF).
It provides a collection of `ViewSet` classes to handle CRUD operations, filtering, searching,
ordering, and permission enforcement for the main entities of the system.

Overview
--------
The API is organized into the following functional areas:

1. **Product Management**
   - Browse, search, filter, and order products.
   - Manage product images.
   - Admin users can create, update, and delete products.

2. **Category Management**
   - Retrieve category listings and details.
   - Fetch categories with nested product relations.
   - Admin users can perform category CRUD operations.

3. **Customer Reviews**
   - Users can post reviews for products.
   - Reviews support moderation and approval by admins.
   - Reviews are annotated with like counts and linked user profiles.

4. **Shopping Cart**
   - Anonymous and authenticated users can create carts.
   - Add, update, and remove cart items.
   - Retrieve cart contents by UUID.

5. **Orders**
   - Authenticated users can place orders based on their carts.
   - Admins can manage and update all orders.
   - Supports order creation, updates, and retrieval.

6. **Address Book**
   - Users can manage their own shipping addresses.
   - Admins can access all addresses in the system.
   - Provides separate serializers for users and admins.

7. **Wishlist**
   - Authenticated users can add/remove products from their wishlist.
   - Retrieve personalized wishlist with product annotations.

Documentation & Schema Integration
----------------------------------
All viewsets and methods include descriptive docstrings, request/response
examples, and error handling notes to integrate with tools such as
**Swagger/OpenAPI** for API schema generation.

Permissions & Security
----------------------
- **Admin-only access**: Product/category/order/address management.
- **Authenticated-only access**: Reviews, orders, addresses, wishlists.
- **Anonymous access**: Browsing products and categories.
- Custom permission classes:
  - `IsAdminOrReadOnly`: Public read, admin write.
  - `ReviewPermission`: Review creation/moderation logic.

Filtering, Search, and Ordering
-------------------------------
- Products: Full-text search, filtering by custom fields, ordering by creation date, price, rating.
- Reviews: Filtered by approval status, linked to product context.
- DRF backends used: `SearchFilter`, `DjangoFilterBackend`, `OrderingFilter`.

Dependencies
------------
- **Django REST Framework**: Base API functionality.
- **django-filter**: Advanced filtering.
- **Custom utilities**: Query annotations (e.g., `main_image_subquery`).
- **Custom serializers**: User/admin-specific response handling.
- **Custom permissions**: Role-based access enforcement.

Classes Provided
----------------
- `ProductImagesViewSet`: Manage product images (CRUD).
- `ProductViewSet`: Product catalog with search/filter/order.
- `CategoryViewSet`: Category listing/details with nested products.
- `ReviewViewSet`: Customer product reviews with moderation.
- `CartViewSet`: Shopping cart management (create/retrieve/delete).
- `CartItemViewSet`: Cart item CRUD operations.
- `OrderViewSet`: User/admin order management.
- `AddressViewSet`: Address book for users/admins.
- `WishlistViewSet`: User wishlist operations.

Usage
-----
These viewsets should be registered with a DRF `DefaultRouter` in the
application's `urls.py` file to expose RESTful endpoints.

Example:

    from rest_framework.routers import DefaultRouter
    from .views import ProductViewSet, CategoryViewSet

    router = DefaultRouter()
    router.register("products", ProductViewSet, basename="products")
    router.register("categories", CategoryViewSet, basename="categories")
    urlpatterns = router.urls

"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .filter import ProductFilter, ReviewFilter
from .models import (
    Address,
    Cart,
    CartItem,
    Category,
    Order,
    Product,
    ProductImage,
    Review,
    Wishlist,
)
from .permissions import IsAdminOrReadOnly, ReviewPermission
from .serializers import (
    AddCartItemSerializer,
    AddressForAdminSerializer,
    AddressForUsersSerializer,
    CartItemSerializer,
    CartSerializer,
    CategoryDetailsSerializer,
    CategoryListSerializer,
    OrderCreateSerializer,
    OrderForAdminSerializer,
    OrderForUsersSerializer,
    OrderUpdateSerializer,
    ProductDetailsSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ReviewAdminUpdateSerializer,
    ReviewListAdminSerializer,
    ReviewListUserSerializer,
    UpdateCartItemSerializer,
    WishlistSerializer,
)
from .utils import main_image_subquery

User = get_user_model()


class ProductImagesViewSet(ModelViewSet):
    """
    Manage product images (CRUD).

    Permissions:
    - Admin can add, update, and delete images.
    - Public users can only view images.

    Endpoints:
    ---------
    - GET /products/{product_pk}/images/
        List all images of a product.

        Example Response (200):
        [
            {
                "id": 1,
                "image": "https://example.com/media/products/1/img1.jpg",
                "alt_text": "Front view"
            }
        ]

    - POST /products/{product_pk}/images/ (admin only)
        Upload a new image for a product.

        Example Request:
        {
            "image": "<file>",
            "alt_text": "Side view"
        }

        Example Response (201):
        {
            "id": 2,
            "image": "https://example.com/media/products/1/img2.jpg",
            "alt_text": "Side view"
        }

    - DELETE /products/{product_pk}/images/{id}/ (admin only)
        Delete a product image.

        Response (204): No Content
    """

    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        product_pk = self.kwargs["product_pk"]
        return ProductImage.objects.filter(product_id=product_pk)

    def get_serializer_context(self):
        return {"product_pk": self.kwargs["product_pk"]}


class ProductViewSet(ModelViewSet):
    """
    Product catalog API.

    Supports search, filtering, and ordering.
    Public users can browse products, while admins can manage them.

    Endpoints:
    ---------
    - GET /products/
        List products with filters, search, and ordering.

        Query Parameters:
        - search: search by name/category
        - ordering: price, created_at, average_rating
        - filters: defined in `ProductFilter`

        Example Response (200):
        [
            {
                "id": 10,
                "name": "Wireless Mouse",
                "price": 25.99,
                "average_rating": 4.5,
                "main_image": "https://example.com/media/products/mouse.jpg"
            }
        ]

    - GET /products/{id}/
        Retrieve product details including images and reviews.

        Example Response (200):
        {
            "id": 10,
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse",
            "price": 25.99,
            "average_rating": 4.5,
            "category": {"id": 2, "name": "Accessories"},
            "images": [...],
            "reviews": [...]
        }

    - POST /products/ (admin only)
        Create a new product.

    - PATCH/DELETE /products/{id}/ (admin only)
        Update or remove a product.
    """

    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_at", "price", "average_rating"]
    search_fields = ["name", "category__name"]
    ordering = ["-created_at"]
    filterset_class = ProductFilter
    serializer_action_classes = {
        "list": ProductListSerializer,
        "retrieve": ProductDetailsSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, ProductDetailsSerializer)

    def get_queryset(self):
        queryset = Product.objects.with_annotations().select_related("category")
        if self.action == "retrieve":
            return queryset.prefetch_related("reviews", "images")
        return queryset


class CategoryViewSet(ModelViewSet):
    """
    Category API with nested products.

    Endpoints:
    ---------
    - GET /categories/
        List all categories.

        Example Response (200):
        [
            {"id": 1, "name": "Electronics", "slug": "electronics"},
            {"id": 2, "name": "Clothing", "slug": "clothing"}
        ]

    - GET /categories/{id}/
        Retrieve category details with related products.

        Example Response (200):
        {
            "id": 1,
            "name": "Electronics",
            "products": [
                {"id": 10, "name": "Wireless Mouse", "price": 25.99}
            ]
        }

    - POST/PATCH/DELETE (admin only)
    """

    permission_classes = [IsAdminOrReadOnly]
    serializer_action_classes = {
        "list": CategoryListSerializer,
        "retrieve": CategoryDetailsSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(
            self.action, CategoryDetailsSerializer
        )

    def get_queryset(self):
        queryset = Category.objects.prefetch_related(
            Prefetch(
                "products",
                queryset=Product.objects.with_annotations()
                .select_related("category")
                .prefetch_related("reviews", "images"),
            )
        )
        return queryset


class ReviewViewSet(ModelViewSet):
    """
    Customer product reviews.

    Permissions:
    - Authenticated users can post reviews.
    - Admin can moderate (approve, update, delete).

    Endpoints:
    ---------
    - GET /products/{product_pk}/reviews/
        List reviews for a product.
        - Staff: sees all reviews.
        - Users: only approved reviews.

        Example Response (200):
        [
            {
                "id": 5,
                "rating": 5,
                "comment": "Great product!",
                "likes_count": 2,
                "user": {"id": 1, "first_name": "Alice"}
            }
        ]

    - POST /products/{product_pk}/reviews/
        Submit a new review.

        Example Request:
        {
            "rating": 4,
            "comment": "Good quality, fast shipping."
        }

        Example Response (201):
        {
            "id": 6,
            "rating": 4,
            "comment": "Good quality, fast shipping.",
            "is_approved": false
        }

    - PATCH/DELETE /products/{product_pk}/reviews/{id}/ (admin only)
        Update or remove reviews.
    """

    permission_classes = [ReviewPermission]
    queryset = Review.objects.all()
    filterset_class = ReviewFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            if self.action in ["retrieve", "list"]:
                return ReviewListAdminSerializer
            if self.action in ["update", "partial_update"]:
                return ReviewAdminUpdateSerializer
        return ReviewListUserSerializer

    def get_queryset(self):
        product_pk = self.kwargs["product_pk"]
        queryset = (
            Review.objects.filter(product_id=product_pk)
            .annotate(likes_count=Count("likes", distinct=True))
            .select_related("user")
            .prefetch_related(
                Prefetch(
                    "likes",
                    queryset=User.objects.only(
                        "id", "first_name", "last_name", "profile_pic"
                    ),
                )
            )
            .order_by("-created_at")
        )
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(is_approved=True)

    def get_serializer_context(self):
        context = {
            "product_pk": self.kwargs["product_pk"],
            "user": self.request.user,
        }
        return context


class CartViewSet(
    CreateModelMixin, RetrieveModelMixin, GenericViewSet, DestroyModelMixin
):
    """
    Shopping cart API.

    Endpoints:
    ---------
    - POST /carts/
        Create a new cart (returns UUID).

        Example Response (201):
        {"id": "uuid-1234", "items": []}

    - GET /carts/{id}/
        Retrieve cart with items.

        Example Response (200):
        {
            "id": "uuid-1234",
            "items": [
                {"id": 1, "product": {"id": 10, "name": "Mouse"}, "quantity": 2}
            ]
        }

    - DELETE /carts/{id}/
        Delete the cart.
        Response (204): No Content
    """

    serializer_class = CartSerializer
    queryset = Cart.objects.prefetch_related(
        Prefetch(
            "items__product", queryset=Product.objects.annotate(**main_image_subquery())
        )
    )
    lookup_value_regex = lookup_value_regex = (
        "[0-9a-fA-F]{8}\-?[0-9a-fA-F]{4}\-?[0-9a-fA-F]{4}\-?[0-9a-fA-F]{4}\-?[0-9a-fA-F]{12}"
    )


class CartItemViewSet(ModelViewSet):
    """
    Cart item operations.

    Endpoints:
    ---------
    - POST /carts/{cart_pk}/items/
        Add item to cart.

        Example Request:
        {"product_id": 10, "quantity": 2}

        Example Response (201):
        {"id": 1, "product": {"id": 10, "name": "Mouse"}, "quantity": 2}

    - PATCH /carts/{cart_pk}/items/{id}/
        Update item quantity.

        Example Request:
        {"quantity": 3}

        Example Response (200):
        {"id": 1, "product": {"id": 10, "name": "Mouse"}, "quantity": 3}

    - DELETE /carts/{cart_pk}/items/{id}/
        Remove item from cart.
        Response (204): No Content

    - GET /carts/{cart_pk}/items/
        List cart items.
    """

    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        cart_pk = self.kwargs["cart_pk"]
        queryset = CartItem.objects.prefetch_related(
            Prefetch(
                "product", queryset=Product.objects.annotate(**main_image_subquery())
            )
        ).filter(cart_id=cart_pk)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AddCartItemSerializer
        elif self.request.method == "PATCH":
            return UpdateCartItemSerializer
        return CartItemSerializer

    def get_serializer_context(self):
        return {"cart_pk": self.kwargs["cart_pk"]}


class OrderViewSet(ModelViewSet):
    """
    Orders API.

    Permissions:
    - Authenticated users can create and view their orders.
    - Admins can view/update/delete all orders.

    Endpoints:
    ---------
    - POST /orders/
        Place a new order from a cart.

        Example Request:
        {"cart_id": "uuid-1234"}

        Example Response (201):
        {
            "id": 100,
            "status": "PENDING",
            "items": [
                {"product": {"id": 10, "name": "Mouse"}, "quantity": 2}
            ]
        }

    - GET /orders/
        List orders (user: own orders, admin: all orders).

    - PATCH /orders/{id}/ (admin only)
        Update order status.

        Example Request:
        {"status": "SHIPPED"}

    - DELETE /orders/{id}/ (admin only)
        Cancel order.
    """

    http_method_names = ["get", "post", "patch", "delete", "options", "head"]

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = Order.objects.select_related("user").prefetch_related(
            Prefetch(
                "items__product",
                queryset=Product.objects.annotate(**main_image_subquery()),
            )
        )
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(user_id=user.id)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OrderCreateSerializer
        if self.request.method == "PATCH":
            return OrderUpdateSerializer
        if self.request.user.is_staff:
            return OrderForAdminSerializer
        return OrderForUsersSerializer

    def get_serializer_context(self):
        return {"user_id": self.request.user.id}

    def create(self, request, *args, **kwargs):
        create_order_serializer = OrderCreateSerializer(
            data=request.data, context={"user_id": self.request.user.id}
        )
        create_order_serializer.is_valid(raise_exception=True)
        craeted_order = create_order_serializer.save()

        serializer = OrderForUsersSerializer(craeted_order)
        return Response(serializer.data)


class AddressViewSet(ModelViewSet):
    """
    Address book API.

    Permissions:
    - Users can manage their addresses.
    - Admin can view all users' addresses.

    Endpoints:
    ---------
    - GET /addresses/
        List addresses.
        - User: own addresses.
        - Admin: all addresses.

        Example Response (200):
        [
            {"id": 1, "street": "Main St", "city": "Tehran", "postal_code": "12345"}
        ]

    - POST /addresses/
        Add new address.

        Example Request:
        {"street": "Main St", "city": "Tehran", "postal_code": "12345"}

    - PATCH/DELETE /addresses/{id}/
        Update or remove address.
    """

    serializer_class = AddressForUsersSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Address.objects.select_related("user").all()
        user = self.request.user
        if user.is_staff:
            return queryset
        return queryset.filter(user_id=user.id)

        return queryset

    def get_serializer_class(self):
        if self.request.user.is_staff:
            if self.action in ["retrieve", "list"]:
                return AddressForAdminSerializer
            if self.action in ["update", "partial_update"]:
                return AddressForUsersSerializer
        return AddressForUsersSerializer

    def get_serializer_context(self):
        return {"user": self.request.user}


class WishlistViewSet(ModelViewSet):
    """
    Wishlist API.

    Permissions:
    - Only authenticated users can manage wishlists.

    Endpoints:
    ---------
    - GET /wishlist/
        List user wishlist.

        Example Response (200):
        [
            {"id": 1, "product": {"id": 10, "name": "Wireless Mouse"}}
        ]

    - POST /wishlist/
        Add product to wishlist.

        Example Request:
        {"product_id": 10}

        Example Response (201):
        {"id": 1, "product": {"id": 10, "name": "Wireless Mouse"}}

    - DELETE /wishlist/{id}/
        Remove product from wishlist.
        Response (204): No Content
    """

    http_method_names = ["get", "post", "delete", "options", "head"]
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Wishlist.objects.filter(user_id=user_id).prefetch_related(
            Prefetch(
                "product",
                queryset=Product.objects.with_annotations()
                .select_related("category")
                .prefetch_related("reviews", "images"),
            )
        )

        return queryset

    def get_serializer_context(self):
        return {"user": self.request.user}
