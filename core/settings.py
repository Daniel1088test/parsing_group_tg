"""
Django settings for project.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-05k@-&x^t9-7@vy6v%&%9x=kp3dq#qvy1!n@&pnfn4ycc$)hxu')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Add current directory to Python path
sys.path.insert(0, str(BASE_DIR))

# Get Railway URL for allowed hosts and CSRF
RAILWAY_PUBLIC_URL = os.environ.get('RAILWAY_PUBLIC_URL', '')
RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL', '')

ALLOWED_HOSTS = [
    # Default localhost values
    'localhost', '127.0.0.1', '0.0.0.0',
    
    # Railway host names
    '.up.railway.app', '.railway.app',
    
    # Extract hostname from Railway URL if available
    *([urlparse(RAILWAY_PUBLIC_URL).netloc] if RAILWAY_PUBLIC_URL else []),
    *([urlparse(RAILWAY_STATIC_URL).netloc] if RAILWAY_STATIC_URL else []),
    
    # Any additional hosts from environment
    *(os.environ.get('ALLOWED_HOSTS', '').split(',') if os.environ.get('ALLOWED_HOSTS') else [])
]

# Handle X-Forwarded-Host and X-Forwarded-Proto headers from Railway
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Setup CSRF for Railway
if RAILWAY_PUBLIC_URL:
    public_url = urlparse(RAILWAY_PUBLIC_URL)
    CSRF_TRUSTED_ORIGINS = [
        f"https://{public_url.netloc}",
        f"http://{public_url.netloc}",
    ]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'admin_panel',
    'tg_bot',
    'core',
]

MIDDLEWARE = [
    # Health check middleware should be first to ensure health checks never fail
    'core.health_middleware.HealthCheckMiddleware',
    
    # Standard Django middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom media handling middleware
    'core.health_middleware.MediaFilesMiddleware',
]

# Ensure database connections are released in long-running apps
# This prevents database connection exhaustion in Railway
CONN_MAX_AGE = 60  # recommended for Railway's ephemeral builds

# Setup URL routing
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'core.wsgi.application'

# Database configuration 
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    print("Using DATABASE_URL for database connection")
    
    # Parse the DATABASE_URL
    from urllib.parse import urlparse
    
    db_url = urlparse(DATABASE_URL)
    db_name = db_url.path[1:]  # Remove leading slash
    username = db_url.username
    password = db_url.password
    host = db_url.hostname
    port = db_url.port
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': username,
            'PASSWORD': password,
            'HOST': host,
            'PORT': port,
            'CONN_MAX_AGE': CONN_MAX_AGE,
            'OPTIONS': {
                'sslmode': 'require' if 'railway.app' in host else 'prefer'
            },
        }
    }
else:
    print("Using SQLite database as fallback")
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
LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kiev'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []

# Only add static directory if it actually exists
if os.path.exists(os.path.join(BASE_DIR, 'static')):
    STATICFILES_DIRS.append(os.path.join(BASE_DIR, 'static'))

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login/logout URLs
LOGIN_URL = '/admin_panel/login/'
LOGIN_REDIRECT_URL = '/admin_panel/'
LOGOUT_REDIRECT_URL = '/admin_panel/login/'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'middleware': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'telegram_parser': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'manual_parser': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Ensure logs directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Get PUBLIC_URL for configuration
# The parser and bot will use this to determine their URLs
PUBLIC_URL = os.environ.get('PUBLIC_URL', os.environ.get('RAILWAY_PUBLIC_URL', ''))
if PUBLIC_URL:
    print(f"Bot will use PUBLIC_URL: {PUBLIC_URL}")

# Check if essential directories exist
for directory in [STATIC_ROOT, MEDIA_ROOT, os.path.join(MEDIA_ROOT, 'messages')]:
    os.makedirs(directory, exist_ok=True)