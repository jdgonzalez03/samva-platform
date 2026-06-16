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