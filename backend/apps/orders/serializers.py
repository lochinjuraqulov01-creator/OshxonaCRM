"""apps/orders/serializers.py"""
from django.db import transaction
from rest_framework import serializers

from apps.products.models import Product
from apps.restaurant.models import Table

from .models import Cart, Feedback, Order, OrderItem, OrderStatusHistory


class OrderItemReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity',
                  'unit_price', 'total_price']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source='changed_by.__str__', read_only=True, default='')

    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'old_status', 'new_status', 'changed_by_name', 'note', 'created_at']


class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.__str__', read_only=True, default='')
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    table_number = serializers.IntegerField(source='order.table.number', read_only=True)

    class Meta:
        model = Feedback
        fields = ['id', 'order', 'order_number', 'table_number',
                  'user_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'order', 'user']

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Baho 1 dan 5 gacha bo‘lishi kerak.')
        return value


class OrderReadSerializer(serializers.ModelSerializer):
    items = OrderItemReadSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source='table.number', read_only=True)
    status_display = serializers.CharField(read_only=True)
    feedback = FeedbackSerializer(read_only=True)
    has_feedback = serializers.SerializerMethodField()
    elapsed_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user', 'table_number',
            'status', 'status_display',
            'subtotal', 'service_fee', 'total', 'items_count',
            'customer_note', 'cancel_reason',
            'accepted_at', 'ready_at', 'delivered_at', 'cancelled_at',
            'created_at', 'items', 'feedback', 'has_feedback',
            'elapsed_minutes', 'prep_minutes',
        ]

    def get_has_feedback(self, obj):
        return hasattr(obj, 'feedback')

    def get_elapsed_minutes(self, obj):
        from django.utils import timezone
        end = obj.delivered_at or obj.cancelled_at or timezone.now()
        return round((end - obj.created_at).total_seconds() / 60, 1)


# ================= YARATISH =================

class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Mini App "Buyurtma berish" tugmasi.
    QR skanerlangan stol (number + token) bilan yaratiladi:
      { "table_number": 5, "qr_token": "...", "items": [...], "customer_note": "" }
    """
    table_number = serializers.IntegerField(min_value=1, write_only=True)
    qr_token = serializers.UUIDField(write_only=True)
    items = OrderItemCreateSerializer(many=True, write_only=True, min_length=1)

    class Meta:
        model = Order
        fields = ['table_number', 'qr_token', 'items', 'customer_note']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Buyurtma bo‘sh bo‘lmasligi kerak.')
        return value

    def validate(self, attrs):
        """QR token + stol raqami mosligini tekshirish."""
        table = Table.objects.filter(
            number=attrs['table_number'],
            qr_token=attrs['qr_token'],
            is_active=True).first()
        if not table:
            raise serializers.ValidationError({
                'qr_token': 'QR kod yaroqsiz yoki stol topilmadi.'})
        attrs['table'] = table

        # Mahsulotlarni tekshirish va narxlarini bazadan olish
        products = []
        for item in attrs['items']:
            product = (Product.objects
                       .select_related('category')
                       .filter(id=item['product_id'], is_available=True, is_deleted=False)
                       .first())
            if not product:
                raise serializers.ValidationError({
                    'items': f'Mahsulot topilmadi yoki sotuvda emas: {item["product_id"]}'})
            products.append((product, item['quantity']))
        attrs['_products'] = products
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = self.context['request'].user
        table = validated_data['table']
        note = validated_data.get('customer_note', '')
        service_percent = self._service_percent()

        order = Order(user=user, table=table, customer_note=note)
        subtotal = 0
        items_count = 0
        for product, qty in validated_data['_products']:
            subtotal += product.price * qty
            items_count += qty

        order.subtotal = subtotal
        order.service_fee = (subtotal * service_percent / 100).quantize(
            __import__('decimal').Decimal('0.01'))
        order.total = order.subtotal + order.service_fee
        order.items_count = items_count
        order.save()

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=p,
                product_name=p.name_uz,          # snapshot
                quantity=qty,
                unit_price=p.price,
                total_price=p.price * qty,       # bulk_create save() ni chaqirmaydi
            )
            for p, qty in validated_data['_products']
        ])

        # Mijoz savatini bo'shatish
        Cart.objects.filter(user=user).delete()

        # Real-time admin panelga yangi buyurtma hodisasi
        from .consumers import broadcast_order_event
        broadcast_order_event(
            Order.WS_EVENT_NEW,
            {
                'order_id': str(order.id),
                'order_number': order.order_number,
                'table_number': table.number,
                'status': order.status,
                'status_display': order.get_status_display(),
                'items_count': items_count,
                'total': float(order.total),
                'note': note,
                'created_at': order.created_at.isoformat(),
            })

        # Oshxona/adminiga ogohlantirish (rasmda belgilangan ADMIN_CHAT_ID)
        from apps.notifications.services import notify_new_order
        notify_new_order(order)

        return order

    @staticmethod
    def _service_percent():
        from django.conf import settings
        return getattr(settings, 'SERVICE_PERCENT', 0)


# ================= SAVAT =================

class CartItemAddSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=50)


class CartSerializer(serializers.Serializer):
    """Savat ko'rinishi — Mini App uchun."""
    items = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    items_count = serializers.SerializerMethodField()

    def get_items(self, cart: Cart):
        data = []
        for item in cart.items.select_related('product'):
            data.append({
                'id': str(item.id),
                'product_id': str(item.product_id),
                'name': item.product.name_uz,
                'price': item.unit_price,
                'quantity': item.quantity,
                'total_price': item.total_price,
                'image_url': (self.context.get('request').build_absolute_uri(item.product.image.url)
                              if getattr(item.product, 'image', None) and item.product.image
                              else None),
            })
        return data

    def get_items_count(self, cart: Cart):
        return sum(i.quantity for i in cart.items.all())
