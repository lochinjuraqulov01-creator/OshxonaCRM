"""apps/users — foydalanuvchilar (Telegram mijozlar + adminlar)."""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'
    verbose_name = 'Foydalanuvchilar'
