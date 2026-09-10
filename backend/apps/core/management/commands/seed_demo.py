"""
python manage.py seed_demo [--if-empty] [--force]

Demo ma'lumotlar yaratadi:
  • admin foydalanuvchi (admin / admin123)
  • 5 kategoriya, ~15 mahsulot
  • 8 stol (QR tokenlar bilan)
  • bir nechta demo buyurtma (statistika grafiklari uchun)
"""
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.products.models import Category, Product
from apps.restaurant.models import Table
from apps.users.models import User


class Command(BaseCommand):
    help = 'Demo ma\'lumotlarni yaratadi (admin, menyu, stollar, buyurtmalar)'

    def add_arguments(self, parser):
        parser.add_argument('--if-empty', action='store_true',
                            help='Faqat baza bo\'sh bo\'lsa yaratadi')
        parser.add_argument('--force', action='store_true',
                            help='Mavjud ma\'lumotlarni e\'tiborsiz qoldirib qo\'shadi')

    def handle(self, *args, **options):
        if options['if_empty'] and (
                Category.objects.exists() or Table.objects.exists()):
            self.stdout.write(self.style.WARNING('Baza to‘ldirilgan — seed o‘tkazildi.'))
            return

        # ---------- Admin ----------
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin', email='admin@smartoshxona.uz',
                password='admin123', first_name='Bosh administrator')
            self.stdout.write(self.style.SUCCESS('✔ Admin yaratildi: admin / admin123'))

        # ---------- Kategoriyalar ----------
        cats_data = [
            ('Milliy taomlar', 'Национальные блюда', '🍲', 1),
            ('Kaboblar', 'Шашлыки', '🍢', 2),
            ('Salatlar', 'Салаты', '🥗', 3),
            ('Ichimliklar', 'Напитки', '🥤', 4),
            ('Shirinliklar', 'Десерты', '🍰', 5),
        ]
        cats = {}
        for uz, ru, icon, order in cats_data:
            cat, created = Category.objects.get_or_create(
                name_uz=uz,
                defaults={'name_ru': ru, 'icon': icon, 'order_num': order})
            cats[uz] = cat

        # ---------- Mahsulotlar ----------
        products_data = [
            ('Milliy taomlar', 'Osh', 'Плов', 32000, 'Besh xil gosht bilan pishirilgan an\'anaviy osh'),
            ('Milliy taomlar', 'Lagmon', 'Лагман', 28000, 'Qo\'lda cho\'zilgan lagmon, qovurilgan go\'sht bilan'),
            ('Milliy taomlar', 'Manti', 'Манты', 24000, '5 dona, qiyma va piyoz bilan'),
            ('Milliy taomlar', 'Sho‘rva', 'Суп', 22000, 'Qo\'y go\'shtidan boy sho\'rva'),
            ('Kaboblar', 'Tovuq kabob', 'Шашлык из курицы', 18000, '1 dona, tovuq filesi'),
            ('Kaboblar', 'Qo‘y kabob', 'Шашлык из баранины', 25000, '1 dona, qo\'y go\'shti'),
            ('Kaboblar', 'Baklajon kabob', 'Овощной шашлык', 12000, '1 dona, baklajon va pomidor'),
            ('Salatlar', 'Achichuk', 'Ачичук', 14000, 'Pomidor, piyoz, bodring'),
            ('Salatlar', 'Yunon salati', 'Греческий салат', 22000, 'Feta pishloqi va zaytun bilan'),
            ('Ichimliklar', 'Ko‘k choy', 'Зелёный чай', 5000, 'Xitoy choyi, choynak 1 litr'),
            ('Ichimliklar', 'Ayron', 'Айран', 8000, 'Tabiiy ayron 0.3 l'),
            ('Ichimliklar', 'Pepsi', 'Пепси', 9000, '0.5 l, sovutilgan'),
            ('Ichimliklar', 'Fresh apelsin', 'Апельсиновый сок', 16000, 'Yangi siqilgan 0.3 l'),
            ('Shirinliklar', 'Medovik', 'Медовик', 15000, 'Asal torti, bo\'lak'),
            ('Shirinliklar', 'Chak-chak', 'Чак-чак', 12000, 'An\'anaviy chak-chak'),
            ('Shirinliklar', 'Muzqaymoq', 'Мороженое', 10000, 'Vanilya muzqaymoq, yagodalar bilan'),
        ]
        created_products = 0
        for cat_name, uz, ru, price, desc in products_data:
            _, created = Product.objects.get_or_create(
                name_uz=uz,
                defaults={
                    'category': cats[cat_name],
                    'name_ru': ru,
                    'description_uz': desc,
                    'description_ru': desc,
                    'price': Decimal(price),
                    'order_num': created_products,
                })
            created_products += int(created)

        self.stdout.write(self.style.SUCCESS(f'✔ Mahsulotlar: {created_products} ta'))

        # ---------- Stollar ----------
        for i in range(1, 9):
            Table.objects.get_or_create(
                number=i,
                defaults={'name': 'Zal 1' if i <= 6 else 'Terasa',
                          'seats': 4 if i <= 6 else 6})
        self.stdout.write(self.style.SUCCESS('✔ Stollar: 8 ta'))

        # ---------- Demo buyurtmalar ----------
        if not options['force'] and Order_exists():
            self.stdout.write(self.style.WARNING('Buyurtmalar mavjud — demo buyurtmalar yaratilmadi.'))
            return

        from apps.orders.models import Order, OrderItem

        demo_user, _ = User.objects.get_or_create(
            username='demo_guest',
            defaults={'first_name': 'Demo mijoz', 'is_registered': True})
        products = list(Product.objects.all())
        tables = list(Table.objects.all())
        statuses = [Order.STATUS_DELIVERED, Order.STATUS_DELIVERED,
                    Order.STATUS_DELIVERED, Order.STATUS_PREPARING,
                    Order.STATUS_NEW, Order.STATUS_IN_PROGRESS,
                    Order.STATUS_CANCELLED]

        count = 0
        for days_ago in range(6, -1, -1):
            for _ in range(random.randint(2, 5)):
                created_at = (timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
                              - timezone.timedelta(days=days_ago)
                              + timezone.timedelta(hours=random.randint(11, 20),
                                                   minutes=random.randint(0, 59)))
                status = statuses[min(days_ago, len(statuses) - 1)]
                order = Order(
                    user=demo_user,
                    table=random.choice(tables),
                    status=status,
                    customer_note=random.choice(['', '', 'Achchiq qilmang', 'Tezroq bo‘lsa']))
                order.created_at = created_at
                order.save()

                chosen = random.sample(products, random.randint(2, 4))
                subtotal = Decimal(0)
                cnt = 0
                for p in chosen:
                    qty = random.randint(1, 3)
                    subtotal += p.price * qty
                    cnt += qty
                    OrderItem.objects.create(
                        order=order, product=p, product_name=p.name_uz,
                        quantity=qty, unit_price=p.price)
                order.subtotal = subtotal
                order.total = subtotal
                order.items_count = cnt
                if status == Order.STATUS_PREPARING:
                    order.accepted_at = created_at
                elif status in (Order.STATUS_DELIVERED, Order.STATUS_IN_PROGRESS):
                    order.accepted_at = created_at
                    order.ready_at = created_at + timezone.timedelta(minutes=15)
                    order.delivered_at = (created_at + timezone.timedelta(minutes=25)
                                          if status == Order.STATUS_DELIVERED else None)
                order.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f'✔ Demo buyurtmalar: {count} ta'))
        self.stdout.write(self.style.SUCCESS('Demo ma\'lumotlar tayyor!'))


def Order_exists():
    from apps.orders.models import Order
    return Order.objects.exists()
