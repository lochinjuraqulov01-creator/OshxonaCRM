"""apps/restaurant/serializers.py"""
from rest_framework import serializers

from .models import Table


class TableSerializer(serializers.ModelSerializer):
    is_busy = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    active_orders_count = serializers.SerializerMethodField()
    qr_url = serializers.SerializerMethodField()

    class Meta:
        model = Table
        fields = [
            'id', 'number', 'name', 'seats', 'is_active', 'note',
            'qr_token', 'qr_url', 'qr_content',
            'is_busy', 'status_display', 'active_orders_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'qr_token', 'created_at', 'updated_at']

    def get_active_orders_count(self, obj):
        return obj.active_orders.count()

    def get_qr_url(self, obj):
        request = self.context.get('request')
        path = f'/api/restaurant/tables/{obj.id}/qr/'
        return request.build_absolute_uri(path) if request else path

    def validate_number(self, value):
        qs = Table.objects.filter(number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Bu raqamli stol allaqachon mavjud.')
        return value


class TableValidateSerializer(serializers.Serializer):
    """Mini App QR skanerlagandan keyin stolni tekshirish."""
    table_number = serializers.IntegerField(min_value=1)
    qr_token = serializers.UUIDField()
