"""
bot/main.py — SmartOshxona Telegram bot (aiogram 3.x).

Ishga tushirish (backend/ papkasidan):
    python -m bot.main

Bot polling rejimida ishlaydi (webhook sozlash talab qilmaydi).
Kiruvchi xabarlarga javob beradi; CHIQUVCHI bildirishnomalarni
esa Django (apps/notifications/services.py) yuboradi.
"""
import asyncio
import logging
import sys

# Windows konsoli UTF-8 emas (cp1251) → emoji loglar UnicodeEncodeError beradi.
# Shuning oldini olish uchun chiqish oqimlarini UTF-8 ga o'tkazamiz.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import BOT_TOKEN
from bot.handlers import feedback, orders, start

logger = logging.getLogger('bot')

# Django ORM ni yoqish
from bot import django_setup  # noqa: E402, F401


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(asctime)s:%(name)s:%(message)s')

    if not BOT_TOKEN:
        logger.critical(
            'TELEGRAM_BOT_TOKEN не настроен! Укажите токен в файле .env.')
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(orders.router)
    dp.include_router(feedback.router)

    logger.info('🤖 Бот Kuro Tokyo запущен (поллинг)...')
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Бот остановлен.')
