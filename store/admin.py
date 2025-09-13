from django.contrib import admin
from django.utils.translation import gettext_lazy as _

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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    date_hierarchy = "created_at"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "category",
        "new_price",
        "old_price",
        "inventory",
        "is_active",
        "average_rating",
        "created_at",
    )
    list_filter = ("category", "is_active", "new_price", "old_price", "created_at")
    search_fields = (
        "name",
        "slug",
        "description",
    )
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    list_editable = ("new_price", "old_price", "inventory", "is_active")
    actions = ["mark_as_active", "mark_as_inactive"]
    inlines = [ProductImageInline]

    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)

    mark_as_active.short_description = _("Mark selected products as active")

    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)

    mark_as_inactive.short_description = _("Mark selected products as inactive")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image", "alt_text")
    list_filter = ("main_picture",)
    search_fields = (
        "product__name",
        "alt_text",
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("full_name", "name", "is_default")
    list_filter = ("is_default", "name")
    search_fields = (
        "full_name",
        "name",
        "postal_code",
    )
    list_editable = ("is_default",)

    def full_name(self, user):
        return user.full_name


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ("price_per_item",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "payment_status",
        "total_price",
        "order_date",
        "shipping_address",
    )
    list_filter = (
        "status",
        "payment_status",
        "order_date",
    )
    search_fields = (
        "user__full_name",
        "id",
    )
    date_hierarchy = "order_date"
    inlines = [OrderItemInline]
    actions = ["mark_as_shipped", "mark_as_delivered"]

    def mark_as_shipped(self, request, queryset):
        queryset.update(status="Shipped")

    mark_as_shipped.short_description = _("Mark selected orders as shipped")

    def mark_as_delivered(self, request, queryset):
        queryset.update(status="Delivered")

    mark_as_delivered.short_description = _("Mark selected orders as delivered")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "user",
        "rating",
        "is_approved",
        "created_at",
        "updated_at",
    )
    list_filter = ("rating", "is_approved", "created_at")
    search_fields = (
        "product__name",
        "user__full_name",
        "comment",
    )
    list_editable = ("is_approved",)
    actions = ["approve_reviews", "disapprove_reviews"]

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    approve_reviews.short_description = _("Approve selected reviews")

    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)

    disapprove_reviews.short_description = _("Disapprove selected reviews")


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at", "updated_at")
    list_filter = ("created_at",)
    search_fields = (
        "user__full_name",
        "product__name",
    )
    date_hierarchy = "created_at"


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "updated_at")
    list_filter = ("created_at",)
    date_hierarchy = "created_at"
    inlines = [CartItemInline]
