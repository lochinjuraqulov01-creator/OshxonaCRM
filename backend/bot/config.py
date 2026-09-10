"""bot/config.py — bot sozlamalari (.env dan o'qiydi)."""
import os

from decouple import config

# Django sozlamalarini ulash (ORM ishlashi uchun)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
MINI_APP_URL = config('MINI_APP_URL', default='')
ADMIN_PANEL_URL = config('ADMIN_PANEL_URL', default='')
RESTAURANT_NAME = config('RESTAURANT_NAME', default='Kuro Tokyo')
