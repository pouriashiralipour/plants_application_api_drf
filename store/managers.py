"""
Custom querysets and managers for the e-commerce application.

This module defines reusable extensions to Django's default ORM
`QuerySet` that add annotations and computed fields to product
queries. The goal is to centralize complex query logic in a single
place, keeping views and serializers clean.

Classes
-------
ProductQuerySet
    A custom queryset class for the `Product` model that adds
    annotations such as the main image, average rating, and sales count.

Notes
-----
- Using custom querysets ensures complex annotations can be reused
  across multiple views, serializers, and business logic.
- Each annotation is computed at the database level, improving
  performance compared to Python-side calculations.
"""

from django.db.models import Avg, Count, FloatField, Q, QuerySet
from django.db.models.functions import Round

from .utils import main_image_subquery


class ProductQuerySet(QuerySet):
    """
    Custom queryset for the `Product` model.

    This queryset provides additional annotations that are commonly
    required for displaying or analyzing product data in the store.

    Features
    --------
    - Attaches the product's main image via a subquery.
    - Computes the average review rating, rounded to one decimal place.
    - Counts the number of successful sales (paid orders).

    Example
    -------
    >>> from store.models import Product
    >>> products = Product.objects.with_annotations()
    >>> products[0].average_rating
    4.5
    """

    def with_annotations(self):
        """
        Annotates each product with additional computed fields.

        The following fields are added to each product in the queryset:

        Annotations
        -----------
        main_image : str
            The path/URL of the product's main image, obtained via a
            subquery from `ProductImage`.
        average_rating : float
            The average rating (1–5) from related `Review` objects,
            rounded to one decimal place.
        sales_count : int
            The total number of times the product has been sold,
            counted from `OrderItem` entries where the parent order's
            payment status is `"Paid"`.

        Returns
        -------
        django.db.models.QuerySet
            A queryset of `Product` objects annotated with the fields
            above.

        Example
        -------
        >>> from store.models import Product
        >>> products = Product.objects.with_annotations()
        >>> for product in products:
        ...     print(product.name, product.main_image,
        ...           product.average_rating, product.sales_count)
        """
        return self.annotate(
            **main_image_subquery(),
            average_rating=Round(Avg("reviews__rating"), 1, output_field=FloatField()),
            sales_count=Count(
                "order_items", filter=Q(order_items__order__payment_status="Paid")
            )
        )
