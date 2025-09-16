from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, FloatField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Round
from rest_framework.viewsets import ModelViewSet

from .models import Category, Product, ProductImage, Review
from .permissions import IsAdminOrReadOnly, ReviewPermission
from .serializers import (
    CategoryDetailsSerializer,
    CategoryListSerializer,
    ProductDetailsSerializer,
    ProductImageSerializer,
    ProductListSerializer,
    ReviewAdminUpdateSerializer,
    ReviewListAdminSerializer,
    ReviewListUserSerializer,
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
