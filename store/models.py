"""
E-commerce Application Models
=============================

This module defines the core database models for the e-commerce platform.
It provides the foundational data structures that support product management,
customer accounts, order processing, shopping carts, and user interactions
such as reviews and wishlists.

Overview
--------

The models in this module encapsulate the following entities:

- **Category**:
  Organizes products into logical groups for easier browsing and filtering.

- **Product**:
  Represents items available for sale, including attributes such as name,
  description, price, inventory, and category association.

- **ProductImage**:
  Stores product-related images, with support for identifying the main display image.

- **Address**:
  Maintains user addresses, supporting multiple addresses per user and
  enforcing a single default address.

- **Order**:
  Tracks purchases made by users, including status, payment state, total price,
  and shipping address.

- **OrderItem**:
  Associates products with orders, capturing quantity and unit price at the
  time of purchase.

- **Review**:
  Allows users to submit product reviews with ratings, optional comments,
  and like functionality. Reviews can be approved for moderation purposes.

- **Wishlist**:
  Enables users to bookmark products they are interested in purchasing later.

- **Cart**:
  Represents a shopping cart session (for both anonymous and authenticated users),
  used to temporarily hold products before checkout.

- **CartItem**:
  Associates products with a cart, recording the chosen quantity.

Features
--------

- UUIDs are used as primary keys for core entities such as products, orders,
  and carts for uniqueness and scalability.
- Constraints and indexes are applied to optimize queries and enforce data
  integrity (e.g., unique default address per user, unique wishlist entries).
- Custom model managers (e.g., `ProductQuerySet`) are integrated for advanced
  product queries.
- Timestamps (`created_at`, `updated_at`) are included on most models to
  support auditing and chronological ordering.
- Support for internationalization (i18n) is provided via Django's
  `gettext_lazy`.

Usage
-----

These models form the backbone of the e-commerce system and are intended to be
interacted with through Django's ORM, views, and serializers. They support
typical workflows such as:

1. Creating and categorizing products.
2. Managing shopping carts and persisting them across sessions.
3. Processing user orders and tracking fulfillment status.
4. Collecting and moderating user-generated reviews.
5. Allowing customers to save favorite items via wishlists.

Example::

    >>> from store.models import Product, Category
    >>> category = Category.objects.create(name="Plants", description="Indoor plants")
    >>> product = Product.objects.create(
    ...     name="Aloe Vera",
    ...     slug="aloe-vera",
    ...     description="A natural air purifier.",
    ...     price=15000,
    ...     inventory=20,
    ...     category=category,
    ... )
    >>> str(product)
    'Aloe Vera'

This module should be imported by Django automatically when applying migrations
or performing ORM queries, and typically does not require direct imports in
application logic beyond normal model usage.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import ProductQuerySet


class Category(models.Model):
    """
    Represents a product category.

    Categories are used to organize products into logical groups,
    making it easier for customers to browse and filter items.

    Fields
    ------
    name : str
        The name of the category (max length: 100).
    description : str
        A text description of the category's purpose or content.
    created_at : datetime
        Timestamp when the category was created (auto-generated).
    updated_at : datetime
        Timestamp when the category was last updated (auto-generated).

    Relationships
    -------------
    products : RelatedManager[Product]
        Reverse relation to products assigned to this category.

    Meta
    ----
    verbose_name : "Category"
    verbose_name_plural : "Categories"

    Example
    -------
    >>> category = Category.objects.create(name="Indoor Plants", description="Houseplants")
    >>> str(category)
    'Indoor Plants'
    """

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
    """
    Represents an individual product available for purchase.

    Each product includes core details such as name, description,
    price, and available inventory. Products are associated with
    a category and may include one or more related images.

    Fields
    ------
    id : UUID
        Unique identifier for the product (auto-generated).
    name : str
        The display name of the product.
    slug : str
        A unique slug for URL usage (supports Unicode).
    description : str
        Detailed information about the product.
    is_active : bool
        Whether the product is available for sale.
    price : int
        Product price in smallest currency unit (e.g., rials).
    inventory : int
        Current stock quantity available for sale.
    created_at : datetime
        When the product was added to the system.
    updated_at : datetime
        Last modification time of the product.

    Relationships
    -------------
    category : Category (nullable)
        Category this product belongs to.
    images : RelatedManager[ProductImage]
        Associated product images.
    reviews : RelatedManager[Review]
        Customer reviews for this product.
    order_items : RelatedManager[OrderItem]
        Order items that reference this product.
    cart_items : RelatedManager[CartItem]
        Cart items that reference this product.
    wishlisted_by : RelatedManager[Wishlist]
        Wishlists that include this product.

    Meta
    ----
    ordering : ["-created_at"]
    indexes : [("slug", "category")]

    Example
    -------
    >>> product = Product.objects.create(
    ...     name="Aloe Vera",
    ...     slug="aloe-vera",
    ...     description="Natural air purifier",
    ...     price=15000,
    ...     inventory=25
    ... )
    >>> str(product)
    'Aloe Vera'
    """

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

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["slug", "category"])]

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """
    Stores product images.

    Each image belongs to a single product. One image may be marked
    as the main display picture.

    Fields
    ------
    image : str
        Path or identifier for the image file.
    main_picture : bool
        Whether this image is the product's main picture.

    Relationships
    -------------
    product : Product
        The product this image belongs to.

    Meta
    ----
    verbose_name : "Product Image"
    verbose_name_plural : "Product Images"
    """

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
    """
    Stores a user's address.

    Users can register multiple addresses and set one as their default.

    Fields
    ------
    name : str
        Label for the address (e.g., "Home", "Office").
    address : str
        The street and location details.
    postal_code : str
        Postal or ZIP code.
    is_default : bool
        Marks whether this address is the default for the user.

    Relationships
    -------------
    user : settings.AUTH_USER_MODEL
        The owner of the address.

    Constraints
    -----------
    - Only one default address is allowed per user.

    Meta
    ----
    verbose_name : "Address"
    verbose_name_plural : "Addresses"
    """

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
    """
    Represents a customer order.

    Orders track products purchased by users, their payment status,
    shipping address, and order lifecycle.

    Fields
    ------
    id : UUID
        Unique identifier for the order.
    order_date : datetime
        The time when the order was placed.
    total_price : int
        The total cost of the order.
    status : str
        Order processing stage (Pending, Processing, Shipped, Delivered, Cancelled).
    payment_status : str
        Payment result (Pending, Paid, Failed).
    updated_at : datetime
        Last modification time.

    Relationships
    -------------
    user : settings.AUTH_USER_MODEL
        The customer who placed the order.
    shipping_address : Address (nullable)
        The address where the order will be delivered.
    items : RelatedManager[OrderItem]
        Products included in the order.

    Meta
    ----
    ordering : ["-order_date"]
    indexes : [("user", "order_date")]
    """

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
    """
    Represents a single product within an order.

    Captures the product, quantity, and price at the time of purchase.

    Fields
    ------
    quantity : int
        The number of units of the product.
    price_per_item : int
        Price of each unit at the time of order.

    Relationships
    -------------
    order : Order
        The order this item belongs to.
    product : Product
        The purchased product.

    Meta
    ----
    verbose_name : "OrderItem"
    verbose_name_plural : "OrderItems"
    """

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
    """
    Represents a customer review for a product.

    Reviews include ratings, optional comments, and likes from other users.

    Fields
    ------
    rating : int
        A value between 1 and 5.
    comment : str
        Optional review text.
    is_approved : bool
        Whether the review is visible on the site.
    created_at : datetime
        Review creation timestamp.
    updated_at : datetime
        Last updated timestamp.

    Relationships
    -------------
    product : Product
        The product being reviewed.
    user : settings.AUTH_USER_MODEL
        The author of the review.
    likes : ManyToMany[User]
        Users who liked this review.

    Constraints
    -----------
    - Each user may review a product only once.

    Meta
    ----
    ordering : ["-created_at"]
    indexes : [("product", "user")]
    """

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
    """
    Represents a user's wishlist item.

    Stores products that a user is interested in for future purchases.

    Fields
    ------
    created_at : datetime
        When the wishlist entry was created.
    updated_at : datetime
        When the wishlist entry was last updated.

    Relationships
    -------------
    user : settings.AUTH_USER_MODEL
        The owner of the wishlist.
    product : Product
        The product added to the wishlist.

    Constraints
    -----------
    - A product can only appear once in a user's wishlist.

    Meta
    ----
    indexes : [("user", "product")]
    """

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
    """
    Represents a shopping cart session.

    Carts are used to temporarily hold products before checkout.

    Fields
    ------
    id : UUID
        Unique identifier for the cart.
    created_at : datetime
        When the cart was created.
    updated_at : datetime
        Last modification timestamp.

    Relationships
    -------------
    items : RelatedManager[CartItem]
        Products currently in the cart.

    Meta
    ----
    verbose_name : "Cart"
    verbose_name_plural : "Carts"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, verbose_name=_("id"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created_at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated_at"))

    class Meta:
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        return f"{self.id}"


class CartItem(models.Model):
    """
    Represents a product within a shopping cart.

    Tracks the selected product and its quantity.

    Fields
    ------
    quantity : int
        The number of units of the product in the cart.

    Relationships
    -------------
    cart : Cart
        The cart this item belongs to.
    product : Product
        The product added to the cart.

    Constraints
    -----------
    - Each product may only appear once per cart.

    Meta
    ----
    indexes : [("cart", "product")]
    """

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
