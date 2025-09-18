import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("category name"))
    description = models.TextField(verbose_name=_("description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_("id"))
    name = models.CharField(max_length=255, verbose_name=_("name"))
    slug = models.SlugField(_("slug"), unique=True, allow_unicode=True)
    description = models.TextField(verbose_name=_("description"))
    is_active = models.BooleanField(default=True, verbose_name=_("is active"))
    price = models.PositiveIntegerField(
        verbose_name=_("price"),
        validators=[MinValueValidator(0), MaxValueValidator(100000000)],
    )
    inventory = models.PositiveIntegerField(
        default=0,
        verbose_name=_("inventory"),
        validators=[MinValueValidator(0), MaxValueValidator(100000000)],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products",
        verbose_name=_("category"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["slug", "category"])]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("product"),
    )
    image = models.CharField(max_length=255, verbose_name=_("image"))
    main_picture = models.BooleanField(_("main picture"), default=False)

    class Meta:
        verbose_name = _("Product Image")
        verbose_name_plural = _("Product Images")

    def __str__(self):
        return self.product.name


class Address(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name=_("user"),
    )
    name = models.CharField(max_length=100, verbose_name=_("name"))
    address = models.CharField(max_length=255, verbose_name=_("address"))
    postal_code = models.CharField(max_length=20, verbose_name=_("postal code "))
    is_default = models.BooleanField(default=False, verbose_name=_("is default "))

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "is_default"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user}:{self.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", _("Pending")),
        ("Processing", _("Processing")),
        ("Shipped", _("Shipped")),
        ("Delivered", _("Delivered")),
        ("Cancelled", _("Cancelled")),
    ]
    PAID_CHOICES = [
        ("Pending", _("Pending")),
        ("Paid", _("Paid")),
        ("Failed", _("Failed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_("id"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("user"),
    )
    shipping_address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="shipping address",
    )
    order_date = models.DateTimeField(auto_now_add=True, verbose_name="order date")
    total_price = models.PositiveIntegerField(
        verbose_name=_("total price"),
        validators=[MinValueValidator(0), MaxValueValidator(100000000)],
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Pending",
        verbose_name="status",
    )
    payment_status = models.CharField(
        max_length=50,
        choices=PAID_CHOICES,
        default="Pending",
        verbose_name=_("payment status"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-order_date"]
        indexes = [models.Index(fields=["user", "order_date"])]

    def __str__(self):
        return f"{self.user} : {self.status}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("order")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name=_("product"),
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("quantity"))
    price_per_item = models.PositiveIntegerField(
        verbose_name=_("price per item"),
        validators=[MinValueValidator(0), MaxValueValidator(100000000)],
    )

    class Meta:
        verbose_name = _("OrderItem")
        verbose_name_plural = _("OrderItems")

    def __str__(self):
        return f"{self.order.id}:{self.product}-{self.quantity}"


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("product"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("user"),
    )
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_("rating"),
    )
    comment = models.TextField(blank=True, null=True, verbose_name=_("comment"))
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="liked_comments", blank=True
    )
    is_approved = models.BooleanField(default=True, verbose_name=_("Is Approved"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("review")
        verbose_name_plural = _("reviews")
        unique_together = (
            "product",
            "user",
        )
        ordering = ["-created_at"]
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "user"])]

    def __str__(self):
        user = getattr(self.user, "user__full_name", str(self.user_id))
        return _("Review by %(user)s — %(product)s (%(rating)d/5)") % {
            "user": user,
            "product": self.product.name,
            "rating": self.rating,
        }


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
        verbose_name=_("user"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
        verbose_name=_("product"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Wishlist")
        verbose_name_plural = _("Wishlists")
        unique_together = (
            "user",
            "product",
        )
        indexes = [models.Index(fields=["user", "product"])]

    def __str__(self):
        return f"{self.user.full_name}:{self.product.name}"


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_("id"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        return f"{self.id}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name=_("cart")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("product"),
    )
    quantity = models.PositiveSmallIntegerField(verbose_name=_("quantity"))

    class Meta:
        verbose_name = _("CartItem")
        verbose_name_plural = _("CartItems")
        unique_together = [["cart", "product"]]
        indexes = [models.Index(fields=["cart", "product"])]

    def __str__(self):
        return f"{self.product.name}:{self.quantity}"
