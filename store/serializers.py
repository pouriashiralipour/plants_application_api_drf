from rest_framework import serializers

from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    serializers.BooleanField(write_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "main_picture"]

    def create(self, validated_data):
        product_id = self.context["product_pk"]
        return ProductImage.objects.create(product_id=product_id, **validated_data)


class CategoryProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class ProductListSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="main_image", read_only=True)
    images = ProductImageSerializer(write_only=True)
    category = CategoryProductSerializer()
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "category",
            "average_rating",
            "image",
            "images",
        ]


class ProductDetailsSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategoryProductSerializer(read_only=True)
    category_name = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="name",
        source="category",
        write_only=True,
    )
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "category",
            "category_name",
            "description",
            "inventory",
            "average_rating",
            "price",
            "images",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return Product.objects.create(**validated_data)
