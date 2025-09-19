"""
Custom filters for product and review querysets.

This module defines reusable `django-filter` filter sets that enable
API consumers to filter products and reviews by various criteria such as
category, price range, and rating. These filters integrate seamlessly with
Django REST Framework when using `django_filters.rest_framework.DjangoFilterBackend`.

Classes
-------
ProductFilter
    Provides filtering options for `Product` objects, including category,
    price range, and average rating.

ReviewFilter
    Provides filtering options for `Review` objects, specifically by rating.

Usage
-----
When applied to DRF views, these filters allow clients to pass query
parameters such as `?category=Plants&price_min=100&price_max=500&rating=4`
to filter the results dynamically.
"""

from django_filters.rest_framework import FilterSet, filters

from .models import Category, Product, Review


class ProductFilter(FilterSet):
    """
    FilterSet for the `Product` model.

    Enables filtering products by category, price range, and rating.

    Filters
    -------
    category : ChoiceFilter
        Filters by product category name.
        Choices are dynamically populated from existing categories.
    price_min : NumberFilter
        Minimum product price (inclusive).
    price_max : NumberFilter
        Maximum product price (inclusive).
    rating : ChoiceFilter
        Filters products by their annotated `average_rating`.
        Choices range from 1 to 5 stars, plus an `"all"` option to disable filtering.

    Meta
    ----
    model : Product
        The model being filtered.
    fields : list[str]
        Filterable fields: ["category", "price_min", "price_max", "rating"]

    Example
    -------
    >>> from store.filters import ProductFilter
    >>> f = ProductFilter({"price_min": 10000, "rating": 4}, queryset=Product.objects.all())
    >>> qs = f.qs  # filtered queryset
    """

    category = filters.ChoiceFilter(
        choices=Category.objects.values_list("name", "name"),
        field_name="category__name",
        label="Category",
        empty_label="Categories",
    )
    price_min = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="price", lookup_expr="lte")
    rating = filters.ChoiceFilter(
        method="filter_by_rating",
        choices=[(i, f"{i} star") for i in range(1, 6)] + [("all", "all")],
    )

    class Meta:
        model = Product
        fields = ["category", "price_min", "price_max", "rating"]

    def filter_by_rating(self, queryset, name, value):
        """
        Custom filter for product average rating.

        Parameters
        ----------
        queryset : QuerySet[Product]
            The initial product queryset.
        name : str
            The name of the filter field ("rating").
        value : str | int
            The filter value (1–5 or "all").

        Returns
        -------
        QuerySet[Product]
            The filtered queryset. If `value` is `"all"`, the queryset
            is returned unchanged.
        """
        if value == "all":
            return queryset
        return queryset.filter(average_rating__gte=int(value))


class ReviewFilter(FilterSet):
    """
    FilterSet for the `Review` model.

    Enables filtering reviews by rating.

    Filters
    -------
    rating : ChoiceFilter
        Filters reviews by their `rating` field.
        Choices range from 1 to 5 stars, plus an `"all"` option.

    Meta
    ----
    model : Review
        The model being filtered.
    fields : list[str]
        Filterable fields: ["rating"]

    Example
    -------
    >>> from store.filters import ReviewFilter
    >>> f = ReviewFilter({"rating": 5}, queryset=Review.objects.all())
    >>> qs = f.qs  # filtered queryset
    """

    rating = filters.ChoiceFilter(
        method="filter_by_rating",
        choices=[(i, f"{i} star") for i in range(1, 6)] + [("all", "all")],
    )

    class Meta:
        model = Review
        fields = ["rating"]

    def filter_by_rating(self, queryset, name, value):
        """
        Custom filter for review rating.

        Parameters
        ----------
        queryset : QuerySet[Review]
            The initial review queryset.
        name : str
            The name of the filter field ("rating").
        value : str | int
            The filter value (1–5 or "all").

        Returns
        -------
        QuerySet[Review]
            The filtered queryset. If `value` is `"all"`, the queryset
            is returned unchanged.
        """
        if value == "all":
            return queryset
        return queryset.filter(rating__exact=int(value))
