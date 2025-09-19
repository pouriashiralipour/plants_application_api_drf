"""

Utility functions for query annotations and reusable ORM logic.

This module provides helper functions that simplify adding
complex annotations to Django querysets. Instead of repeating
subqueries or advanced ORM expressions across views or managers,
these helpers encapsulate them in clean, reusable functions.

Functions
---------
main_image_subquery()
    Returns a subquery expression that selects the main product
    image for use when annotating `Product` querysets.

Notes
-----
- By centralizing ORM subqueries here, the codebase becomes
  easier to maintain and avoids duplication.
- Subqueries are executed directly at the database level, which
  helps prevent the N+1 query problem when accessing related data.
"""

from django.db.models import OuterRef, Subquery


def main_image_subquery():
    """
    Build a subquery to fetch the main image for each product.

    This function constructs a Django ORM `Subquery` that retrieves
    the `image` field of the first `ProductImage` marked as the main
    picture for a given `Product`. It is intended to be used when
    annotating querysets of `Product` objects so each product can
    include its main image directly in query results.

    How it works
    ------------
    - Uses `OuterRef("pk")` to reference the current product in the
      outer queryset.
    - Filters `ProductImage` records for that product with
      `main_picture=True`.
    - Orders by primary key (`id`) to ensure deterministic selection
      if multiple images are flagged as main.
    - Wraps the query in a `Subquery` limited to the first record.

    Returns
    -------
    dict
        A dictionary with a single key `"main_image"`, whose value is
        a `Subquery` selecting the product's main image path/URL.

    Example
    -------
    >>> from store.models import Product
    >>> from store.utils import main_image_subquery
    >>> products = Product.objects.annotate(**main_image_subquery())
    >>> for product in products:
    ...     print(product.name, product.main_image)

    This approach avoids N+1 queries by embedding the image lookup
    in the main query itself.
    """
    from .models import ProductImage

    queryset = ProductImage.objects.filter(
        product=OuterRef("pk"), main_picture=True
    ).order_by("id")

    return {
        "main_image": Subquery(queryset.values("image")[:1]),
    }
