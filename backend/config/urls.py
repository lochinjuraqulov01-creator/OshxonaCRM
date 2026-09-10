"""config/urls.py — asosiy URL marshrutlari."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import re_path
from django.views.static import serve as media_serve

@never_cache   # Mini App HTML keshlanmasin
def miniapp_view(request):
    return render(request, 'miniapp/index.html')


@never_cache   # Admin Panel HTML i ham keshlanmasin (eski app.js qolmasligi uchun)
def adminpanel_view(request):
    return render(request, 'adminpanel/index.html')

urlpatterns = [
    path('django-admin/', admin.site.urls),

    # ---- Mini App (mijozlar tomoni) ----
    path('miniapp/', miniapp_view, name='miniapp'),

    # ---- Admin Panel (web) ----
    path('adminpanel/', adminpanel_view, name='adminpanel'),
    # ---- API ----
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/auth/', include('apps.users.urls')),
    path('api/restaurant/', include('apps.restaurant.urls')),
    path('api/products/', include('apps.products.urls')),
    path('api/orders/', include('apps.orders.urls')),
    path('api/stats/', include('apps.analytics.urls')),
]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', media_serve, {'document_root': settings.MEDIA_ROOT}),
]