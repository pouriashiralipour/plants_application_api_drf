from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from core.models import CustomUser

from .models import Cart, CartItem, Category, Product, ProductImage, Review


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

    def create(self, validated_data):
        product_id = self.context["product_pk"]
        user = self.context["user"]

        if Review.objects.filter(product_id=product_id, user=user).exists():
            raise ValidationError(
                {"detail": _("You have already submitted a review for this product.")}
            )
        return Review.objects.create(product_id=product_id, user=user, **validated_data)


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


class CartProductSerializer(serializers.ModelSerializer):
    image = serializers.CharField(source="main_image", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "price", "image"]


class CartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer()
    item_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "item_price"]

    def get_item_price(self, obj):
        return obj.quantity * obj.product.price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price"]
        read_only_fields = ["id"]

    def get_total_price(self, obj):
        return sum([item.quantity * item.product.price for item in obj.items.all()])


class AddCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity"]

    def create(self, validated_data):
        cart_id = self.context["cart_pk"]

        product = validated_data.get("product")
        quantity = validated_data.get("quantity")

        if product.inventory < quantity:
            raise ValidationError(_("Quantity must less than inventory"))
        try:
            cart_item = CartItem.objects.get(cart_id=cart_id, product_id=product.id)
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(cart_id=cart_id, **validated_data)

        self.instance = cart_item
        return cart_item


class UpdateCartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]
