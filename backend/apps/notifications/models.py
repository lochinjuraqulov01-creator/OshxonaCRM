"""apps/notifications/models.py — yuborilgan bildirishnomalar jurnali."""
from django.db import models

from config.base_model import TimeStampedModel


class NotificationLog(TimeStampedModel):
    TYPE_ORDER_STATUS = 'order_status'
    TYPE_NEW_ORDER = 'new_order'
    TYPE_FEEDBACK = 'feedback'
    TYPE_SYSTEM = 'system'
    TYPE_CHOICES = [
        (TYPE_ORDER_STATUS, 'Статус заказа'),
        (TYPE_NEW_ORDER, 'Новый заказ'),
        (TYPE_FEEDBACK, 'Обратная связь'),
        (TYPE_SYSTEM, 'Система'),
    ]

    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_SYSTEM)
    payload = models.JSONField(default=dict, blank=True)
    is_sent = models.BooleanField(default=False)
    error = models.TextField(blank=True)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
        verbose_name = 'Bildirishnoma'
        verbose_name_plural = 'Bildirishnomalar'

    def __str__(self):
        return f'{self.get_type_display()} — sent:{self.is_sent}'
