from .common import *

DEBUG = True

# Hosts
ALLOWED_HOSTS = ['*']

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# CSRF
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
]

# Celery config
CELERY_BROKER_URL = 'amqp://samva_platform:samva_platform@broker:5672/'