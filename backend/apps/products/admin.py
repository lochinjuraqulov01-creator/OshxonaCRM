from django.contrib import admin

from .models import Category, PriceHistory, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'name_ru', 'icon', 'order_num', 'is_active')
    list_editable = ('order_num', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name_uz', 'category', 'price', 'is_available', 'order_num')
    list_filter = ('category', 'is_available')
    search_fields = ('name_uz', 'name_ru')
    list_editable = ('is_available', 'order_num')
    inlines = [ProductImageInline]


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'old_price', 'new_price', 'created_at')
    list_filter = ('product',)
