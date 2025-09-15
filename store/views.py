from django.db.models import OuterRef, Subquery
from rest_framework.viewsets import ModelViewSet

from .models import Product, ProductImage
from .permissions import IsAdminOrReadOnly
from .serializers import (
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

    def get_queryset(self):
        product_pk = self.kwargs["product_pk"]
        return ProductImage.objects.filter(product_id=product_pk)


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
            .select_related("category")
            .prefetch_related("reviews", "images")
        )
