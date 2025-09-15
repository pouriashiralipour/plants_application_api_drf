from django.db.models import OuterRef, Prefetch, Subquery
from rest_framework.viewsets import ModelViewSet

from .models import Product, ProductImage
from .serializers import ProductListSerializer


def main_image_subquery():
    queryset = ProductImage.objects.filter(
        product=OuterRef("pk"), main_picture=True
    ).order_by("id")

    return {
        "main_image": Subquery(queryset.values("image")[:1]),
    }


class ProductViewSet(ModelViewSet):
    serializer_class = ProductListSerializer
    queryset = Product.objects.all()

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("category")
            .prefetch_related(
                Prefetch(
                    "images", queryset=ProductImage.objects.filter(main_picture=True)
                )
            )
            .all()
        )
        return queryset
