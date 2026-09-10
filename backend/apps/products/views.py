"""apps/products/views.py — menyu API (mijoz) + CRUD (admin)."""
import logging

from django.core.cache import cache
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.pagination import StandardPagination
from config.permissions import IsAdminUser
from django.conf import settings

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    MenuCategorySerializer,
    ProductSerializer,
)

logger = logging.getLogger('apps')


class PublicMenuView(viewsets.ViewSet):
    """
    Mini App uchun ochiq menyu.

    GET /api/products/menu/          → kategoriyalar + mahsulotlar (guruhlangan)
    GET /api/products/menu/?lang=ru  → rus tilida
    Kesh: MENU_CACHE_TTL soniya (optimallashtirish — DB yuklamasi kamayadi).
    """
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'], url_path='menu')
    def menu(self, request):
        lang = request.query_params.get('lang', 'uz')
        if lang not in ('uz', 'ru'):
            lang = 'uz'

        cache_key = f'menu_public_v1_{lang}'
        data = cache.get(cache_key)
        if data is not None:
            return Response({'success': True, 'cached': True, 'categories': data})

        cats = (Category.objects
                .filter(is_active=True, is_deleted=False)
                .prefetch_related(
                    Prefetch(
                        'products',
                        queryset=Product.objects.filter(
                            is_available=True, is_deleted=False),
                    ))
                .order_by('order_num', 'name_uz'))

        data = MenuCategorySerializer(cats, many=True, context={'lang': lang}).data
        cache.set(cache_key, data, settings.MENU_CACHE_TTL)
        return Response({'success': True, 'cached': False, 'categories': data})


class CategoryViewSet(viewsets.ModelViewSet):
    """Admin Panel: kategoriya CRUD."""
    queryset = Category.objects.filter(is_deleted=False)
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        instance.delete()   # soft delete


class ProductViewSet(viewsets.ModelViewSet):
    """Admin Panel: mahsulot CRUD (rasm, nom, narx, izoh)."""
    queryset = (Product.objects
                .filter(is_deleted=False)
                .select_related('category'))
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['category', 'is_available']
    search_fields = ['name_uz', 'name_ru']
    ordering_fields = ['price', 'created_at', 'name_uz']
    pagination_class = StandardPagination
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        instance.delete()   # soft delete
