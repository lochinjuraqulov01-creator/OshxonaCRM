"""apps/users/models.py — maxsus User modeli.

Ikkita turdagi foydalanuvchi:
  • Telegram mijoz  — telegram_id orqali, parolsiz (Mini App initData tekshiruvi)
  • Admin (xodim)   — username/parol orqali (Admin Panel)
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    objects = UserManager()
    
    avatar = models.ImageField(
        upload_to='avatars/', null=True, blank=True,
        verbose_name='Profil rasmi')

    # Telegram ma'lumotlari
    telegram_id = models.BigIntegerField(
        null=True, blank=True, unique=True, db_index=True,
        verbose_name='Telegram ID')
    telegram_username = models.CharField(
        max_length=64, blank=True, verbose_name='Telegram username')
    telegram_photo_url = models.URLField(blank=True)

    # Umumiy
    phone = models.CharField(max_length=20, blank=True)
    LANG_UZ = 'uz'
    LANG_RU = 'ru'
    LANG_CHOICES = [(LANG_UZ, 'O‘zbekcha'), (LANG_RU, 'Русский')]
    lang = models.CharField(
        max_length=2, choices=LANG_CHOICES, default=LANG_UZ,
        verbose_name='Til')
    is_registered = models.BooleanField(
        default=False, verbose_name='Ro‘yxatdan o‘tgan',
        help_text='Telegram orqali /start yuborgan mijozlar')

    class Meta:
        db_table = 'users'
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['is_registered', 'is_staff']),
        ]

    def __str__(self):
        if self.telegram_id:
            return f'TG:{self.first_name or self.telegram_username or self.telegram_id}'
        return self.username or f'User#{self.pk}'

    @property
    def is_telegram_user(self):
        return bool(self.telegram_id)

    @classmethod
    def get_or_create_telegram_user(cls, tg_user: dict) -> 'User':
        """Telegram foydalanuvchini topadi yoki yaratadi (bot/miniapp uchun)."""
        tg_id = tg_user.get('id')
        user, created = cls.objects.get_or_create(
            telegram_id=tg_id,
            defaults={
                'username': f'tg_{tg_id}',
                'first_name': tg_user.get('first_name', '') or '',
                'last_name': tg_user.get('last_name', '') or '',
                'telegram_username': tg_user.get('username', '') or '',
                'telegram_photo_url': tg_user.get('photo_url', '') or '',
                'lang': tg_user.get('language_code', 'uz')[:2] or 'uz',
                'is_registered': True,
            },
        )
        if not created:
            # Ma'lumotlarni yangilab boramiz
            changed = []
            if tg_user.get('first_name') and user.first_name != tg_user['first_name']:
                user.first_name = tg_user['first_name']; changed.append('first_name')
            if tg_user.get('username') and user.telegram_username != tg_user['username']:
                user.telegram_username = tg_user['username']; changed.append('telegram_username')
            if not user.is_registered:
                user.is_registered = True; changed.append('is_registered')
            if changed:
                user.save(update_fields=changed + ['last_login'])
        return user
