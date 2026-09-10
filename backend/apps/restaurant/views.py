"""apps/restaurant/views.py — stol CRUD + QR generatsiya + validatsiya."""
import logging

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.exceptions import SmartOshxonaAPIException
from config.permissions import IsAdminUser
from apps.users.authentication import JWTQueryParamAuthentication

from .models import Table
from .serializers import TableSerializer, TableValidateSerializer
from .services import make_qr_png

logger = logging.getLogger('apps')


class TableViewSet(viewsets.ModelViewSet):
    """Admin Panel uchun stollar CRUD + QR amallari."""
    queryset = Table.objects.all().order_by('number')
    serializer_class = TableSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ['is_active']
    search_fields = ['number', 'name']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        """Stolni o'chirish — agar band bo'lsa taqiqlanadi."""
        table = self.get_object()
        if table.is_busy:
            raise SmartOshxonaAPIException(
                'Bu stolda hozir faol buyurtma bor — avval buyurtmalarni yopish kerak.',
                code='table_busy', status_code=400)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'], url_path='qr',
            authentication_classes=[JWTQueryParamAuthentication])
    def qr(self, request, pk=None):
        """Stol QR kodini PNG qilib qaytaradi.

        ?label=1     → stol raqami yozilgan plakat
        ?download=1  → yuklab olish rejimi (attachment)
        ?token=JWT   → <img>/<a download> teglari sarlavha yubora olmaydi,
                       shuning uchun JWT query param orqali ham qabul qilinadi
        """
        table = self.get_object()
        with_label = request.query_params.get('label')
        label = f'STOL №{table.number}' if with_label else None
        buf = make_qr_png(table.qr_content, size=512, with_label=label)
        if request.query_params.get('download'):
            resp = HttpResponse(buf.getvalue(), content_type='image/png')
            resp['Content-Disposition'] = f'attachment; filename="table-{table.number}-qr.png"'
            return resp
        return HttpResponse(buf.getvalue(), content_type='image/png', status=200)

    @action(detail=True, methods=['post'], url_path='regenerate-qr')
    def regenerate_qr(self, request, pk=None):
        """QR tokenni yangilash (eski QR kodlar bekor bo'ladi)."""
        table = self.get_object()
        table.regenerate_qr()
        return Response({
            'success': True,
            'message': f'Stol #{table.number} QR kodi yangilandi.',
            'qr_token': str(table.qr_token),
            'qr_content': table.qr_content,
        })

    @action(detail=False, methods=['get'], url_path='busy-map')
    def busy_map(self, request):
        """Barcha stollar holati (band/bo'sh) — admin bosh sahifasi uchun."""
        tables = self.get_queryset()
        data = TableSerializer(tables, many=True, context={'request': request}).data
        return Response({'success': True, 'results': data})


class ValidateTableView(APIView):
    """
    POST /api/restaurant/tables/validate/
    Mini App QR skanerlagandan keyin stolni tasdiqlaydi.
    Mijoz "Buyurtma berish" → QR skaner → bu endpoint → tasdiqlash dialogi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        s = TableValidateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        number = s.validated_data['table_number']
        token = s.validated_data['qr_token']

        table = Table.objects.filter(
            number=number, qr_token=token, is_active=True).first()
        if not table:
            raise SmartOshxonaAPIException(
                'QR kod yaroqsiz yoki stol topilmadi. Iltimos, ofitsiantga murojaat qiling.',
                code='invalid_qr', status_code=400)

        return Response({
            'success': True,
            'table': {
                'id': str(table.id),
                'number': table.number,
                'name': table.name,
                'seats': table.seats,
            },
        })
