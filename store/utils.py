from django.db.models import OuterRef, Subquery


def main_image_subquery():
    from .models import ProductImage

    queryset = ProductImage.objects.filter(
        product=OuterRef("pk"), main_picture=True
    ).order_by("id")

    return {
        "main_image": Subquery(queryset.values("image")[:1]),
    }
