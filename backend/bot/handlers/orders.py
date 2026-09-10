"""bot/handlers/orders.py — mijoz buyurtmalari ko'rinishi."""
import logging

from aiogram import F, Router
from aiogram.types import Message
from django.utils import timezone

from bot.keyboards import orders_webapp_inline

logger = logging.getLogger('bot')
router = Router()

STATUS_EMOJI = {
    'new': '🆕 Новый',
    'preparing': '👨‍🍳 Готовится',
    'in_progress': '🚶 В процессе (доставляется)',
    'delivered': '✅ Доставлен',
    'cancelled': '❌ Отменён',
}

@router.message(F.text.in_({'📋 Mening buyurtmalarim', '📋 Мои заказы'}))
async def btn_my_orders(message: Message):
    """Oxirgi 5 buyurtma holati."""
    from apps.orders.models import Order
    from apps.users.models import User

    user = User.objects.filter(telegram_id=message.from_user.id).first()
    if not user:
        await message.answer('Сначала отправьте команду /start.')
        return

    orders = (Order.objects
              .filter(user=user)
              .select_related('table')
              .order_by('-created_at')[:5])

    if not orders:
        await message.answer(
            '📭 У вас пока нет заказов.\n\n'
            'Нажмите кнопку «🍽  Меню» и сделайте свой первый заказ!',
            reply_markup=orders_webapp_inline(user_lang(user)))
        return

    lines = ['📋 <b>Ваши последние заказы</b>\n']
    for o in orders:
        created = timezone.localtime(o.created_at).strftime('%d.%m %H:%M')
        lines.append(
            f'{STATUS_EMOJI.get(o.status, "•")} <b>#{o.order_number}</b>\n'
            f'   🪑 Stol №{o.table.number} · 🕒 {created} · 💰 {o.total:,.0f} so‘m\n'
        )

    await message.answer(
        '\n'.join(lines),
        reply_markup=orders_webapp_inline(user_lang(user)),
        disable_web_page_preview=True,
    )


def user_lang(user) -> str:
    return user.lang or 'uz'
