"""config/base_model.py — umumiy abstrakt modellar."""
import uuid

from django.db import models


class UUIDModel(models.Model):
    """UUID asosiy kalitli abstrakt model."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Yaratilgan/yangilangan vaqt maydonlari."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """O'chirilganda bazadan ketmaydi, faqat belgilanadi (is_deleted)."""
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save(update_fields=['is_deleted'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
