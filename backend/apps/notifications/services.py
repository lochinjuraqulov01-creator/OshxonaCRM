"""apps/notifications/services.py — Telegram Bot API orqali xabar yuborish.

Eslatma: bu servis Django jarayonidan ishlaydi (bot alohida aiogram
jarayonida faqat KIRUVCHI xabarlarga javob beradi). Shu tufayli
admin buyurtma holatini o'zgartirsa, mijozga xabar bot ishlamasa ham boradi.
"""
import logging

import httpx
from django.conf import settings

from .models import NotificationLog

logger = logging.getLogger('apps')

STATUS_EMOJI = {
    'new': '🆕',
    'preparing': '👨‍🍳',
    'in_progress': '🚶',
    'delivered': '✅',
    'cancelled': '❌',
}


def send_telegram_message(chat_id: int | str, text: str,
                          reply_markup: dict | None = None) -> tuple[bool, str]:
    """Bot API ga HTTP so'rov.  (muvaffaqiyat, xato) qaytaradi."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning('TELEGRAM_BOT_TOKEN не настроен — сообщение не отправлено.')
        return False, 'Токен отсутствует'

    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        resp = httpx.post(
            f'{settings.TELEGRAM_API_URL}/sendMessage',
            json=payload, timeout=10)
        data = resp.json()
        if data.get('ok'):
            return True, ''
        return False, str(data.get('description', 'неизвестная ошибка'))
    except Exception as e:
        logger.error('Ошибка при отправке сообщения в Telegram: %s', e)
        return False, str(e)


def notify_order_status(order) -> None:
    """Buyurtma holati o'zgarganda mijozga xabar."""
    user = order.user
    if not user or not user.telegram_id:
        return

    emoji = STATUS_EMOJI.get(order.status, 'ℹ️')
    text = (
        f'{emoji} <b>Заказ #{order.order_number}</b>\n\n'
        f'Состояние: <b>{order.get_status_display()}</b>\n'
        f'Стол:  №{order.table.number}\n'
        f'Сумма: {order.total:,.0f} сум\n'
    )
    if order.status == 'in_progress':
        text += '\n🛎 Ваш заказ готов — сейчас доставим!'
    elif order.status == 'delivered':
        text += '\n🙏 Мы рады, что вам понравилось! Не забудьте оставить отзыв.'

    log = NotificationLog.objects.create(
        user=user, order=order, type=NotificationLog.TYPE_ORDER_STATUS,
        payload={'status': order.status, 'order_number': order.order_number})
    ok, error = send_telegram_message(user.telegram_id, text)
    log.is_sent = ok
    log.error = error
    log.save(update_fields=['is_sent', 'error'])


def notify_new_order(order) -> None:
    """Yangi buyurtma haqida oshxona adminiga xabar (ADMIN_CHAT_ID sozlangan bo'lsa)."""
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
    if not chat_id:
        return

    lines = [f'🆕 <b>НОВЫЙ ЗАКАЗ #{order.order_number}</b>', f'📍 Стол: №{order.table.number}', '']
    for item in order.items.all():
        lines.append(f'• {item.product_name} × {item.quantity} — {item.total_price:,.0f} сум')
    lines.append('')
    lines.append(f'💰 Итого: <b>{order.total:,.0f} so‘m</b>')
    if order.customer_note:
        lines.append(f'📝 Примечание: {order.customer_note}')

    log = NotificationLog.objects.create(
        order=order, type=NotificationLog.TYPE_NEW_ORDER,
        payload={'order_number': order.order_number})
    ok, error = send_telegram_message(chat_id, '\n'.join(lines))
    log.is_sent = ok
    log.error = error
    log.save(update_fields=['is_sent', 'error'])
