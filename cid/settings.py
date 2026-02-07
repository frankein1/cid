"""
cid/settings.py
Django settings for cid project.
Version optimisée et structurée pour le module CORE et les futures apps métier.
"""
from decouple import config, Csv
from dotenv import load_dotenv
from pathlib import Path
import os
import sys


# ============================================================
# BASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# Récupère la valeur de 'SECRET_KEY' dans .env
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# Récupère la valeur de 'DEBUG' et la convertit en booléen (si non spécifié, False par défaut)
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']  # En dev : accepter localhost, 127.0.0.1 EN PROD : CHOISIR LES HOTES REELLEMENT VALIDES

# Configuration de la base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # PostgreSQL features
    'django.contrib.postgres',

    # Apps locales
    'core', # coeur de l application 
    'beneficiaire', #geston des beneficiaires
    'ged', #Gestion Electronique des documents 
    'messagerie', #messagerie
    'mds', #Maison Departementale de Solidarite
    'planning', # plannings
    'AidFi',#Aides Financières
    #    'protection_enfance.apps.ProtectionEnfanceConfig',
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Middlewares SI DITAS
    'core.authentication.middleware.ServiceSelectorMiddleware',
    'core.authentication.middleware.AuditMiddleware',
]


# ============================================================
# AUTHENTIFICATION / UTILISATEURS
# ============================================================

AUTH_USER_MODEL = 'core.User'

# 1. URL de la page de connexion : Indique à Django l'URL REELLE pour se connecter.
LOGIN_URL = '/login/'

# 2. Redirection après une connexion réussie (sans le paramètre ?next=)
LOGIN_REDIRECT_URL = '/' 

# 3. Redirection après une déconnexion réussie
LOGOUT_REDIRECT_URL = '/'



AUTHENTICATION_BACKENDS = [
    # Local authentication (fallback)
    'core.authentication.backends.CD13LocalBackend',

    # Django standard
    'django.contrib.auth.backends.ModelBackend',
]


# ============================================================
# URLS / WSGI
# ============================================================

ROOT_URLCONF = 'cid.urls'
WSGI_APPLICATION = 'cid.wsgi.application'


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # Dossier templates global du projet
        'DIRS': [
            BASE_DIR / 'templates',
        ],

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
            # ================ AJOUTE CES 3 LIGNES ================
            'libraries': {
                'ged_tags': 'ged.ged_tags',
                'permissions_tags' : 'core.templatetags.permissions_tags', 
            },
            # =====================================================
            
        },
    },
]


# ============================================================
# VALIDATION MOTS DE PASSE
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
# INTERNATIONALISATION
# ============================================================

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_L10N = True
USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC / MEDIA
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================
# CONFIG SPÉCIFIQUE SI DITAS
# ============================================================

# SeaweedFS
# Utiliser config() pour lire directement le .env ou la valeur par défaut
SEAWEEDFS_MASTER_URL = config('SEAWEEDFS_MASTER_URL', default='http://localhost:9333')
SEAWEEDFS_VOLUME_URL = config('SEAWEEDFS_VOLUME_URL', default='http://localhost:8080')
SEAWEEDFS_FILER_URL = config('SEAWEEDFS_FILER_URL', default='http://localhost:8888')

# Upload max (10 Mo)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# ============================================================
# OPTIONS DEV / LOGS
# ============================================================

# Afficher SQL en debug si souhaité
if DEBUG and os.environ.get("SHOW_SQL") == "1":
    LOGGING = {
        'version': 1,
        'handlers': {
            'console': {'class': 'logging.StreamHandler'},
        },
        'loggers': {
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        },
    }

# ============================================================
# Ajouté pour supprimer le warning W042 et utiliser un type de clé primaire moderne
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# ============================================================


# ============================================================
# SÉCURITÉ AUTOMATIQUE
# ============================================================

if not DEBUG:
    # On force la sécurité des cookies car on suppose que la prod est en HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    # Si vous passez derrière un reverse-proxy (Nginx) pour le HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
