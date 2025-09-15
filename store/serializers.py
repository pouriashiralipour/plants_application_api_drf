from rest_framework import serializers

from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image"]


class CategoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    category = CategoryProductSerializer()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "category", "images"]
