from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductViewSet, PublicMenuView

app_name = 'products'

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('catalog', ProductViewSet, basename='product')

urlpatterns = [
    path('menu/', PublicMenuView.as_view({'get': 'menu'}), name='public-menu'),
    path('', include(router.urls)),
]
