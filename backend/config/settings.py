"""
SmartOshxona — Django Settings (v1.0)
=====================================
Oshxona avtomatlashtirish tizimi:
  • Telegram Bot + Mini App (mijozlar tomoni)
  • Web Admin Panel (admin tomoni)
  • REST API (Django REST Framework)
  • Real-time (WebSocket / Channels)
Barcha sozlamalar .env fayli orqali boshqariladi.
"""
from pathlib import Path
from datetime import timedelta

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== ASOSIY ====================
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-ozgartiring')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

# Reverse proxy (ngrok/nginx) orqali ishlash uchun
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ==================== ILOVALAR ====================
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'django_cleanup.apps.CleanupConfig',   # o'chirilgan fayl rasmlarini tozalash
    'channels',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.restaurant',
    'apps.products',
    'apps.orders',
    'apps.notifications',
    'apps.analytics',
]

# 'daphne' — runserver ni ASGI (WebSocket) rejimiga o'tkazadi; birinchi bo'lishi shart
INSTALLED_APPS = ['daphne'] + DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Mini App / Admin panel statik fayllari (JS/CSS)
STATICFILES_DIRS = [BASE_DIR / 'static']

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ==================== MA'LUMOTLAR BAZASI ====================
# Prod: PostgreSQL.  Tez lokal demo: .env da DB_ENGINE=sqlite
DB_ENGINE = config('DB_ENGINE', default='postgres')
DATABASE_URL = config('DATABASE_URL', default='')   # Railway shu o'zgaruvchini beradi

if DATABASE_URL:
    # Railway/Heroku uslubi: bitta URL orqali ulanish
    from urllib.parse import urlparse
    u = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': u.path.lstrip('/'),
            'USER': u.username,
            'PASSWORD': u.password,
            'HOST': u.hostname,
            'PORT': str(u.port or 5432),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {'sslmode': 'require', 'connect_timeout': 10},
        }
    }


elif DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='smart_oshxona'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default='postgres'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {'connect_timeout': 10},
        }
    }


# ==================== REDIS / KESH ====================
# Redis yo'q bo'lsa (lokal demo) — lokal kesh va in-memory channel layer
USE_REDIS = config('USE_REDIS', default=True, cast=bool)
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

if USE_REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
            'KEY_PREFIX': 'smartoshxona',
            'TIMEOUT': 300,                          # 5 daqiqalik kesh
        }
    }
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL], 'capacity': 1500, 'expiry': 10},
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'smartoshxona-local',
            'TIMEOUT': 300,
        }
    }
    CHANNEL_LAYERS = {
        'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
    }

# Kesh TTL-lari (optimallashtirish: tez ma'lumot almashinuvi)
MENU_CACHE_TTL = 120        # ochiq menyu — 2 daqiqa
STATS_CACHE_TTL = 60        # statistika — 1 daqiqa
QR_CACHE_TTL = 300

# ==================== CUSTOM USER ====================
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==================== XALQAROLASHTIRISH ====================
LANGUAGE_CODE = 'uz'
TIME_ZONE = config('TIME_ZONE', default='Asia/Tashkent')
USE_I18N = True
USE_TZ = True

# ==================== STATIC / MEDIA ====================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = '/media/'

MEDIA_ROOT = Path(config('MEDIA_ROOT', default=str(BASE_DIR / 'media')))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== DRF ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '120/min',
        'user': '600/min',
    },
    'EXCEPTION_HANDLER': 'config.exceptions.custom_exception_handler',
}

# ==================== JWT ====================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_MINUTES', default=30, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_DAYS', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
}

# ==================== CORS ====================
# Mini App Telegram domenidan, admin panel esa lokal/prod domenidan keladi
CORS_ALLOW_ALL_ORIGINS = True          # v1: soddalik; prod da aniq domenlar ko'rsatiling
CORS_ALLOWED_ORIGINS = [
    'https://web.telegram.org',
    'https://telegram.org',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv())

# ==================== TELEGRAM ====================
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'
TELEGRAM_ADMIN_CHAT_ID = config('TELEGRAM_ADMIN_CHAT_ID', default='')
MINI_APP_URL = config('MINI_APP_URL', default='https://example.uz/miniapp/')
ADMIN_PANEL_URL = config('ADMIN_PANEL_URL', default='https://example.uz/adminpanel/')

# ==================== OSHXONA SOZLAMALARI ====================
RESTAURANT_NAME = config('RESTAURANT_NAME', default='SmartOshxona')
SERVICE_PERCENT = config('SERVICE_PERCENT', default=0, cast=int)   # xizmat haqi %
QR_CONTENT_PREFIX = 'SMARTOX:TABLE:'   # QR kod mazmuni: SMARTOX:TABLE:<raqam>:<token>

# ==================== API HUJJATLARI ====================
SPECTACULAR_SETTINGS = {
    'TITLE': 'SmartOshxona API',
    'DESCRIPTION': 'Oshxona avtomatlashtirish tizimi — REST API '
                   '(Bot + Mini App + Admin Panel uchun)',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ==================== LOGGING ====================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} [{module}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'smartoshxona.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'bot': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}
