"""bot/handlers/feedback.py — fikr-mulohaza oqimi (FSM).

Oqim: «Fikr bildirish» → yetkazilgan buyurtmalarni tanlatish
      → baho (inline 1-5) → izoh (matn yoki o'tkazib yuborish) → saqlash.
"""
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger('bot')
router = Router()


class FeedbackStates(StatesGroup):
    waiting_comment = State()


@router.message(F.text.in_({'⭐ Fikr bildirish', '⭐ Оставить отзыв'}))
async def btn_feedback(message: Message, state: FSMContext):
    from apps.orders.models import Order
    from apps.users.models import User

    user = User.objects.filter(telegram_id=message.from_user.id).first()
    if not user:
        await message.answer('Сначала отправьте команду /start.')
        return

    delivered = (Order.objects
                 .filter(user=user, status=Order.STATUS_DELIVERED)
                 .exclude(feedback__isnull=False)
                 .select_related('table')
                 .order_by('-delivered_at')[:5])

    if not delivered:
        await message.answer(
            '📭 Не найдено доставленных заказов для отзыва.\n\n'
            'Сделайте заказ — после того, как мы его доставим, вы сможете оценить его! 😊')
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    from django.utils import timezone

    lines = ['⭐ <b>Какой заказ вы хотите оценить?</b>\n']
    kb_rows = []
    for o in delivered:
        t = timezone.localtime(o.delivered_at or o.created_at).strftime('%d.%m %H:%M')
        lines.append(f'• #{o.order_number} — Стол №{o.table.number} — {t}')
        kb_rows.append([InlineKeyboardButton(
            text=f'#{o.order_number} (Стол №{o.table.number})',
            callback_data=f'fbselect:{o.order_number}')])

    await state.update_data(order_ids=[o.order_number for o in delivered])
    await message.answer('\n'.join(lines),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith('fbselect:'))
async def cb_select_order(cb: CallbackQuery, state: FSMContext):
    order_number = cb.data.split(':', 1)[1]
    await state.update_data(order_number=order_number)
    from bot.keyboards import rating_inline
    await cb.message.answer(
        f'⭐ <b>#{order_number}</b> oцените заказ:',
        reply_markup=rating_inline(order_number))
    await cb.answer()


@router.callback_query(F.data.startswith('rate:'))
async def cb_rate(cb: CallbackQuery, state: FSMContext):
    """Baho tanlandi → izoh so'raymiz."""
    _, order_number, rating = cb.data.split(':')

    if order_number == 'cancel':
        await state.clear()
        await cb.message.edit_text('Отменён.')
        await cb.answer()
        return

    await state.update_data(order_number=order_number, rating=int(rating))
    stars = '⭐' * int(rating)
    await cb.message.edit_text(
        f'{stars}\n\n📝 Напишите комментарий к заказу (отправьте текст).\n'
        'Или нажмите кнопку «Отправить без комментария».')
    from bot.keyboards import skip_comment_inline
    await cb.message.answer('Напишете отзыв?', reply_markup=skip_comment_inline())
    await state.set_state(FeedbackStates.waiting_comment)
    await cb.answer()


@router.callback_query(F.data == 'skip_comment', FeedbackStates.waiting_comment)
async def cb_skip_comment(cb: CallbackQuery, state: FSMContext):
    await _save_feedback(cb, state, comment='')


@router.message(FeedbackStates.waiting_comment, F.text)
async def on_comment(message: Message, state: FSMContext):
    await _save_feedback(message, state, comment=message.text[:1000])


async def _save_feedback(obj: Message | CallbackQuery, state: FSMContext, comment: str):
    data = await state.get_data()
    order_number = data.get('order_number')
    rating = data.get('rating')

    from apps.orders.models import Feedback, Order
    order = Order.objects.filter(order_number=order_number).first()
    if not order:
        await state.clear()
        text = 'Заказ не найден.'
        if isinstance(obj, CallbackQuery):
            await obj.message.answer(text)
            await obj.answer()
        else:
            await obj.answer(text)
        return

    Feedback.objects.get_or_create(
        order=order,
        defaults={'user': order.user, 'rating': rating, 'comment': comment})

    await state.clear()
    text = ('🙏 <b>Спасибо за ваш отзыв!</b>\n\n'
            f'Заказ #{order.order_number} — {"⭐" * rating}\n'
            + (f'📝 Комментарий: {comment}' if comment else ''))
    if isinstance(obj, CallbackQuery):
        await obj.message.answer(text)
        await obj.answer('Сохранено!')
    else:
        await obj.answer(text)


@router.callback_query(F.data.startswith('rate:'))
async def cb_rate_fallback(cb: CallbackQuery):
    """Agar state ulanmasa — hech bo'lmaganda tugma "bosildi" bo'lsin."""
    await cb.answer()
