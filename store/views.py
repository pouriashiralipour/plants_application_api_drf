from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, FloatField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Round
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin,
)
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

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

User = get_user_model()


def main_image_subquery():
    queryset = ProductImage.objects.filter(
        product=OuterRef("pk"), main_picture=True
    ).order_by("id")

    return {
        "main_image": Subquery(queryset.values("image")[:1]),
    }


class ProductImagesViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        product_pk = self.kwargs["product_pk"]
        return ProductImage.objects.filter(product_id=product_pk)

    def get_serializer_context(self):
        return {"product_pk": self.kwargs["product_pk"]}


class ProductViewSet(ModelViewSet):
    permission_classes = [IsAdminOrReadOnly]
    serializer_action_classes = {
        "list": ProductListSerializer,
        "retrieve": ProductDetailsSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_action_classes.get(self.action, ProductDetailsSerializer)

    def get_queryset(self):
        return (
            Product.objects.annotate(**main_image_subquery())
            .annotate(
                average_rating=Round(
                    Avg("reviews__rating"), 1, output_field=FloatField()
                )
            )
            .select_related("category")
            .prefetch_related("reviews", "images")
        )


class CategoryViewSet(ModelViewSet):
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
                queryset=Product.objects.annotate(**main_image_subquery())
                .annotate(
                    average_rating=Round(
                        Avg("reviews__rating"), 1, output_field=FloatField()
                    )
                )
                .select_related("category")
                .prefetch_related("reviews", "images"),
            )
        )
        return queryset


class ReviewViewSet(ModelViewSet):
    permission_classes = [ReviewPermission]
    queryset = Review.objects.all()

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
    http_method_names = ["get", "post", "delete", "options", "head"]
    permission_classes = [IsAuthenticated]
    serializer_class = WishlistSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        queryset = Wishlist.objects.filter(user_id=user_id).prefetch_related(
            Prefetch(
                "product",
                queryset=Product.objects.annotate(**main_image_subquery())
                .annotate(
                    average_rating=Round(
                        Avg("reviews__rating"), 1, output_field=FloatField()
                    )
                )
                .select_related("category")
                .prefetch_related("reviews", "images"),
            )
        )

        return queryset

    def get_serializer_context(self):
        return {"user": self.request.user}
