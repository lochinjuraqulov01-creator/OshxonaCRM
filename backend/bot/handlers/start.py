"""bot/handlers/start.py — /start va asosiy menyu."""
import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_PANEL_URL, MINI_APP_URL, RESTAURANT_NAME
from bot.keyboards import main_menu, open_menu_inline

logger = logging.getLogger('bot')
router = Router()

WELCOME_TEXT = (
    '👋 <b>Assalomu alaykum, {name}!</b>\n\n'
    f'Добро пожаловать в ресторан «{RESTAURANT_NAME}»! 🍽\n\n'
    'С помощью этого бота вы можете:\n'
    '• 🍽 <b>Меню</b> — просматривать блюда и делать заказы\n'
    '• 📋 <b>Мои заказы</b> — отслеживать их статус\n'
    '• ⭐ <b>Оставить отзыв</b> — поставить оценку и написать комментарий\n\n'
    '🪑 <b>Когда сядете за стол</b>: Откройте меню → выберите блюдо → '
    'добавьте в корзину → нажмите «Оформить заказ» → отсканируйте QR-код на столе → подтвердите.\n\n'
    'Ваш заказ будет отправлен на кухню с номером вашего стола. Приятного аппетита! 😊'
)

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Mijoz /start yozadi → ro'yxatdan o'tadi → asosiy menyu chiqadi."""
    from apps.users.models import User

    tg = message.from_user
    user = User.get_or_create_telegram_user({
        'id': tg.id,
        'first_name': tg.first_name,
        'last_name': tg.last_name,
        'username': tg.username,
        'language_code': tg.language_code,
    })

    lang = 'ru' if (tg.language_code or '').startswith('ru') else 'uz'
    user.lang = lang
    user.save(update_fields=['lang'])

    await message.answer(
        WELCOME_TEXT.format(name=tg.first_name or ''),
        reply_markup=main_menu(MINI_APP_URL, lang),
        disable_web_page_preview=True,
    )
    # Menyu tugmasini (WebApp) alohida inline qilib yuboramiz
    await message.answer(
        'Нажмите кнопку «🍽 Меню» внизу — откроется Mini App 👇',
        reply_markup=open_menu_inline(MINI_APP_URL, lang),
    )


@router.message(F.text.in_({'🍽 Меню', '🍽 Меню'}))
async def btn_menu(message: Message):
    """«Menyu» tugmasi → Mini App ochiladi."""
    await message.answer('✨ Mini App открывается...', reply_markup=open_menu_inline(MINI_APP_URL))


@router.message(F.text.in_({'ℹ️ Yordam', 'ℹ️ Помощь'}))
async def btn_help(message: Message):
    from apps.restaurant.models import Table
    tables_count = Table.objects.filter(is_active=True).count()
    await message.answer(
        'ℹ️ <b>Помощь</b>\n\n'
        '1️⃣ Сядьте за стол — на столе есть QR-код\n'
        '2️⃣ Кнопка «🍽 Меню» → откроется Mini App\n'
        '3️⃣ Выберите блюдо, добавьте в корзину\n'
        '4️⃣ Нажмите «Оформить заказ» → отсканируйте QR-код\n'
        '5️⃣ Подтвердите — заказ отправится на кухню с номером вашего стола\n'
        '6️⃣ Когда будет готово, бот уведомит вас 🔔\n\n'
        f'🏪 Наша кухня: <b>{RESTAURANT_NAME}</b>\n'
        f'🪑 Активных столов: <b>{tables_count}</b>\n\n'

    )


@router.callback_query(F.data == 'noop')
async def cb_noop(cb: CallbackQuery):
    await cb.answer()
