"""
config/asgi.py — ASGI kirish nuqtasi.
HTTP + WebSocket (Channels) so'rovlarini boshqaradi.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack                      # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter         # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
import apps.orders.routing                                         # noqa: E402

application = ProtocolTypeRouter({
    # Oddiy HTTP so'rovlar — Django
    'http': django_asgi_app,
    # WebSocket so'rovlar — Channels
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(apps.orders.routing.websocket_urlpatterns)
        )
    ),
})
