from django_filters.rest_framework import FilterSet, filters

from .models import Category, Product, Review


class ProductFilter(FilterSet):
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
        if value == "all":
            return queryset
        return queryset.filter(average_rating__gte=int(value))


class ReviewFilter(FilterSet):
    rating = filters.ChoiceFilter(
        method="filter_by_rating",
        choices=[(i, f"{i} star") for i in range(1, 6)] + [("all", "all")],
    )

    class Meta:
        model = Review
        fields = ["rating"]

    def filter_by_rating(self, queryset, name, value):
        if value == "all":
            return queryset
        return queryset.filter(rating__exact=int(value))
