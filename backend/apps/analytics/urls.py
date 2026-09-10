from django.urls import path

from .views import AdminStatsView, TodayStatsView

app_name = 'analytics'

urlpatterns = [
    path('today/', TodayStatsView.as_view(), name='today'),
    path('admin/', AdminStatsView.as_view(), name='admin'),
]
