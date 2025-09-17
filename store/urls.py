from rest_framework_nested import routers

from .views import (
    CartItemViewSet,
    CartViewSet,
    CategoryViewSet,
    ProductImagesViewSet,
    ProductViewSet,
    ReviewViewSet,
)

router = routers.DefaultRouter()

router.register(prefix="products", viewset=ProductViewSet, basename="product")
router.register(prefix="categories", viewset=CategoryViewSet, basename="category")
router.register(prefix="carts", viewset=CartViewSet, basename="cart")

product_router = routers.NestedDefaultRouter(router, "products", lookup="product")
product_router.register(
    prefix="images", viewset=ProductImagesViewSet, basename="product-image"
)
product_router.register(
    prefix="reviews", viewset=ReviewViewSet, basename="product-review"
)

cart_item_router = routers.NestedDefaultRouter(router, "carts", lookup="cart")
cart_item_router.register(
    prefix="items", viewset=CartItemViewSet, basename="cart-items"
)

urlpatterns = router.urls + product_router.urls + cart_item_router.urls
