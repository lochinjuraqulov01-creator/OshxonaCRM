"""apps/orders/models.py — buyurtma, tarkibi, savat, fikr-mulohaza.

Buyurtma holatlari (talabga mos):
    new        → Yangi (mijoz tasdiqladi, oshxona ko‘rmagan / ko‘rdi)
    preparing  → Tayyorlanmoqda (oshxona qabul qildi)
    in_progress→ Jarayonda (tayyor, stolga yetkazilmoqda)
    delivered  → Yetkazildi (stolga berildi, yakunlangan)
    cancelled  → Bekor qilindi

Indekslar: admin panelning "vaqt bo‘yicha navbat", filtrlar va
statistika so‘rovlarini tezlashtirish uchun qamrovli indekslar qo‘yilgan.
"""
import random
import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from config.base_model import TimeStampedModel


class Order(TimeStampedModel):
    STATUS_NEW = 'new'
    STATUS_PREPARING = 'preparing'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_PREPARING, 'Готовится'),
        (STATUS_IN_PROGRESS, 'В процессе'),
        (STATUS_DELIVERED, 'Доставлен'),
        (STATUS_CANCELLED, 'Отменён'),
    ]

    # WebSocket ga yuboriladigan hodisa nomlari
    WS_EVENT_NEW = 'order_new'
    WS_EVENT_STATUS = 'order_status'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, db_index=True)

    user = models.ForeignKey(
        'users.User', on_delete=models.PROTECT, related_name='orders',
        verbose_name='Клиент')
    table = models.ForeignKey(
        'restaurant.Table', on_delete=models.PROTECT, related_name='orders',
        verbose_name='Стол')

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    items_count = models.PositiveSmallIntegerField(default=0)

    customer_note = models.TextField(blank=True, verbose_name='Комментарий клиента')
    cancel_reason = models.TextField(blank=True)

    # Holat vaqtlari (KPI: tayyorlash tezligi kabi ko‘rsatkichlar uchun)
    accepted_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'orders'
        verbose_name = 'Buyurtma'
        verbose_name_plural = 'Buyurtmalar'
        ordering = ['-created_at']
        indexes = [
            # Admin filtrlari: holat + vaqt oralig‘i
            models.Index(fields=['status', 'created_at']),
            # Stol tarixi
            models.Index(fields=['table', '-created_at']),
            # Mijoz buyurtmalari
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.order_number} — {self.get_status_display()} (Стол №{self.table.number})'

    # ---------------- Yordamchilar ----------------
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        today = timezone.localdate()
        base = f'S{today:%y%m%d}'
        # Kunlik navbat raqami — izchil va tushunarli
        last = (Order.objects
                .filter(order_number__startswith=base)
                .order_by('-order_number').first())
        seq = 1
        if last:
            try:
                seq = int(last.order_number[-4:]) + 1
            except ValueError:
                seq = random.randint(1000, 9999)
        return f'{base}{seq:04d}'

    @property
    def is_active(self):
        return self.status in [self.STATUS_NEW, self.STATUS_PREPARING, self.STATUS_IN_PROGRESS]

    @property
    def prep_minutes(self):
        """Oshxona tayyorlash tezligi (daq.) — KPI hisoblash uchun."""
        if self.accepted_at and self.ready_at:
            return round((self.ready_at - self.accepted_at).total_seconds() / 60, 1)
        return None

    def update_status(self, new_status: str, admin=None, reason: str = ''):
        """Holatni o'zgartiradi, tarix yozadi va WS + Telegram bildirishnoma yuboradi."""
        from .models import OrderStatusHistory
        old = self.status
        if old == new_status:
            return self

        now = timezone.now()
        self.status = new_status
        if new_status == self.STATUS_PREPARING and not self.accepted_at:
            self.accepted_at = now
        elif new_status == self.STATUS_IN_PROGRESS:
            self.ready_at = now
        elif new_status == self.STATUS_DELIVERED:
            self.delivered_at = now
        elif new_status == self.STATUS_CANCELLED:
            self.cancelled_at = now
            self.cancel_reason = reason or self.cancel_reason
        self.save()

        OrderStatusHistory.objects.create(
            order=self, old_status=old, new_status=new_status,
            changed_by=admin, note=reason)

        # Real-time: admin panelga hodisa yuborish
        from .consumers import broadcast_order_event
        broadcast_order_event(
            self.WS_EVENT_STATUS,
            {
                'order_id': str(self.id),
                'order_number': self.order_number,
                'table_number': self.table.number,
                'old_status': old,
                'status': self.status,
                'status_display': self.get_status_display(),
                'total': float(self.total),
                'at': now.isoformat(),
            })

        # Telegram mijozga xabar
        from apps.notifications.services import notify_order_status
        notify_order_status(self)

        return self


class OrderItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='order_items')
    product_name = models.CharField(max_length=200)     # snapshot (mahsulot o‘chsa ham tarix saqlanadi)
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'order_items'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    def save(self, *args, **kwargs):
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class OrderStatusHistory(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='status_changes')
    note = models.TextField(blank=True)

    class Meta:
        db_table = 'order_status_history'
        ordering = ['created_at']


class Cart(TimeStampedModel):
    """Mijoz savati — Mini App ochilgan sessiya davomida saqlanadi."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        'users.User', on_delete=models.CASCADE, related_name='cart')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f'Savat — {self.user}'

    def recalculate(self):
        total = sum(i.total_price for i in self.items.select_related('product'))
        self.total_amount = total
        self.save(update_fields=['total_amount', 'updated_at'])
        return total


class CartItem(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'cart_items'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f'{self.product} × {self.quantity}'

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class Feedback(TimeStampedModel):
    """Mijoz fikr-mulohazasi: baho (1-5) + sharh.  Har bir buyurtma uchun bitta."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='feedback')
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, related_name='feedbacks')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text='1-5')
    comment = models.TextField(blank=True)

    class Meta:
        db_table = 'feedbacks'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.order.order_number} — {"★" * self.rating}'
