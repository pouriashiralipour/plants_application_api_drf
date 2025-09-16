from rest_framework import serializers

from core.models import CustomUser

from .models import Category, Product, ProductImage, Review


class UserReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "profile_pic"]
        read_only_fields = ["id", "full_name", "profile_pic"]


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


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]
        read_only_fields = ["id"]


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


class CategoryDetailsSerializer(serializers.ModelSerializer):
    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "products"]
        read_only_fields = ["id"]


class ReviewAdminUpdateSerializer(serializers.ModelSerializer):
    user = UserReviewSerializer(read_only=True)
    likes = serializers.SerializerMethodField()
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "rating",
            "comment",
            "likes",
            "likes_count",
            "is_approved",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user",
            "rating",
            "comment",
            "likes",
            "likes_count",
            "created_at",
            "updated_at",
        ]

    def get_likes(self, obj):
        return (
            [user.full_name for user in obj.likes.all()]
            if hasattr(obj, "likes")
            else []
        )


class ReviewListUserSerializer(serializers.ModelSerializer):
    user = UserReviewSerializer(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "rating",
            "comment",
            "likes_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ReviewListAdminSerializer(serializers.ModelSerializer):
    user = UserReviewSerializer(read_only=True)
    likes = UserReviewSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "rating",
            "comment",
            "likes",
            "likes_count",
            "is_approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "likes", "created_at", "updated_at"]
