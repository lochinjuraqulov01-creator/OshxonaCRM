from .views import (AdminLoginView, ChangePasswordView, MeView,
                    ProfileView, RefreshTokenView, TelegramAuthView, DevGuestAuthView)
from django.urls import path

app_name = 'users'

urlpatterns = [
    path('telegram/', TelegramAuthView.as_view(), name='telegram-auth'),
    path('dev-guest/', DevGuestAuthView.as_view(), name='dev-guest'),
    path('login/', AdminLoginView.as_view(), name='admin-login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('me/', MeView.as_view(), name='me'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/password/', ChangePasswordView.as_view(), name='profile-password'),
]
