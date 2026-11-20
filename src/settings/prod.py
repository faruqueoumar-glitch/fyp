from .base import *

import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY environment variable must be set in production')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
# Ensure .onrender.com is allowed
if not any('onrender.com' in h for h in ALLOWED_HOSTS):
    ALLOWED_HOSTS.append('.onrender.com')

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
import dj_database_url

db_url = os.environ.get('DATABASE_URL')
if db_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=db_url,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Honor the 'X-Forwarded-Proto' header for HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

USE_X_FORWARDED_HOST = True
CSRF_FAILURE_VIEW = 'app.views.csrf_failure_view'

# Trust Render domains for CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://fyp-2uhr.onrender.com',
    'https://*.onrender.com',
]
for raw_origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(','):
    origin = raw_origin.strip().rstrip('/')
    if origin and origin.startswith(('http://', 'https://')) and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)
external_url = os.environ.get('RENDER_EXTERNAL_URL', '').strip().rstrip('/')
if external_url and external_url.startswith(('http://', 'https://')) and external_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(external_url)

# WhiteNoise middleware for serving static files
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'app.middleware.BruteForceRateLimitMiddleware',
    'app.middleware.PharmacyContextMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Simplified static file serving.
# https://docs.djangoproject.com/en/3.2/howto/static-files/
# https://warehouse.pypa.io/project/whitenoise/stable/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
# Absolute path to the directory static files are collected to.
# https://docs.djangoproject.com/en/3.2/howto/static-files/#std:setting-STATIC_ROOT
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Production caching configuration using Redis (Render)
import importlib.util

redis_url = os.environ.get('REDIS_URL')
if redis_url and importlib.util.find_spec('redis') is not None:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': redis_url,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# Security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Cookie security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 28800  # 8 hours


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# Email Configuration
# https://docs.djangoproject.com/en/6.0/ref/settings/#email-backend
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@pharmaudit.example')

# Fall back to console email backend for development if EMAIL_HOST is not set
# This ensures password reset requests never crash with a 500 error in dev
BREVO_API_KEY = os.environ.get('BREVO_API_KEY')
if BREVO_API_KEY:
    EMAIL_BACKEND = 'app.email_backends.BrevoEmailBackend'
elif not EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
