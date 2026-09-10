"""apps/restaurant/models.py — stol modeli va QR tokeni.

Har bir stolda unikal QR kod bor:
  QR mazmuni: SMARTOX:TABLE:<raqam>:<qr_token>
Mijoz Mini App ichida QR skanerlaydi → tizim stolni aniqlaydi →
buyurtma shu stol raqami bilan oshxonaga yuboriladi.
"""
import uuid

from django.conf import settings
from django.db import models

from config.base_model import TimeStampedModel


class Table(TimeStampedModel):
    """Oshxona stoli — QR kod bilan bog'langan."""

    number = models.PositiveSmallIntegerField(
        unique=True, verbose_name='Stol raqami')
    name = models.CharField(
        max_length=50, blank=True, verbose_name='Nom (zall/zona)',
        help_text='Masalan: "Zal 1", "Terasa"')
    seats = models.PositiveSmallIntegerField(
        default=4, verbose_name='O‘rindiqlar soni')
    qr_token = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
        verbose_name='QR token')
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name='Faol')
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'tables'
        verbose_name = 'Stol'
        verbose_name_plural = 'Stollar'
        ordering = ['number']

    def __str__(self):
        return f'Stol #{self.number}'

    # ---------------- QR ----------------
    @property
    def qr_content(self) -> str:
        """QR kodga yoziladigan matn."""
        return f'{settings.QR_CONTENT_PREFIX}{self.number}:{self.qr_token}'

    def regenerate_qr(self):
        """QR tokenni yangilash (eski QR kodlar ishlamay qoladi)."""
        self.qr_token = uuid.uuid4()
        self.save(update_fields=['qr_token', 'updated_at'])
        return self.qr_token

    # ---------------- Holat ----------------
    @property
    def active_orders(self):
        return self.orders.filter(
            status__in=['new', 'preparing', 'in_progress'])

    @property
    def is_busy(self) -> bool:
        return self.active_orders.exists()

    @property
    def status_display(self) -> str:
        return 'Band' if self.is_busy else 'Bo‘sh'
