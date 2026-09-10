from django.contrib import admin

from .models import Cart, Feedback, Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'unit_price', 'total_price', 'quantity')


class StatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'changed_by', 'note', 'created_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'table', 'user', 'status',
                    'total', 'items_count', 'created_at')
    list_filter = ('status', 'table', 'created_at')
    search_fields = ('order_number', 'user__username', 'user__telegram_id')
    readonly_fields = ('order_number', 'subtotal', 'service_fee', 'total',
                       'items_count', 'accepted_at', 'ready_at',
                       'delivered_at', 'cancelled_at')
    inlines = [OrderItemInline, StatusHistoryInline]
    date_hierarchy = 'created_at'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('order', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('order__order_number', 'comment')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_amount', 'created_at')
