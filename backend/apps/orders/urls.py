from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminOrderViewSet,
    CartAddView,
    CartClearView,
    CartItemUpdateView,
    CartView,
    CustomerOrderViewSet,
)

app_name = 'orders'

customer_router = DefaultRouter()
customer_router.register('orders', CustomerOrderViewSet, basename='order')

admin_router = DefaultRouter()
admin_router.register('admin-orders', AdminOrderViewSet, basename='admin-order')

urlpatterns = [
    # Savat
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', CartAddView.as_view(), name='cart-add'),
    path('cart/clear/', CartClearView.as_view(), name='cart-clear'),
    path('cart/items/<uuid:item_id>/', CartItemUpdateView.as_view(), name='cart-item'),
    # Mijoz buyurtmalari
    path('', include(customer_router.urls)),
    # Admin buyurtmalari
    path('', include(admin_router.urls)),
]
