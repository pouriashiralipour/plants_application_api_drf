from django.db.models import Avg, Count, FloatField, Q, QuerySet
from django.db.models.functions import Round

from .utils import main_image_subquery


class ProductQuerySet(QuerySet):
    def with_annotations(self):
        return self.annotate(
            **main_image_subquery(),
            average_rating=Round(Avg("reviews__rating"), 1, output_field=FloatField()),
            sales_count=Count(
                "order_items", filter=Q(order_items__order__payment_status="Paid")
            )
        )
