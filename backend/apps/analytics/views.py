"""apps/analytics/views.py — statistika endpointlari (talab 5-band).

GET /api/stats/today/    → kunlik daromad + buyurtmalar + TOP mahsulot + sotilmaganlar
GET /api/stats/admin/    → keng qamrovli hisobot (grafiklar uchun)

Kesh: STATS_CACHE_TTL (1 daqiqa) — statistikani tez-tez so'raydi-ku,
DB yuklamasini kamaytirish uchun keshdan foydalanamiz.
"""
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Feedback, Order, OrderItem
from apps.products.models import Product
from config.permissions import IsAdminUser

logger = logging.getLogger('apps')


def _day_start():
    now = timezone.localtime()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class TodayStatsView(APIView):
    """Bugungi tezkor statistika — Admin panel dashboard kartochkalari."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        cache_key = 'stats_today_v1'
        data = cache.get(cache_key)
        if data:
            return Response({'success': True, 'cached': True, **data})

        start = _day_start()
        today_orders = Order.objects.filter(created_at__gte=start)
        delivered = today_orders.filter(status=Order.STATUS_DELIVERED)

        revenue = delivered.aggregate(s=Sum('total'))['s'] or 0
        orders_count = today_orders.count()
        guests = (today_orders.values('user').distinct().count())
        avg_check = delivered.aggregate(a=Avg('total'))['a'] or 0

        # Bugungi eng ko'p sotilgan mahsulot
        top = (OrderItem.objects
               .filter(order__created_at__gte=start)
               .exclude(order__status=Order.STATUS_CANCELLED)
               .values('product_id', 'product_name')
               .annotate(qty=Sum('quantity'), revenue=Sum('total_price'))
               .order_by('-qty')[:5])

        # Bugungi sotilmagan mahsulotlar (menyuda bor, lekin hech kim olmagan)
        sold_ids = (OrderItem.objects.filter(order__created_at__gte=start)
                    .values_list('product_id', flat=True).distinct())
        unsold = (Product.objects
                  .filter(is_deleted=False, is_available=True)
                  .exclude(id__in=sold_ids)
                  .values('id', 'name_uz', 'price')[:50])

        # Holatlar taqsimoti
        by_status = today_orders.values('status').annotate(count=Count('id'))

        data = {
            'revenue': float(revenue),
            'orders_count': orders_count,
            'active_orders': today_orders.filter(
                status__in=['new', 'preparing', 'in_progress']).count(),
            'avg_check': round(float(avg_check), 2),
            'unique_guests': guests,
            'top_products': [
                {'id': str(t['product_id']), 'name': t['product_name'],
                 'qty': t['qty'], 'revenue': float(t['revenue'] or 0)} for t in top],
            'unsold_products': [
                {'id': str(u['id']), 'name': u['name_uz'],
                 'price': float(u['price'])} for u in unsold],
            'status_distribution': [
                {'status': s['status'], 'count': s['count']} for s in by_status],
        }
        from django.conf import settings
        cache.set(cache_key, data, settings.STATS_CACHE_TTL)
        return Response({'success': True, 'cached': False, **data})


class AdminStatsView(APIView):
    """
    Keng qamrovli hisobot — grafiklar va talab tahlili.
    ?period=today|week|month&days=7
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        days = int(request.query_params.get('days', 7))
        days = min(max(days, 1), 90)
        cache_key = f'stats_admin_v1_{days}'
        data = cache.get(cache_key)
        if data:
            return Response({'success': True, 'cached': True, **data})

        start = _day_start() - timedelta(days=days - 1)
        start_utc = start

        orders = Order.objects.filter(created_at__gte=start_utc)
        delivered = orders.filter(status=Order.STATUS_DELIVERED)

        # ---------- Kunlik daromad trendi ----------
        trend = (delivered
                 .annotate(day=TruncDate('created_at'))
                 .values('day')
                 .annotate(revenue=Sum('total'), orders=Count('id'))
                 .order_by('day'))

        # ---------- Mahsulotlar talab darajasi ----------
        # Har bir mahsulotning sotilgan miqdori → ulush % → High/Medium/Low
        item_stats = (OrderItem.objects
                      .filter(order__created_at__gte=start_utc)
                      .exclude(order__status=Order.STATUS_CANCELLED)
                      .values('product_id', 'product_name')
                      .annotate(qty=Sum('quantity'), revenue=Sum('total_price')))

        total_qty = sum(i['qty'] for i in item_stats) or 1
        demand = []
        for i in item_stats:
            share = i['qty'] / total_qty * 100
            if share >= 10:
                level, color = 'Высокий', 'high'
            elif share >= 4:
                level, color = 'Средний', 'medium'
            else:
                level, color = 'Низкий', 'low'
            demand.append({
                'id': str(i['product_id']),
                'name': i['product_name'],
                'qty': i['qty'],
                'revenue': float(i['revenue'] or 0),
                'share': round(share, 2),
                'level': level, 'color': color,
            })
        demand.sort(key=lambda x: -x['qty'])

        # Sotilmaganlar (davr ichida umuman sotilmagan)
        sold_ids = (OrderItem.objects.filter(order__created_at__gte=start_utc)
                    .values_list('product_id', flat=True).distinct())
        never_sold = (Product.objects
                      .filter(is_deleted=False)
                      .exclude(id__in=sold_ids)
                      .values('id', 'name_uz', 'price')[:50])

        # ---------- Holatlar taqsimoti ----------
        status_dist = (orders.values('status').annotate(count=Count('id')))

        # ---------- Stollar bo'yicha tushum ----------
        table_rev = (delivered
                     .values('table__number')
                     .annotate(revenue=Sum('total'), orders=Count('id'))
                     .order_by('-revenue')[:10])

        # ---------- O'rtacha ko'rsatkichlar (KPI) ----------
        prep = [o.prep_minutes for o in delivered if o.prep_minutes is not None]
        avg_prep = round(sum(prep) / len(prep), 1) if prep else None

        # ---------- Feedback reytingi ----------
        fb = (Feedback.objects
              .filter(created_at__gte=start_utc)
              .aggregate(avg_rating=Avg('rating'), count=Count('id')))

        data = {
            'days': days,
            'kpi': {
                'revenue': float(delivered.aggregate(s=Sum('total'))['s'] or 0),
                'orders': orders.count(),
                'delivered': delivered.count(),
                'cancelled': orders.filter(status=Order.STATUS_CANCELLED).count(),
                'avg_check': round(float(delivered.aggregate(a=Avg('total'))['a'] or 0), 2),
                'avg_prep_minutes': avg_prep,
                'avg_rating': round(float(fb['avg_rating'] or 0), 2),
                'feedback_count': fb['count'],
            },
            'trend': [
                {'date': str(t['day']), 'revenue': float(t['revenue'] or 0),
                 'orders': t['orders']} for t in trend],
            'demand': demand[:20],
            'never_sold': [
                {'id': str(p['id']), 'name': p['name_uz'], 'price': float(p['price'])}
                for p in never_sold],
            'status_distribution': list(status_dist),
            'table_revenue': [
                {'table': t['table__number'], 'revenue': float(t['revenue'] or 0),
                 'orders': t['orders']} for t in table_rev],
        }
        from django.conf import settings
        cache.set(cache_key, data, settings.STATS_CACHE_TTL)
        return Response({'success': True, 'cached': False, **data})
