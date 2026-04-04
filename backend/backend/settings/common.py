from pathlib import Path
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

DEPENDENCIES_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
    'django.contrib.gis'
]

WAGTAIL_APPS = [
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail',
    'wagtail.contrib.settings',

    'taggit',
    'modelcluster',
    'wagtailgeowidget',
]

PROJECT_APPS = [
    'accounts',
    'farmer',
    'core',
    'cms',
    'farm',
]

ADDONS_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'leaflet',
]

INSTALLED_APPS = WAGTAIL_APPS + DEPENDENCIES_APPS + PROJECT_APPS + ADDONS_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_DIR, 'templates'),
        ],
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

WSGI_APPLICATION = 'backend.wsgi.application'

# Database config
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': 'postgres',
        'PORT': 5432,
    }
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, 'static'),
]

# STORAGE SETTINGS
AWS_ACCESS_KEY_ID = os.environ.get('STORAGE_KEY')
AWS_SECRET_ACCESS_KEY = os.environ.get('STORAGE_SECRET')
AWS_STORAGE_BUCKET_NAME = os.environ.get('STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.environ.get('STORAGE_ENDPOINT_URL')
AWS_S3_REGION_NAME = os.environ.get('STORAGE_REGION_NAME')
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_QUERYSTRING_AUTH = os.environ.get('STORAGE_QUERYSTRING_AUTH') == 'True'
AWS_DEFAULT_ACL = None
AWS_S3_FILE_OVERWRITE = False

STORAGES = {
    'default': {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Wagtail Settings
WAGTAIL_SITE_NAME = os.environ.get('WAGTAIL_SITE_NAME', 'S.A.M.V.A. Platform')

WAGTAILADMIN_BASE_URL = os.environ.get('WAGTAILADMIN_BASE_URL', 'http://localhost:8000')

WAGTAILSEARCH_BACKENDS = {
    "default": {"BACKEND": "wagtail.search.backends.database"}
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# Security settings
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# TODO : Improve this to load from .env files
import glob
def find_library(pattern):
    matches = glob.glob(pattern)
    return matches[0] if matches else None

GDAL_LIBRARY_PATH = find_library('/usr/lib/x86_64-linux-gnu/libgdal.so*')
GEOS_LIBRARY_PATH = find_library('/usr/lib/x86_64-linux-gnu/libgeos_c.so*')


# Leaflet settings
LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (4.142, -73.626),
    'DEFAULT_ZOOM': 12,
    'MAX_ZOOM': 20,
    'MIN_ZOOM': 3,
    'PLUGINS': {
        'forms': {
            'auto-include': True
        }
    }
}