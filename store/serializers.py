from core.models import CustomUser
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import (
    Address,
    Cart,
    CartItem,
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Review,
    Wishlist,
)


class UserReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "profile_pic"]
        read_only_fields = ["id", "full_name", "profile_pic"]


class AddressUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "phone_number", "email"]
        read_only_fields = ["id", "full_name", "phone_number", "email"]


class AddressForAdminSerializer(serializers.ModelSerializer):
    user = AddressUserSerializer()

    class Meta:
        model = Address
        fields = ["id", "user", "name", "address", "postal_code", "is_default"]
        read_only_fields = ["id", "user"]


class AddressForUsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "name", "address", "postal_code", "is_default"]

    def create(self, validated_data):
        user = self.context["user"]

        if validated_data.get("is_default", False):
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        else:
            validated_data["is_default"] = False

        return Address.objects.create(user=user, **validated_data)


class ProductImageSerializer(serializers.ModelSerializer):
    main_picture = serializers.BooleanField(write_only=True)

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
    sales_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "price",
            "category",
            "average_rating",
            "sales_count",
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
    sales_count = serializers.IntegerField(read_only=True)
    total_reviews = serializers.IntegerField(read_only=True)

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
            "sales_count",
            "total_reviews",
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
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "rating",
            "comment",
            "likes_count",
            "is_liked_by_me",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(id=user.id).exists()

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


class OrderItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product",
            "quantity",
        ]


class OrderUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=255)

    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "nickname", "phone_number", "email"]


class OrderForAdminSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    user = OrderUserSerializer()

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "shipping_address",
            "order_date",
            "total_price",
            "status",
            "payment_status",
            "items",
        ]


class OrderForUsersSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_date",
            "total_price",
            "status",
            "items",
        ]


class OrderCreateSerializer(serializers.Serializer):
    cart_id = serializers.UUIDField(write_only=True)

    def validate_cart_id(self, cart_id):
        try:
            if (
                Cart.objects.prefetch_related("items").get(id=cart_id).items.count()
            ) == 0:
                raise ValidationError(_("Your Cart is empty."))
        except Cart.DoesNotExist:
            raise serializers.ValidationError(_("There is no cart with this id."))
        return cart_id

    def save(self, **kwargs):
        cart_id = self.validated_data["cart_id"]
        user_id = self.context["user_id"]

        user = CustomUser.objects.get(id=user_id)
        cart = Cart.objects.get(id=cart_id)

        cart_items = CartItem.objects.select_related("product").filter(cart_id=cart_id)
        total_price = sum(item.quantity * item.product.price for item in cart_items)

        order = Order.objects.create(user=user, total_price=total_price)

        order_items = [
            OrderItem(
                order=order,
                product_id=cart_item.product.id,
                quantity=cart_item.quantity,
                price_per_item=cart_item.product.price,
            )
            for cart_item in cart_items
        ]

        OrderItem.objects.bulk_create(order_items)

        cart.delete()

        return order


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status", "payment_status"]


class WishlistSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True)
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ["id", "product", "product_id"]
        read_only_fields = ["id"]

    def validate_product_id(self, product_id):
        if not Product.objects.filter(id=product_id).exists():
            raise serializers.ValidationError(_("Product does not exist."))
        return product_id

    def create(self, validated_data):
        user = self.context["user"]
        product_id = validated_data["product_id"]
        return Wishlist.objects.create(user=user, product_id=product_id)
