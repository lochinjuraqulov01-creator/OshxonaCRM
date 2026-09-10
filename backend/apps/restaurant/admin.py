from django.contrib import admin

from .models import Table


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'name', 'seats', 'is_active',
                    'is_busy', 'created_at')
    list_editable = ('is_active',)
    search_fields = ('number', 'name')
    list_filter = ('is_active',)
