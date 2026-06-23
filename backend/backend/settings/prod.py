from .common import *

DEBUG = False

# Hosts
ALLOWED_HOSTS = [
    'yourdomain.com',
    'www.yourdomain.com',
]

# Please add your domains
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
]

# Celery config
if os.environ.get('RABBITMQ_USER', None):
    RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
    RABBITMQ_PASSWORD = os.environ.get('RABBITMQ_PASSWORD')
    CELERY_BROKER_URL = 'amqp://{}:{}@broker:5672/'.format(RABBITMQ_USER, RABBITMQ_PASSWORD)
elif os.environ.get('RABBITMQ_URL', None):
    CELERY_BROKER_URL = os.environ.get('RABBITMQ_URL') 