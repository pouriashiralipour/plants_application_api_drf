from django.db.models import Prefetch
from rest_framework.viewsets import ModelViewSet

from .models import Product, ProductImage
from .serializers import ProductListSerializer


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
