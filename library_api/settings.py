"""Settings for the JSON-only library API."""

SECRET_KEY = "desenvolvimento-local-troque-esta-chave-em-producao"
DEBUG = False
ALLOWED_HOSTS = ["*"]

ROOT_URLCONF = "library_api.urls"
WSGI_APPLICATION = "library_api.wsgi.application"

INSTALLED_APPS = [
    "library.apps.LibraryConfig",
]

# The API has no sessions, admin site, HTML views, or template rendering.
MIDDLEWARE = []
TEMPLATES = []

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "db.sqlite3",
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
APPEND_SLASH = False
