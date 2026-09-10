"""apps/users/views.py — autentifikatsiya endpointlari."""
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from config.exceptions import SmartOshxonaAPIException
from .models import User
from .serializers import (AdminLoginSerializer, AdminProfileSerializer,
                          ChangePasswordSerializer, TelegramAuthSerializer,
                          UserSerializer)
from .services import TelegramInitDataError, validate_init_data

logger = logging.getLogger('apps')


class TelegramAuthView(APIView):
    """
    POST /api/auth/telegram/
    Mini App initData ni tekshirib, mijozni ro'yxatdan o'tkazadi
    va JWT tokenlar qaytaradi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        s = TelegramAuthSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        raw_init = s.validated_data['init_data']


        if not raw_init and settings.DEBUG:
            user, _ = User.objects.get_or_create(
                username='dev_guest',
                defaults={'first_name': 'Dev Guest'})
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data,
            })

        try:
            parsed = validate_init_data(s.validated_data['init_data'])
        except TelegramInitDataError as e:
            raise SmartOshxonaAPIException(str(e), code='telegram_auth', status_code=401)

        tg_user = parsed['_user']
        user = User.get_or_create_telegram_user(tg_user)

        refresh = RefreshToken.for_user(user)
        refresh['tg_id'] = user.telegram_id

        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class AdminLoginView(APIView):
    """
    POST /api/auth/login/
    Admin Panel uchun username/parol bilan JWT olish.
    Faqat is_staff=True foydalanuvchi ruxsat oladi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        s = AdminLoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        token_ser = TokenObtainPairSerializer(data=s.validated_data)
        try:
            token_ser.validate(s.validated_data)
        except Exception:
            return Response(
                {'success': False, 'message': 'Login yoki parol noto‘g‘ri.'},
                status=status.HTTP_401_UNAUTHORIZED)

        user = token_ser.user
        if not user.is_staff:
            return Response(
                {'success': False, 'message': 'Faqat xodimlar uchun.'},
                status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })
class DevGuestAuthView(APIView):
    """
    POST /api/auth/dev-guest/
    FAQAT DEBUG=True da ishlaydi — Telegram tashqarisida (oddiy brauzerda)
    Mini App ni test qilish uchun. Prodakshnda (DEBUG=False) 403 qaytaradi.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.conf import settings
        if not settings.DEBUG:
            return Response(
                {'success': False, 'message': 'Bu endpoint faqat DEBUG rejimida ishlaydi.'},
                status=status.HTTP_403_FORBIDDEN)

        user = User.objects.filter(telegram_id=999999999).first()
        if user is None:
            user = User.objects.create(
                telegram_id=999999999,
                username='tg_999999999',
                first_name='Test',
                last_name='Mijoz',
                is_registered=True,
            )

        refresh = RefreshToken.for_user(user)
        refresh['tg_id'] = user.telegram_id

        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })

class RefreshTokenView(APIView):
    """POST /api/auth/refresh/ — access tokenni yangilash."""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'success': False, 'message': 'refresh talab qilinadi.'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            from rest_framework_simplejwt.tokens import RefreshToken as RT
            rt = RT(refresh_token)
            return Response({
                'success': True,
                'access': str(rt.access_token),
            })
        except Exception:
            return Response({'success': False, 'message': 'Token yaroqsiz.'},
                            status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    """GET /api/auth/me/ — joriy foydalanuvchi ma'lumoti (til sozlash uchun ham)."""
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({'success': False, 'message': 'Avval tizimga kiring.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        return Response({'success': True, 'user': UserSerializer(request.user).data})

    def patch(self, request):
        """Til yoki telefon raqamini yangilash."""
        if not request.user or not request.user.is_authenticated:
            return Response({'success': False, 'message': 'Avval tizimga kiring.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'user': serializer.data})



class ProfileView(APIView):
    """
    GET   /api/auth/profile/  — admin profilini ko'rish
    PATCH /api/auth/profile/  — ism/familiya/telefon/email + avatar (multipart)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'success': True,
            'profile': AdminProfileSerializer(
                request.user, context={'request': request}).data,
        })

    def patch(self, request):
        serializer = AdminProfileSerializer(
            request.user, data=request.data, partial=True,
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'success': True,
            'message': 'Profil saqlandi.',
            'profile': serializer.data,
        })


class ChangePasswordView(APIView):
    """POST /api/auth/profile/password/ — parolni o'zgartirish."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'success': True, 'message': 'Parol yangilandi.'})
