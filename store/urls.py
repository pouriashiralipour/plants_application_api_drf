from rest_framework_nested import routers

from .views import ProductViewSet

router = routers.DefaultRouter()

router.register(prefix="products", viewset=ProductViewSet, basename="product")


urlpatterns = router.urls
