import os
from django.conf import settings

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    settings.BASE_DOMAIN,
]

ALLOWED_HOSTS.extend([
    f"{language_code}.{settings.BASE_DOMAIN}"
    for language_code, language in settings.LANGUAGES
])

CSRF_TRUSTED_ORIGINS = [
    f"http://localhost",
    f"http://*.localhost",
    f"https://{settings.BASE_DOMAIN}",
    f"https://*.{settings.BASE_DOMAIN}",
]

DEBUG = True

SERVER_EMAIL = 'info@arguman.org'

DEFAULT_FROM_EMAIL = 'info@arguman.org'
POSTMARK_TOKEN = "xyz"
POSTMARK_API_URL = "https://api.postmarkapp.com/email"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'arguman',
        'USER': os.getenv('POSTGRES_USER', 'arguman'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'arguman'),
        'HOST': os.getenv('POSTGRES_HOST', 'db'),
        'PORT': os.getenv('POSTGRES_PORT', 5432),
    }
}

MONGODB_USERNAME = os.getenv('MONGODB_USERNAME', 'arguman')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD', 'arguman')

# CACHES = {
#     "default": {
#         "BACKEND": "redis_cache.cache.RedisCache",
#         "LOCATION": "127.0.0.1:6379:1"
#     }
# }
