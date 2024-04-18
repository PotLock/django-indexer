"""
Django settings for indexer project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
import ssl
from distutils.util import strtobool
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: update before prod release
SECRET_KEY = "django-insecure-=r_v_es6w6rxv42^#kc2hca6p%=fe_*cog_5!t%19zea!enlju"

ALLOWED_HOSTS = [
    "ec2-54-89-249-195.compute-1.amazonaws.com",
    "54.89.249.195"
]

# Env vars
AWS_ACCESS_KEY_ID = os.environ.get("PL_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("PL_AWS_SECRET_ACCESS_KEY")
CELERY_BROKER_HOST = os.environ.get("PL_CELERY_BROKER_HOST")
CELERY_RESULT_HOST = os.environ.get("PL_CELERY_RESULT_HOST")
DEBUG = strtobool(os.environ.get("PL_DEBUG", "False"))
ENVIRONMENT = os.environ.get("PL_ENVIRONMENT", "local")
POSTGRES_DB = os.environ.get("PL_POSTGRES_DB")
POSTGRES_HOST = os.environ.get("PL_POSTGRES_HOST", None)
POSTGRES_PASS = os.environ.get("PL_POSTGRES_PASS", None)
POSTGRES_PORT = os.environ.get("PL_POSTGRES_PORT", None)
POSTGRES_READONLY_PASS = os.environ.get("PL_POSTGRES_READONLY_PASS", None)
POSTGRES_READONLY_USER = os.environ.get("PL_POSTGRES_READONLY_USER", None)
POSTGRES_USER = os.environ.get("PL_POSTGRES_USER", None)
REDIS_HOST = os.environ.get("PL_REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("PL_REDIS_PORT", 6379)

BLOCK_SAVE_HEIGHT = os.environ.get("BLOCK_SAVE_HEIGHT")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "celery",
    "api",
    "accounts",
    "activities",
    "donations",
    "indexer_app",
    "lists",
    "pots",
    "tokens",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "base.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "base.wsgi.application"

# REDIS / CACHE CONFIGS

REDIS_SCHEMA = (
    "redis://" if ENVIRONMENT == "local" else "rediss://"
)  # rediss denotes SSL connection
REDIS_BASE_URL = f"{REDIS_SCHEMA}{REDIS_HOST}:{REDIS_PORT}"

# Append SSL parameters as query parameters in the URL
SSL_QUERY = "?ssl_cert_reqs=CERT_NONE" # TODO: UPDATE ACCORDING TO ENV (prod should require cert)

CELERY_BROKER_URL = f"{REDIS_SCHEMA}{CELERY_BROKER_HOST}:{REDIS_PORT}/0{SSL_QUERY}"

CELERY_RESULT_BACKEND = f"{REDIS_SCHEMA}{CELERY_RESULT_HOST}/0{SSL_QUERY}"

# print("Broker URL:", CELERY_BROKER_URL)
# print("Result Backend:", CELERY_RESULT_BACKEND)

# hash_tag = "task_group_1"

CELERY_BROKER_TRANSPORT_OPTIONS = {
    "fanout_prefix": True,
    "fanout_patterns": True,
    "visibility_timeout": 3600,  # Adjust as necessary
    # "key_prefix": f"celery_tasks:{{{hash_tag}}}", # Add hash tag to ensure that all keys involved in the same operation are located in the same redis cluster hash slot
    # "key_prefix": f"celery_tasks:{{{hash_tag}}}"
    "ssl": True,
    # "ssl_cert_reqs": "CERT_NONE",  # No client certificate required
}

# # Add SSL configurations directly into the broker and result backend options
# CELERY_BROKER_TRANSPORT_OPTIONS['redis_backend_use_ssl'] = {
#     'ssl_cert_reqs': "CERT_NONE"
# }

# # Ensure the backend uses SSL
# CELERY_RESULT_BACKEND_OPTIONS = {
#     "ssl_cert_reqs": "CERT_NONE",
#     "ssl": True,
# }

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"{REDIS_BASE_URL}/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SSL": True,
            "KEY_PREFIX": "django_cache",
            # "ssl_cert_reqs": "CERT_NONE",
        },
    }
}


###############################################################################
# DATABASE CONFIGS
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
###############################################################################
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASS,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
    },
    "default_readonly": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_READONLY_USER,
        "PASSWORD": POSTGRES_READONLY_PASS,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, "static")
print("static root: ", STATIC_ROOT)
STATICFILES_DIRS = [os.path.join(BASE_DIR, "assets")]
STATIC_URL = "/static/"
STATICFILES_LOCATION = "static"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
