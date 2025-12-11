"""
Django settings for bidsconnect project.
"""

from pathlib import Path
import os
from datetime import timedelta

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-^25!+&(b68a4s!^ie%0w9-^y96!z3if%vrc8elno6e=!#rq9dm'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [
    '178.128.143.28',
    'bidsconnect.co.tz',
    'www.bidsconnect.co.tz',
    'localhost',
    '127.0.0.1',
    'bidsconnect.co.tz,bidsconnect.co.tz',  # safety net for broken proxy
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',

    # Your apps
    'accounts',
    'analytics',
    'bids',
    'legal',
    'notifications',
    'payments',
    'tenders',
    'marketplace',
    'automation',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'djoser',
    'django_filters',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bidsconnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'bidsconnect.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────────────────────
#  CRITICAL: STATIC & MEDIA SETTINGS (THIS WAS MISSING!)
# ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = '/home/sammy/bidsconnectBack/staticfiles'   # ← REQUIRED for collectstatic

MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/sammy/bidsconnectBack/media'

# Optional: if you have a project-level static folder
# STATICFILES_DIRS = [BASE_DIR / "static"]

# ──────────────────────────────────────────────────────────────

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
}

# Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Djoser + Custom User
AUTH_USER_MODEL = 'accounts.CustomUser'

DJOSER = {
    'LOGIN_FIELD': 'email',
    'USER_CREATE_PASSWORD_RETYPE': False,
    'SEND_ACTIVATION_EMAIL': False,
    'SET_PASSWORD_RETYPE': True,
    'PASSWORD_RESET_CONFIRM_RETYPE': True,
    'TOKEN_MODEL': None,
    'SERIALIZERS': {
        'user_create': 'accounts.serializers.CustomUserCreateSerializer',
        'user': 'accounts.serializers.CustomUserCreateSerializer',
        'current_user': 'accounts.serializers.CustomUserDetailSerializer',
    },
    'PERMISSIONS': {
        'user_create': ['rest_framework.permissions.AllowAny'],
        'user': ['rest_framework.permissions.IsAuthenticated'],
        'user_list': ['rest_framework.permissions.IsAuthenticated'],
    },
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "http://178.128.143.28",
    "http://bidsconnect.co.tz",
    "http://www.bidsconnect.co.tz",
    "https://178.128.143.28",
    "https://bidsconnect.co.tz",
    "https://www.bidsconnect.co.tz",
]
CORS_ALLOW_CREDENTIALS = True

# Security (set to True when you enable HTTPS)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'