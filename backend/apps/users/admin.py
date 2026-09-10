from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'first_name', 'telegram_id',
                    'telegram_username', 'lang', 'is_registered', 'is_staff')
    list_filter = ('is_staff', 'is_registered', 'lang')
    search_fields = ('username', 'first_name', 'telegram_id', 'telegram_username')
    fieldsets = UserAdmin.fieldsets + (
        ('Telegram', {'fields': ('telegram_id', 'telegram_username', 'telegram_photo_url')}),
        ('Qo‘shimcha', {'fields': ('phone', 'lang', 'is_registered')}),
    )
