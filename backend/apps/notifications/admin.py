from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('type', 'user', 'order', 'is_sent', 'created_at')
    list_filter = ('type', 'is_sent')
    readonly_fields = ('payload', 'error')
