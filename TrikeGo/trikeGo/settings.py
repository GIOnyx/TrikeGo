"""
Django settings for trikeGo project.
"""

from dotenv import load_dotenv
load_dotenv()
import os
import dj_database_url 
from dotenv import load_dotenv # Already there
load_dotenv() # Already there
from supabase import create_client
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# Reads the DEBUG env var, defaults to False if not set. Handles 'True'/'False' strings.
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# settings.py

# ... other imports ...

# Dynamic Hostname Configuration for Render
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000'] # Add 127.0.0.1 here too

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    # Add the render external hostname to CSRF trusted origins (must include scheme)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Allow any Render-provided onrender.com hostname (subdomains) in ALLOWED_HOSTS so deployments
# don't need to set RENDER_EXTERNAL_HOSTNAME for simple cases. This uses the leading dot pattern
# which Django's ALLOWED_HOSTS accepts to match subdomains.
ALLOWED_HOSTS.append('.onrender.com')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework', 
    'user',
    'booking',
    'chat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# If we're running behind a proxy (Render), respect X-Forwarded-Proto so Django knows when
# requests are HTTPS. This is important for secure cookies and redirects.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Production security settings: enable when DEBUG is False
if not DEBUG:
    # Redirect HTTP -> HTTPS
    SECURE_SSL_REDIRECT = True
    # Secure cookies
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: tell browsers to always use HTTPS (set reasonably long duration)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

ROOT_URLCONF = 'trikeGo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'trikeGo.wsgi.application'

os.environ["PGOPTIONS"] = "-c inet_family=inet"

DATABASES = {
    'default': dj_database_url.config(
        # Feel free to specify SSL requirements if needed
        conn_max_age=600,
        # ssl_require=True # Uncomment if Render DB requires SSL
    )
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# OpenRouteService API Configuration
OPENROUTESERVICE_API_KEY = os.environ.get('OPENROUTESERVICE_API_KEY', 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImIyOThlMTFhZDk5MzRmOGVhY2NmOTAxMGQzM2ZlYWJhIiwiaCI6Im11cm11cjY0In0=')

AUTH_USER_MODEL = "user.CustomUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'  
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Basic logging configuration to ensure request access logs show in the console
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'daphne': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}