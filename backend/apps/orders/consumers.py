"""apps/orders/consumers.py — WebSocket real-time.

Admin Panel ws://.../ws/admin/orders/?token=<JWT> manziliga ulanadi:
  • yangi buyurtma kelganda → 'order_new' hodisasi
  • holat o'zgarganda       → 'order_status' hodisasi
Frontend toast + ovozli bildirishnoma bilan ko'rsatadi.
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger('apps')


class AdminOrderConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = 'admin_orders'

    async def connect(self):
        # JWT tokenni query paramdan tekshiramiz
        user = await self._authenticate()
        if user is None:
            await self.close(code=4001)
            return
        if not user.is_staff:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            'event': 'connected',
            'message': 'Real-time подключение установлено.',
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Admin faqat tinglaydi
        pass

    async def order_event(self, event):
        """Group orqali keldi → brauzerga yuborish."""
        await self.send(text_data=json.dumps(event['data'], ensure_ascii=False))

    @database_sync_to_async
    def _authenticate(self):
        query = self.scope.get('query_string', b'').decode()
        token = None
        for part in query.split('&'):
            if part.startswith('token='):
                token = part[6:]
                break
        if not token:
            return None
        try:
            AccessToken(token)      # yaroqli bo'lsa exception bermaydi
            from apps.users.models import User
            # Token ichidagi user_id ni olish
            access = AccessToken(token)
            return User.objects.filter(id=access['user_id']).first()
        except (TokenError, Exception):
            logger.warning('Ошибка авторизации WS — недействительный токен.')
            return None


# ---------------- Yordamchi (broadcast) ----------------

def broadcast_order_event(event: str, data: dict):
    """Buyurtma hodisasini admin group ga yuborish (sync kontekstdan)."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            'admin_orders',
            {
                'type': 'order_event',
                'data': {'event': event, **data},
            },
        )
    except Exception as e:
        logger.error('Ошибка WS-рассылки (broadcast): %s', e)
