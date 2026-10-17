from pathlib import Path
import os
from celery.schedules import crontab

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
    'sensors',
    'predictions',
    'assistant',
]

ADDONS_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'leaflet',
    'corsheaders',
    'django_celery_results',
]

INSTALLED_APPS = WAGTAIL_APPS + DEPENDENCIES_APPS + PROJECT_APPS + ADDONS_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
    'core.middleware.AdminTimeZoneMiddleware',
]

ROOT_URLCONF = 'backend.urls'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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
# Dates are stored and served by the API in UTC; only the Django admin shows them in local time.
ADMIN_TIME_ZONE = 'America/Bogota'
ADMIN_TIME_ZONE_PATH = '/django-admin/'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, 'static'),
]


# Wagtail Settings
WAGTAIL_SITE_NAME = os.environ.get('WAGTAIL_SITE_NAME', 'S.A.M.V.A. Platform')

WAGTAILADMIN_BASE_URL = os.environ.get('WAGTAILADMIN_BASE_URL', 'http://localhost:8000')

WAGTAILSEARCH_BACKENDS = {
    "default": {"BACKEND": "wagtail.search.backends.database"}
}

AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {
        "sensor_ingest": "120/min",
        # Each chat turn runs a local LLM on the server's CPU for several seconds.
        "assistant_chat": "20/min",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SAMVA Platform API",
    "DESCRIPTION": "API de la plataforma SAMVA",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
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

# Celery
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

CELERY_BEAT_SCHEDULE = {
    'what_time_is_it': {
        'task': 'core.tasks.what_time_is_it',
        'schedule': crontab(minute='*/5'),
    },
    'poll_weather_stations': {
        'task': 'sensors.tasks.poll_weather_stations',
        'schedule': crontab(minute='*/5'),
    },
}


# Weather Station Provider Configuration
WEATHERLINK_BASE_URL='https://api.weatherlink.com/v2'

# MQTT ingest (LoRaWAN uplinks), consumed by the `mqtt_ingest` command.
# `ttn` subscribes to The Things Network, where the real nodes arrive already decoded;
# `local` subscribes to the compose Mosquitto, where only the simulator publishes.
# An unknown source or a `ttn` profile without credentials is rejected by the command
# itself, so a typo stops the subscriber instead of every web and Celery process.
def mqtt_source(environ):
    return environ.get('MQTT_SOURCE', 'local').strip().lower()


def mqtt_ingest_config(source, environ):
    if source == 'ttn':
        # TTN's MQTT integration page shows the username as `<app>@ttn`, so that is what
        # gets pasted; the tenant suffix is added below and must not appear twice.
        app_id = environ.get('TTN_APP_ID', '').strip().removesuffix('@ttn')
        return {
            'source': 'ttn',
            'app_id': app_id,
            'host': environ.get('TTN_MQTT_HOST', 'au1.cloud.thethings.network'),
            'port': int(environ.get('TTN_MQTT_PORT', '8883')),
            'tls': True,
            'username': f'{app_id}@ttn',
            'password': environ.get('TTN_API_KEY', ''),
            'topic': f'v3/{app_id}@ttn/devices/+/up',
            'client_id': environ.get('MQTT_CLIENT_ID', 'samva-mqtt-ingest'),
        }

    return {
        'source': 'local',
        'host': environ.get('MQTT_HOST', 'mqtt'),
        'port': int(environ.get('MQTT_PORT', '1883')),
        'tls': False,
        'username': '',
        'password': '',
        'topic': 'v3/+/devices/+/up',
        'client_id': environ.get('MQTT_CLIENT_ID', 'samva-mqtt-ingest'),
    }


MQTT_SOURCE = mqtt_source(os.environ)
MQTT_INGEST = mqtt_ingest_config(MQTT_SOURCE, os.environ)


# Assistant (chatbot): a local Ollama server running a tool-calling model.
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://ollama:11434').rstrip('/')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2:3b')
# On CPU the first turn also loads the model into memory, which alone can take ~20 s.
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get('OLLAMA_TIMEOUT_SECONDS', '120'))
OLLAMA_KEEP_ALIVE = os.environ.get('OLLAMA_KEEP_ALIVE', '30m')
