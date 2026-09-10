"""apps/orders/views.py — buyurtma API.

Mijoz (Mini App, Telegram JWT):
  GET  /api/orders/orders/                → o'z buyurtmalari
  POST /api/orders/orders/                → yangi buyurtma (QR + items)
  GET  /api/orders/orders/<id>/           → batafsil
  POST /api/orders/orders/<id>/cancel/    → yangi buyurtmani bekor qilish
  POST /api/orders/orders/<id>/feedback/  → baho + sharh
  GET  /api/orders/cart/                  → savat
  POST /api/orders/cart/add/              → savatga qo'shish
  PATCH /api/orders/cart/items/<id>/      → miqdorni o'zgartirish
  DELETE /api/orders/cart/items/<id>/     → o'chirish
  POST /api/orders/cart/clear/            → tozalash

Admin (Admin Panel, JWT):
  GET  /api/orders/admin-orders/          → ro'yxat (filterlar: status, vaqt, stol)
  GET  /api/orders/admin-orders/<id>/
  POST /api/orders/admin-orders/<id>/status/ → holat o'zgartirish
  GET  /api/orders/admin-orders/table-history/?table_id=  → stollar tarixi
"""
import logging

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import SmartOshxonaAPIException
from config.pagination import StandardPagination
from config.permissions import IsAdminUser

from .models import Cart, CartItem, Feedback, Order
from .serializers import (
    CartSerializer,
    FeedbackSerializer,
    OrderCreateSerializer,
    OrderReadSerializer,
    OrderStatusHistorySerializer,
)

logger = logging.getLogger('apps')


# ============================================================
#  MIJOZ TOMONI
# ============================================================

class CustomerOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Mini App uchun buyurtmalar."""
    serializer_class = OrderReadSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'action', None) == 'create_order':
            return Order.objects.all()
        return (Order.objects
                .filter(user=self.request.user)
                .select_related('table', 'user')
                .prefetch_related('items', 'feedback'))

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        status_f = request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page, many=True)
        return self.get_paginated_response(ser.data)

    def retrieve(self, request, *args, **kwargs):
        """Bitta buyurtma — success sarguzasht bilan."""
        order = self.get_object()
        data = self.get_serializer(order, context={'request': request}).data
        return Response({'success': True, **data})

    def create(self, request, *args, **kwargs):
        """POST /api/orders/orders/ — QR orqali buyurtma yaratish."""
        ser = OrderCreateSerializer(data=request.data, context={'request': request})
        ser.is_valid(raise_exception=True)
        order = ser.save()
        out = OrderReadSerializer(order, context={'request': request})
        return Response({'success': True, 'message': 'Buyurtmangiz oshxonaga yuborildi!',
                         'order': out.data})

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Mijoz faqat yangi (oshxona qabul qilmagan) buyurtmani bekor qilishi mumkin."""
        order = self.get_object()
        if order.status != Order.STATUS_NEW:
            raise SmartOshxonaAPIException(
                'Bu buyurtma allaqachon oshxonada — bekor qilib bo‘lmaydi.',
                code='cancel_not_allowed', status_code=400)
        order.update_status(Order.STATUS_CANCELLED, reason='Mijoz bekor qildi')
        return Response({'success': True, 'message': 'Buyurtma bekor qilindi.'})

    @action(detail=True, methods=['post'], url_path='feedback')
    def feedback(self, request, pk=None):
        """Baho (1-5) + sharh.  Faqat yetkazilgan buyurtma uchun."""
        order = self.get_object()
        if order.status != Order.STATUS_DELIVERED:
            raise SmartOshxonaAPIException(
                'Fikr bildirish uchun buyurtma yetkazilgan bo‘lishi kerak.',
                code='feedback_not_allowed', status_code=400)
        if hasattr(order, 'feedback'):
            raise SmartOshxonaAPIException(
                'Bu buyurtma uchun fikr allaqachon qoldirilgan.',
                code='feedback_exists', status_code=400)

        ser = FeedbackSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        feedback = Feedback.objects.create(
            order=order, user=request.user,
            rating=ser.validated_data['rating'],
            comment=ser.validated_data.get('comment', ''))
        return Response({'success': True, 'message': 'Fikringiz uchun rahmat!',
                         'feedback': FeedbackSerializer(feedback).data})


# ============================================================
#  ADMIN TOMONI
# ============================================================

class AdminOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin Panel: barcha buyurtmalar ro'yxati + boshqaruv."""
    serializer_class = OrderReadSerializer
    permission_classes = [IsAdminUser]
    pagination_class = StandardPagination
    filterset_fields = ['status', 'table']
    ordering_fields = ['created_at', 'total']
    http_method_names = ['get', 'post', 'head', 'options']

    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()
        data = self.get_serializer(order, context={'request': request}).data
        return Response({'success': True, **data})

    def get_queryset(self):
        qs = (Order.objects
              .select_related('table', 'user')
              .prefetch_related('items', 'feedback', 'status_history'))

        params = self.request.query_params
        # Vaqt oralig'i filtri
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        if date_from:
            try:
                qs = qs.filter(created_at__date__gte=date_from)
            except Exception:
                pass
        if date_to:
            try:
                qs = qs.filter(created_at__date__lte=date_to)
            except Exception:
                pass
        # Qidiruv: buyurtma raqami / stol
        search = params.get('search')
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(table__number__iexact=search))
        return qs

    @action(detail=True, methods=['post'], url_path='status')
    def change_status(self, request, pk=None):
        """Holat o'zgartirish: preparing / in_progress / delivered / cancelled."""
        order = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        allowed = {Order.STATUS_PREPARING, Order.STATUS_IN_PROGRESS,
                   Order.STATUS_DELIVERED, Order.STATUS_CANCELLED}
        if new_status not in allowed:
            raise SmartOshxonaAPIException(
                f'Holat quyidagilardan biri bo‘lishi kerak: {", ".join(sorted(allowed))}',
                code='bad_status', status_code=400)
        if order.status == Order.STATUS_DELIVERED:
            raise SmartOshxonaAPIException(
                'Yetkazilgan buyurtmani o‘zgartirib bo‘lmaydi.',
                code='final_status', status_code=400)

        order.update_status(new_status, admin=request.user, reason=reason)
        out = OrderReadSerializer(order, context={'request': request})
        return Response({'success': True, 'message': 'Holat yangilandi.',
                         'order': out.data})

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """Buyurtma holatlari tarixi."""
        order = self.get_object()
        data = OrderStatusHistorySerializer(order.status_history.all(), many=True).data
        return Response({'success': True, 'results': data})

    @action(detail=False, methods=['get'], url_path='table-history')
    def table_history(self, request):
        """Bir stolning barcha buyurtmalari tarixi: ?table_id=...&days=30"""
        table_id = request.query_params.get('table_id')
        days = request.query_params.get('days', 30)
        if not table_id:
            raise SmartOshxonaAPIException('table_id talab qilinadi.',
                                           code='param_missing', status_code=400)
        since = timezone.now() - timezone.timedelta(days=int(days))
        qs = (self.get_queryset()
              .filter(table_id=table_id, created_at__gte=since))
        agg = qs.aggregate(revenue=Sum('total'), orders=Count('id'))
        page = self.paginate_queryset(qs)
        ser = OrderReadSerializer(page, many=True, context={'request': request})
        resp = self.get_paginated_response(ser.data)
        resp.data['summary'] = {
            'orders': agg['orders'] or 0,
            'revenue': float(agg['revenue'] or 0),
        }
        return resp

    @action(detail=False, methods=['get'], url_path='live')
    def live(self, request):
        """Faol buyurtmalar (new/preparing/in_progress) — navbat ko'rinishi."""
        qs = (self.get_queryset()
              .filter(status__in=[Order.STATUS_NEW, Order.STATUS_PREPARING,
                                  Order.STATUS_IN_PROGRESS])
              .order_by('created_at'))       # vaqt bo'yicha navbat
        ser = self.get_serializer(qs, many=True)
        return Response({'success': True, 'count': qs.count(), 'results': ser.data})


# ============================================================
#  SAVAT
# ============================================================

def _get_cart(user) -> Cart:
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = _get_cart(request.user)
        cart.recalculate()
        data = CartSerializer(cart, context={'request': request}).data
        return Response({'success': True, 'cart': data})


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from rest_framework import serializers as rf_serializers

        class _Ser(rf_serializers.Serializer):
            product_id = rf_serializers.UUIDField()
            quantity = rf_serializers.IntegerField(min_value=1, max_value=50)

        ser = _Ser(data=request.data)
        ser.is_valid(raise_exception=True)
        pid = ser.validated_data['product_id']
        qty = ser.validated_data['quantity']

        from apps.products.models import Product
        product = Product.objects.filter(id=pid, is_available=True, is_deleted=False).first()
        if not product:
            raise SmartOshxonaAPIException('Mahsulot topilmadi yoki sotuvda emas.',
                                           code='product_missing', status_code=400)

        cart = _get_cart(request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': qty, 'unit_price': product.price})
        if not created:
            item.quantity = min(item.quantity + qty, 50)
            item.save(update_fields=['quantity', 'updated_at'])
        cart.recalculate()

        data = CartSerializer(cart, context={'request': request}).data
        return Response({'success': True, 'message': 'Добавлено в корзину.', 'cart': data})


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        cart = _get_cart(request.user)
        item = cart.items.filter(id=item_id).first()
        if not item:
            raise SmartOshxonaAPIException('Savat elementi topilmadi.',
                                           code='not_found', status_code=404)
        qty = request.data.get('quantity')
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            raise SmartOshxonaAPIException('quantity butun son bo‘lishi kerak.',
                                           code='bad_qty', status_code=400)
        if qty < 1 or qty > 50:
            raise SmartOshxonaAPIException('quantity 1..50 oralig‘ida bo‘lsin.',
                                           code='bad_qty', status_code=400)
        item.quantity = qty
        item.save(update_fields=['quantity', 'updated_at'])
        cart.recalculate()
        data = CartSerializer(cart, context={'request': request}).data
        return Response({'success': True, 'cart': data})

    def delete(self, request, item_id):
        cart = _get_cart(request.user)
        item = cart.items.filter(id=item_id).first()
        if not item:
            raise SmartOshxonaAPIException('Savat elementi topilmadi.',
                                           code='not_found', status_code=404)
        item.delete()
        cart.recalculate()
        data = CartSerializer(cart, context={'request': request}).data
        return Response({'success': True, 'message': 'O‘chirildi.', 'cart': data})


class CartClearView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Cart.objects.filter(user=request.user).delete()
        return Response({'success': True, 'message': 'Savat bo‘shatildi.',
                         'cart': {'items': [], 'total_amount': 0, 'items_count': 0}})
