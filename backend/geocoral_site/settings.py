"""
Django settings for the GeoCoral backend.

Database: supports either SQLite + SpatiaLite or PostgreSQL + PostGIS
for local development, and PostgreSQL + PostGIS in production, matching
the Hardware and Software Specifications section of the GeoCoral
capstone proposal. Switch via the GEOCORAL_DB environment variable.
"""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

# The ML training project (config.py, training/, data_prep/) lives one
# directory up from this Django project, so its modules — especially
# training.predict — can be imported directly for inference.
ML_PROJECT_ROOT = BASE_DIR.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-before-deploying",  # override via env var in production
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,""*","mia-typical-subsidiaries-vaccine.trycloudflare.com").split(",")
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,mia-typical-subsidiaries-vaccine.trycloudflare.com"
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",       # GeoDjango — spatial model fields + admin map widgets
    "rest_framework",
    "corsheaders",
    "monitoring",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "geocoral_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "monitoring.context_processors.role_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "geocoral_site.wsgi.application"


# ----------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------
# GEOCORAL_DB=postgis (recommended, incl. local dev on Windows — see
#   backend/README.md) -> PostgreSQL + PostGIS, matching the paper's
#   Hardware and Software Specifications for both local dev and the
#   deployed Render/PythonAnywhere server.
# GEOCORAL_DB=spatialite (default) -> SQLite + SpatiaLite. Zero extra
#   services to run, but GDAL/SpatiaLite setup on Windows can be fiddly
#   (see README) — prefer postgis locally on Windows unless you already
#   have GDAL working.
# ----------------------------------------------------------------------
if os.environ.get("GEOCORAL_DB") == "postgis":
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": os.environ.get("DB_NAME", "geocoral"),
            "USER": os.environ.get("DB_USER", "geocoral"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    # Django needs the exact path to the SpatiaLite SQLite extension.
    # The filename/location varies by OS and install method — see
    # backend/README.md for how to find it on your machine.
    SPATIALITE_LIBRARY_PATH = os.environ.get("SPATIALITE_LIBRARY_PATH", "mod_spatialite")

# GeoDjango needs the GDAL and GEOS libraries whichever database is used.
# Each developer sets these in their own environment (see start.ps1);
# never hardcode a machine-specific path such as C:\OSGeo4W\... here.
GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH") or None
GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH") or None

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded coral photos are stored here and served from MEDIA_URL.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ----------------------------------------------------------------------
# Django REST Framework
# ----------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# The mobile-responsive web upload form (see paper's Image submission
# interface spec) and any separate frontend need CORS access to the API.
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")


# ----------------------------------------------------------------------
# GeoCoral ML model integration
# ----------------------------------------------------------------------
# Path to the trained classifier checkpoint (see training/train.py in
# the ML project).

# monitoring/ml_service.py loads this once at first use.

GEOCORAL_MODEL_PATH = os.environ.get(
      "GEOCORAL_MODEL_PATH",
      str(ML_PROJECT_ROOT / "saved_models" / "geocoral_resnet50_best.keras"),
  )

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "monitoring:role_home"
# CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS","","https://mia-typical-subsidiaries-vaccine.trycloudflare.com").split(",") if o]

CSRF_TRUSTED_ORIGINS = [
    "https://*.trycloudflare.com",
]