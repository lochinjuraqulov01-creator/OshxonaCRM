"""apps/users/managers.py"""
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """telegram_id bo'yicha qulay qidiruv + superuser yaratish."""

    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError('Username bo‘lishi shart')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser is_staff=True bo‘lishi kerak')
        return self.create_user(username, email, password, **extra_fields)

    def telegram(self, telegram_id: int):
        return self.filter(telegram_id=telegram_id).first()
