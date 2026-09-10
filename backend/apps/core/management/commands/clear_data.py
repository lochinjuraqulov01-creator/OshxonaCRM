"""
python manage.py clear_data [--orders] [--products] [--tables] [--users] [--all] [--yes]

Demo/sinov ma'lumotlarini tozalash.
Hech qanday flag bermasangiz — interaktiv menyuni ko'rsatadi.

Misol:
  python manage.py clear_data --orders              # faqat buyurtmalar + fikrlar
  python manage.py clear_data --products            # menyu (mahsulot + kategoriya)
  python manage.py clear_data --all                 # hamma narsa (admin qoladi)
  python manage.py clear_data --all --yes           # tasdiqsiz, to'g'ridan-to'g'ri

Admin foydalanuvchi (superuser) hech qachon o'chmaydi.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.orders.models import Cart, Feedback, Order
from apps.products.models import Category, Product
from apps.restaurant.models import Table
from apps.users.models import User


class Command(BaseCommand):
    help = 'Demo ma\'lumotlarni tozalaydi (buyurtmalar, menyu, stollar, mijozlar)'

    def add_arguments(self, parser):
        parser.add_argument('--orders', action='store_true',
                            help='Buyurtmalar, buyurtma tarkibi, fikrlar o\'chiriladi')
        parser.add_argument('--products', action='store_true',
                            help='Menyu: mahsulotlar va kategoriyalar o\'chiriladi')
        parser.add_argument('--tables', action='store_true',
                            help='Stollar o\'chiriladi')
        parser.add_argument('--users', action='store_true',
                            help='Mijozlar (superuser emas!) o\'chiriladi')
        parser.add_argument('--all', action='store_true',
                            help='Yuqoridagi hammasi (admin qoladi)')
        parser.add_argument('--yes', '-y', action='store_true',
                            help='Tasdiq so\'ramasdan bajaradi')

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        orders = options['orders']
        products = options['products']
        tables = options['tables']
        users = options['users']

        if options['all']:
            orders = products = tables = users = True

        # Flag berilmagan bo'lsa — interaktiv rejim
        if not (orders or products or tables or users):
            orders, products, tables, users = self._interactive()
            if not (orders or products or tables or users):
                self.stdout.write('Hech narsa o\'chirilmadi.')
                return

        counts = self._summary(orders, products, tables, users)
        if not any(counts.values()):
            self.stdout.write(self.style.WARNING('Baza allaqachon bo\'sh.'))
            return

        self._print_summary(counts)

        if not options['yes']:
            answer = input('\nRostdan ham o\'chirilsinmi? (ha/yo\'q): ').strip().lower()
            if answer not in ('ha', 'h', 'yes', 'y'):
                self.stdout.write('Bekor qilindi. Hech narsa o\'chirilmadi.')
                return

        deleted = self._do_delete(orders, products, tables, users)
        self.stdout.write(self.style.SUCCESS(
            f'\n✔ Tozalandi. Jami o\'chirilgan yozuvlar: {deleted}'))
        self.stdout.write('Endi o\'z ma\'lumotlaringizni qo\'shishingiz mumkin:\n'
                          '  • Admin panel:  /adminpanel/  (Menyu, Stollar bo\'limlari)\n'
                          '  • Django admin: /admin/\n'
                          '  • Yoki: python manage.py seed_demo --if-empty')

    # ------------------------------------------------------------------
    def _interactive(self):
        self.stdout.write('\nNimalarni tozalamoqchisiz? (vergul bilan yozing, masalan: 1,2)')
        self.stdout.write('  1) Buyurtmalar va fikrlar')
        self.stdout.write('  2) Menyu (mahsulotlar + kategoriyalar)')
        self.stdout.write('  3) Stollar')
        self.stdout.write('  4) Mijozlar (superuser qoladi)')
        self.stdout.write('  5) Hammasi')
        raw = input('Tanlov [1,2,3,4,5 / bo\'sh = bekor]: ').strip()
        if not raw:
            return False, False, False, False
        parts = {p.strip() for p in raw.split(',') if p.strip()}
        if '5' in parts:
            return True, True, True, True
        return ('1' in parts, '2' in parts, '3' in parts, '4' in parts)

    # ------------------------------------------------------------------
    def _counts(self, qs):
        return qs.count()

    def _summary(self, orders, products, tables, users):
        from apps.notifications.models import NotificationLog
        from apps.orders.models import Cart

        c = {}
        c['Bildirishnomalar'] = self._counts(NotificationLog.objects)
        c['Fikrlar'] = self._counts(Feedback.objects)
        c['Savatlar'] = self._counts(Cart.objects)
        c['Buyurtmalar'] = self._counts(Order.objects)
        c['Mahsulotlar'] = self._counts(Product.objects)
        c['Kategoriyalar'] = self._counts(Category.objects)
        c['Stollar'] = self._counts(Table.objects)
        c['Mijozlar'] = (User.objects.filter(is_superuser=False).count()
                         if users else 0)
        if not orders:
            c['Bildirishnomalar'] = c['Fikrlar'] = c['Buyurtmalar'] = 0
        if not products:
            c['Mahsulotlar'] = c['Kategoriyalar'] = 0
        if not tables:
            c['Stollar'] = 0
        return c

    def _print_summary(self, counts):
        self.stdout.write('\nO\'chiriladigan yozuvlar:')
        for name, n in counts.items():
            mark = '•' if n else ' '
            self.stdout.write(f'  {mark} {name}: {n}')
        self.stdout.write('  (Admin/superuser foydalanuvchi o\'chmaydi)')

    # ------------------------------------------------------------------
    def _do_delete(self, orders, products, tables, users):
        """FK bog'liqlik tartibida o'chiradi — xatosiz."""
        from apps.notifications.models import NotificationLog
        from apps.orders.models import Cart, CartItem

        deleted = 0

        if orders:
            deleted += NotificationLog.objects.all().delete()[0]
            deleted += Feedback.objects.all().delete()[0]
            deleted += CartItem.objects.all().delete()[0]
            deleted += Cart.objects.all().delete()[0]
            deleted += Order.objects.all().delete()[0]
            self.stdout.write('  ✔ Buyurtmalar, savatlar, fikrlar o\'chirildi')

        if products:
            # savat/buyurtma itemlari productga CASCADE — orders allaqachon
            # o'chirilgan bo'lsa ham, faqat qolganlarini tozalaymiz
            deleted += CartItem.objects.all().delete()[0]
            deleted += Cart.objects.all().delete()[0]
            deleted += Product.objects.all().delete()[0]
            deleted += Category.objects.all().delete()[0]
            self.stdout.write('  ✔ Menyu (mahsulotlar + kategoriyalar) o\'chirildi')

        if tables:
            deleted += Table.objects.all().delete()[0]
            self.stdout.write('  ✔ Stollar o\'chirildi')

        if users:
            n, _ = User.objects.filter(is_superuser=False).delete()
            deleted += n
            self.stdout.write('  ✔ Mijozlar o\'chirildi (superuser qoldi)')

        return deleted
