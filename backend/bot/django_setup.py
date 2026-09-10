"""bot/django_setup.py — bot jarayonida Django ORM ni yoqish."""
import os

# aiogram async kontekstida Django ORM sinxron chaqiruvlariga ruxsat berish.
# Bu quyidagi xatoni hal qiladi:
#   SynchronousOnlyOperation: You cannot call this from an async context
# Kichik/o'rtacha yuklama uchun mutlaqo yetarli (har bir DB so'rovi
# bir necha millisekund davomida event loop'ni bloklaydi — muammo emas).
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

import django

django.setup()
