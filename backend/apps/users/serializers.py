"""apps/users/serializers.py"""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'telegram_id', 'telegram_username', 'first_name',
            'last_name', 'phone', 'lang', 'is_registered', 'is_staff',
            'date_joined',
        ]
        read_only_fields = ['id', 'telegram_id', 'is_registered', 'is_staff', 'date_joined']

class AdminProfileSerializer(serializers.ModelSerializer):
    """Admin Panel "Profil" bo'limi: ism, telefon, email va avatar."""
    avatar_url = serializers.SerializerMethodField()
    username = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email', 'phone',
            'avatar', 'avatar_url', 'is_staff', 'date_joined',
        ]
        read_only_fields = ['id', 'username', 'avatar_url', 'is_staff', 'date_joined']

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if obj.avatar:
            url = obj.avatar.url
            return request.build_absolute_uri(url) if request else url
        return None


class ChangePasswordSerializer(serializers.Serializer):
    """Parol o'zgartirish: eski parol tekshiriladi, yangisi min 6 belgi."""
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

    def validate_old_password(self, val):
        user = self.context['request'].user
        if not user.check_password(val):
            raise serializers.ValidationError('Eski parol noto‘g‘ri.')
        return val

class TelegramAuthSerializer(serializers.Serializer):
    """Mini App initData ni qabul qiladi."""
    init_data = serializers.CharField(required=False, allow_blank=True, default='')


class AdminLoginSerializer(serializers.Serializer):
    """Admin Panel uchun username/parol."""
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, write_only=True, style={'input_type': 'password'})
