"""
Django settings for project.
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
import dj_database_url

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-some-default-key-for-dev')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Add current directory to Python path
sys.path.insert(0, str(BASE_DIR))

# Get Railway URL for allowed hosts and CSRF
RAILWAY_PUBLIC_URL = os.environ.get('RAILWAY_PUBLIC_URL', '')
RAILWAY_STATIC_URL = os.environ.get('RAILWAY_STATIC_URL', '')
RAILWAY_PUBLIC_DOMAIN = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')

# Base allowed hosts
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Add Railway domain to allowed hosts if available
if RAILWAY_PUBLIC_DOMAIN and RAILWAY_PUBLIC_DOMAIN not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RAILWAY_PUBLIC_DOMAIN)

# Add Railway health check domain
ALLOWED_HOSTS.append('healthcheck.railway.app')

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

# Also add RAILWAY_PUBLIC_DOMAIN to CSRF trusted origins
if RAILWAY_PUBLIC_DOMAIN:
    CSRF_TRUSTED_ORIGINS = CSRF_TRUSTED_ORIGINS if 'CSRF_TRUSTED_ORIGINS' in locals() else []
    CSRF_TRUSTED_ORIGINS.extend([
        f"https://{RAILWAY_PUBLIC_DOMAIN}",
        f"http://{RAILWAY_PUBLIC_DOMAIN}",
    ])


# Telegram API Token from environment
TELEGRAM_API_TOKEN = os.environ.get('BOT_TOKEN', "8102516142:AAFTsVXXujHHKoX2KZGqZXBHPBznfgh7kg0")
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
    'core.health_middleware.HealthCheckMiddleware',  # Health middleware
    'core.template_middleware.TemplateDebugMiddleware',  # Template debug middleware
    'core.template_debug_middleware.TemplateRenderDebugMiddleware',  # Template render debugging
]

# Ensure database connections are released in long-running apps
# This prevents database connection exhaustion in Railway
CONN_MAX_AGE = 60  # recommended for Railway's ephemeral builds

# Setup URL routing
ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            # Add additional template directories for Railway
            os.path.join(BASE_DIR, 'templates/admin_panel'),
            os.path.join(BASE_DIR, '.'),  # Root directory for direct index.html serving
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Add custom context processor for template debugging
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# Database configuration - use database URL if available, otherwise fallback to specific settings
if 'DATABASE_URL' in os.environ:
    # For Railway or any environment that uses DATABASE_URL
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600, ssl_require=False  # 10 minutes timeout without requiring SSL
        )
    }
    print("Using DATABASE_URL connection string")
elif os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('RAILWAY_SERVICE_NAME'):
    # For Railway when DATABASE_URL is not directly available but PG variables are set
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('PGDATABASE', 'railway'),
            'USER': os.environ.get('PGUSER', 'postgres'),
            'PASSWORD': os.environ.get('PGPASSWORD', ''),
            'HOST': os.environ.get('PGHOST', 'localhost'), # Changed from postgres.railway.internal
            'PORT': os.environ.get('PGPORT', '5432'),
            'CONN_MAX_AGE': 60,  # Recommended for Railway's ephemeral builds
            'OPTIONS': {
                'connect_timeout': 10,
                'options': '-c statement_timeout=5000',  # 5s timeout for statements to avoid hanging queries
            }
        }
    }
    print(f"Using PostgreSQL connection to {os.environ.get('PGHOST', 'localhost')}")
else:
    # For local development, use SQLite by default for simplicity
    db_path = os.path.join(BASE_DIR, 'db.sqlite3')
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': db_path,
        }
    }
    print(f"Using SQLite database at {db_path}")

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    BASE_DIR,  # Serve the main directory as static files
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Ensure media directories exist with proper error handling
try:
    # Create media root if it doesn't exist
    if not os.path.exists(MEDIA_ROOT):
        os.makedirs(MEDIA_ROOT, exist_ok=True)
        # Set permissions on the media root directory
        os.chmod(MEDIA_ROOT, 0o755)
    
    # Create messages directory if it doesn't exist
    messages_dir = os.path.join(MEDIA_ROOT, 'messages')
    if not os.path.exists(messages_dir):
        os.makedirs(messages_dir, exist_ok=True)
        # Set permissions on the messages directory
        os.chmod(messages_dir, 0o755)
except Exception as e:
    import sys
    print(f"Warning: Error creating media directories: {str(e)}", file=sys.stderr)
    # Continue execution rather than failing - the application can still function
    # and our middleware will handle missing files gracefully

# Custom storage settings for Railway deployment
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
if not DEBUG and RAILWAY_PUBLIC_DOMAIN:
    # Use custom storage for Railway deployment
    DEFAULT_FILE_STORAGE = 'core.storage.RailwayMediaStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Whitenoise static file handling
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Bot settings
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Check if running on Railway
IS_RAILWAY = bool(os.environ.get('RAILWAY_SERVICE_NAME'))
PUBLIC_URL = os.environ.get('PUBLIC_URL', '')

if IS_RAILWAY and PUBLIC_URL:
    print(f"Bot will use PUBLIC_URL: {PUBLIC_URL}")
    # Set Railway-specific settings if needed
    CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if '.' in host]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False  # Railway already handles HTTPS

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'template_debug': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'template_middleware': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Session settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_COOKIE_SECURE = bool(os.environ.get('RAILWAY_SERVICE_NAME'))  # Use secure cookies on Railway
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True  # Always save session on every request to prevent data loss

# Ensure logs directory exists
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)