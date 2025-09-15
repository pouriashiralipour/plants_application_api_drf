from rest_framework_nested import routers

from .views import ProductImagesViewSet, ProductViewSet

router = routers.DefaultRouter()

router.register(prefix="products", viewset=ProductViewSet, basename="product")

product_router = routers.NestedDefaultRouter(router, "products", lookup="product")
product_router.register(
    prefix="images", viewset=ProductImagesViewSet, basename="product-image"
)

urlpatterns = router.urls + product_router.urls
