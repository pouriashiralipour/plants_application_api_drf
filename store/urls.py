from rest_framework_nested import routers

from .views import CategoryViewSet, ProductImagesViewSet, ProductViewSet, ReviewViewSet

router = routers.DefaultRouter()

router.register(prefix="products", viewset=ProductViewSet, basename="product")
router.register(prefix="categories", viewset=CategoryViewSet, basename="category")

product_router = routers.NestedDefaultRouter(router, "products", lookup="product")
product_router.register(
    prefix="images", viewset=ProductImagesViewSet, basename="product-image"
)
product_router.register(
    prefix="reviews", viewset=ReviewViewSet, basename="product-review"
)

urlpatterns = router.urls + product_router.urls
