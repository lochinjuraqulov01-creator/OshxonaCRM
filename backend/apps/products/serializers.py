"""apps/products/serializers.py"""
from rest_framework import serializers

from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order_num']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.get_name', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name',
            'name_uz', 'name_ru', 'description_uz', 'description_ru',
            'price', 'image', 'image_url', 'is_available', 'order_num',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        # Rasm bo'lmasa — boshlang'ich placeholder (emoji icon front tomonda)
        return None


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name_uz', 'name_ru', 'icon', 'order_num',
            'is_active', 'products_count',
        ]
        read_only_fields = ['id']

    def get_products_count(self, obj):
        return obj.products.filter(is_deleted=False).count()


# ---------- Mijoz (Mini App) uchun yengil serializerlar ----------

class MenuProductSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'image_url', 'is_available']

    def get_name(self, obj):
        lang = self.context.get('lang', 'uz')
        return obj.get_name(lang)

    def get_description(self, obj):
        lang = self.context.get('lang', 'uz')
        return obj.get_description(lang)

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class MenuCategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'products']

    def get_name(self, obj):
        lang = self.context.get('lang', 'uz')
        return obj.get_name(lang)

    def get_products(self, obj):
        qs = obj.products.filter(is_deleted=False, is_available=True)
        ser = MenuProductSerializer(
            qs, many=True, context={**self.context})
        return ser.data
