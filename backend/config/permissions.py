"""config/permissions.py — maxsus ruxsatlar."""
from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Faqat admin (is_staff=True) foydalanuvchilarga ruxsat."""

    message = 'Faqat administrator uchun ruxsat berilgan.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsTelegramUser(BasePermission):
    """Faqat Telegram orqali ro'yxatdan o'tgan mijozlarga ruxsat."""

    message = 'Bu amal faqat Telegram foydalanuvchilari uchun.'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.telegram_id
            and not request.user.is_staff
        )
