"""apps/products/models.py — kategoriya, mahsulot, rasmlar va narx tarixi.

Ma'lumotlar bazasi optimallashtirishlari:
  • select_related/prefetch_related bilan ishlashga tayyor related_name'lar
  • katta so'rovlar uchun qamrovli (composite) indekslar
  • ochiq menyu API keshlanadi (MENU_CACHE_TTL)
"""
import uuid

from django.core.validators import MinValueValidator
from django.db import models

from config.base_model import SoftDeleteModel, TimeStampedModel


class Category(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name_uz = models.CharField(max_length=100, verbose_name='Nomi (uz)')
    name_ru = models.CharField(max_length=100, verbose_name='Nomi (ru)')
    icon = models.CharField(
        max_length=16, blank=True, verbose_name='Emoji',
        help_text='Mini App kartochkasida chiqadi, masalan 🍢')
    order_num = models.PositiveSmallIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'categories'
        verbose_name = 'Kategoriya'
        verbose_name_plural = 'Kategoriyalar'
        ordering = ['order_num', 'name_uz']
        indexes = [models.Index(fields=['is_active', 'order_num'])]

    def __str__(self):
        return self.name_uz

    def get_name(self, lang='uz'):
        return self.name_uz if lang == 'uz' else self.name_ru


class Product(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='products',
        verbose_name='Kategoriya')
    name_uz = models.CharField(max_length=200, verbose_name='Nomi (uz)')
    name_ru = models.CharField(max_length=200, verbose_name='Nomi (ru)')
    description_uz = models.TextField(blank=True, verbose_name='Izoh (uz)')
    description_ru = models.TextField(blank=True, verbose_name='Izoh (ru)')
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name='Narx')
    image = models.ImageField(
        upload_to='products/', null=True, blank=True, verbose_name='Rasm')
    is_available = models.BooleanField(
        default=True, db_index=True, verbose_name='Sotuvda')
    order_num = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'products'
        verbose_name = 'Mahsulot'
        verbose_name_plural = 'Mahsulotlar'
        ordering = ['order_num', 'name_uz']
        indexes = [
            models.Index(fields=['category', 'is_available']),
            models.Index(fields=['is_available', 'order_num']),
        ]

    def __str__(self):
        return self.name_uz

    def get_name(self, lang='uz'):
        return self.name_uz if lang == 'uz' else self.name_ru

    def get_description(self, lang='uz'):
        return self.description_uz if lang == 'uz' else self.description_ru

    def save(self, *args, **kwargs):
        """Narx o'zgarsa — PriceHistory ga log yoziladi (hisobotlar uchun)."""
        if self.pk:
            try:
                old = Product.objects.get(pk=self.pk)
                if old.price != self.price:
                    PriceHistory.objects.create(
                        product=self, old_price=old.price, new_price=self.price)
            except Product.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    """Mahsulot galereyasi (qo'shimcha rasmlar)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    order_num = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_images'
        ordering = ['order_num', 'id']


class PriceHistory(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    old_price = models.DecimalField(max_digits=12, decimal_places=2)
    new_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'price_history'
        ordering = ['-created_at']
