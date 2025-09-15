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
    image = serializers.CharField(source="main_image", read_only=True)
    images = ProductImageSerializer(write_only=True)
    category = CategoryProductSerializer()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "category", "image", "images"]


class ProductDetailsSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategoryProductSerializer()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "description",
            "inventory",
            "price",
            "images",
        ]
        read_only_fields = ["id"]
