"""bot/keyboards.py — barcha tugmalar."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)


def main_menu(mini_app_url: str, lang: str = 'uz') -> ReplyKeyboardMarkup:
    """Asosiy menyu — /start dan keyin chiqadi."""
    if lang == 'ru':
        rows = [[KeyboardButton(text='🍽 Меню')],
                [KeyboardButton(text='ℹ️ Помощь')]]
    else:
        rows = [[KeyboardButton(text='🍽 Меню')],
                [KeyboardButton(text='⭐ Оставить отзыв')],
                [KeyboardButton(text='ℹ️ Помощь')]]

    kb = ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

    # "Menyu" tugmasi Mini App ochadi (WebApp tugmasi inline bo'lishi kerak,
    # shuning uchun menu WebApp linkini inline sifatida ham qo'shamiz)
    return kb


def open_menu_inline(mini_app_url: str, lang: str = 'uz') -> InlineKeyboardMarkup:
    """Mini App ni ochadigan tugma."""
    label = '🍽 Меню' if lang == 'ru' else '🍽 Меню'
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, web_app=WebAppInfo(url=mini_app_url))
    ]])


def orders_webapp_inline(mini_app_url: str) -> InlineKeyboardMarkup:
    """Buyurtmalarni Mini App ichida ko'rish."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='📋 Мои заказы', web_app=WebAppInfo(url=mini_app_url))
    ]])


def rating_inline(order_number: str) -> InlineKeyboardMarkup:
    """Baho berish tugmalari (1-5 yulduz)."""
    stars = ['⭐', '⭐⭐', '⭐⭐⭐', '⭐⭐⭐⭐', '⭐⭐⭐⭐⭐']
    rows = [[
        InlineKeyboardButton(
            text=stars[i], callback_data=f'rate:{order_number}:{i + 1}')
    ] for i in range(5)]
    rows.append([InlineKeyboardButton(text='✖️ Отмена', callback_data='rate:cancel:0')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_comment_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text='⏭ Отправить без комментария', callback_data='skip_comment')
    ]])
