"""
cid/settings.py - VERSION RENDER
Optimisé pour Render.com avec PostgreSQL Alwaysdata
"""
from pathlib import Path
import os
import sys

# ============================================================
# BASE DIR
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# FONCTION UNIQUE POUR LES VARIABLES D'ENVIRONNEMENT
# ============================================================
def get_env(key, default=None):
    """
    Priorité : 1. Variables Render, 2. .env local, 3. default
    """
    # D'abord les variables d'environnement système (Render)
    value = os.environ.get(key)
    if value is not None:
        return value
    
    # Ensuite .env pour le développement local
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.environ.get(key, default)
    except:
        return default

# ============================================================
# SÉCURITÉ
# ============================================================
SECRET_KEY = get_env('SECRET_KEY', 'django-insecure-change-me-now-12345')

# DEBUG: TRUE pour vendredi (voir les erreurs), FALSE après
DEBUG = get_env('DEBUG', 'True').lower() == 'true'

# Hosts autorisés
ALLOWED_HOSTS = get_env('ALLOWED_HOSTS', '.onrender.com,localhost,127.0.0.1').split(',')

# ============================================================
# BASE DE DONNÉES (Render + Alwaysdata)
# ============================================================
# Sur Render, on utilise DATABASE_URL, en local le .env
if 'RENDER' in os.environ or 'DATABASE_URL' in os.environ:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=get_env('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=False  # ← LE SSL EST DÉJÀ DANS L'URL
        )
    }
    print(f"✅ Base de données Render configurée: {DATABASES['default']['ENGINE']}")
else:
    # Développement local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': get_env('DB_NAME', 'cid_db'),
            'USER': get_env('DB_USER', 'postgres'),
            'PASSWORD': get_env('DB_PASSWORD', ''),
            'HOST': get_env('DB_HOST', 'localhost'),
            'PORT': get_env('DB_PORT', '5432'),
        }
    }

# ============================================================
# APPLICATIONS (identique à votre version)
# ============================================================
INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    # Apps locales
    'core',
    'beneficiaire',
    'ged',
    'messagerie',
    'mds',
    'planning',
    'AidFi',
]

# ============================================================
# MIDDLEWARE (identique)
# ============================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.authentication.middleware.ServiceSelectorMiddleware',
    #'core.authentication.middleware.AuditMiddleware',
]

# ============================================================
# AUTHENTIFICATION
# ============================================================
AUTH_USER_MODEL = 'core.User'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

AUTHENTICATION_BACKENDS = [
    'core.authentication.backends.CD13LocalBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# ============================================================
# TEMPLATES (identique)
# ============================================================
ROOT_URLCONF = 'cid.urls'
WSGI_APPLICATION = 'cid.wsgi.application'

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
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
            'libraries': {
                'ged_tags': 'ged.ged_tags',
                'permissions_tags': 'core.templatetags.permissions_tags',
            },
        },
    },
]

# ============================================================
# MOTS DE PASSE (identique)
# ============================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# INTERNATIONALISATION (identique)
# ============================================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_L10N = True
USE_I18N = True
USE_TZ = True

# ============================================================
# STATIC / MEDIA (identique)
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# SEAWEEDFS - ADAPTÉ POUR LA DÉMO / RENDER
# ============================================================

# URLs (peu importe pour le mock)
SEAWEEDFS_MASTER_URL = get_env('SEAWEEDFS_MASTER_URL', 'http://localhost:9333')
SEAWEEDFS_VOLUME_URL = get_env('SEAWEEDFS_VOLUME_URL', 'http://localhost:8080')
SEAWEEDFS_FILER_URL = get_env('SEAWEEDFS_FILER_URL', 'http://localhost:8888')

# Client intelligent
if 'RENDER' in os.environ:
    try:
        # Essayer le vrai seaweedfs-bin
        import seaweedfs_bin
        from seaweedfs_bin import SeaweedFS
        SEAWEEDFS_CLIENT = SeaweedFS(SEAWEEDFS_MASTER_URL)
        print("✅ SeaweedFS réel chargé")
    except ImportError:
        # Fallback au mock intelligent
        print("⚠️  SeaweedFS-bin non disponible, activation du MOCK INTELLIGENT")
        from ged.seaweedfs_mock import seaweedfs_client
        SEAWEEDFS_CLIENT = seaweedfs_client
else:
    # En local, utiliser le vrai ou le mock selon préférence
    from ged.seaweedfs_mock import seaweedfs_client
    SEAWEEDFS_CLIENT = seaweedfs_client
    print("✅ GED Mock activé (développement local)")

# ============================================================
# LOGGING POUR DEBUG (Vendredi uniquement)
# ============================================================
if DEBUG:
    print("=" * 60)
    print("🔍 MODE DEBUG ACTIVÉ - CONFIGURATION RENDER:")
    print(f"   Django {sys.modules['django'].__version__}")
    print(f"   Python {sys.version}")
    print(f"   Database: {DATABASES['default'].get('ENGINE', 'N/A')}")
    print(f"   Host: {DATABASES['default'].get('HOST', 'N/A')}")
    print(f"   User Model: {AUTH_USER_MODEL}")
    print("=" * 60)
    
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
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
                'level': 'DEBUG',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'WARNING',  # DEBUG pour voir les requêtes SQL
                'propagate': False,
            },
        },
    }

# ============================================================
# CONFIGURATIONS DIVERSES (identique)
# ============================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if not DEBUG:
    # Sécurité en production
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    # En debug, désactiver certaines sécurités pour le développement
    print("⚠️  MODE DEBUG: certaines sécurités sont désactivées")
