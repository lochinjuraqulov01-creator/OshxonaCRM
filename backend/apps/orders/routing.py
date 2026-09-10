"""apps/orders/routing.py"""
from django.urls import re_path

from .consumers import AdminOrderConsumer

websocket_urlpatterns = [
    re_path(r'ws/admin/orders/$', AdminOrderConsumer.as_asgi()),
]
