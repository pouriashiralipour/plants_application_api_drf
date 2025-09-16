from django.db.models import Avg, FloatField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Round
from rest_framework.viewsets import ModelViewSet

from .models import Category, Product, ProductImage
from .permissions import IsAdminOrReadOnly
from .serializers import (
    CategoryDetailsSerializer,
    CategoryListSerializer,
    ProductDetailsSerializer,
    ProductImageSerializer,
    ProductListSerializer,
)


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
