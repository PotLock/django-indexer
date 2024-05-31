"""
Django settings for indexer project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import logging
import os
import ssl
from distutils.util import strtobool
from pathlib import Path

import boto3
import sentry_sdk

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: update before prod release
SECRET_KEY = "django-insecure-=r_v_es6w6rxv42^#kc2hca6p%=fe_*cog_5!t%19zea!enlju"

ALLOWED_HOSTS = ["ec2-100-27-57-47.compute-1.amazonaws.com", "127.0.0.1"]

# Env vars
AWS_ACCESS_KEY_ID = os.environ.get("PL_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("PL_AWS_SECRET_ACCESS_KEY")
# CACHALOT_ENABLED = strtobool(os.environ.get("PL_CACHALOT_ENABLED", "False"))
# CACHALOT_TIMEOUT = os.environ.get("PL_CACHALOT_TIMEOUT")
COINGECKO_API_KEY = os.environ.get("PL_COINGECKO_API_KEY")
DEBUG = strtobool(os.environ.get("PL_DEBUG", "False"))
ENVIRONMENT = os.environ.get("PL_ENVIRONMENT", "local")
LOG_LEVEL = os.getenv("PL_LOG_LEVEL", "INFO").upper()
POSTGRES_DB = os.environ.get("PL_POSTGRES_DB")
POSTGRES_HOST = os.environ.get("PL_POSTGRES_HOST", None)
POSTGRES_PASS = os.environ.get("PL_POSTGRES_PASS", None)
POSTGRES_PORT = os.environ.get("PL_POSTGRES_PORT", None)
POSTGRES_READONLY_PASS = os.environ.get("PL_POSTGRES_READONLY_PASS", None)
POSTGRES_READONLY_USER = os.environ.get("PL_POSTGRES_READONLY_USER", None)
POSTGRES_USER = os.environ.get("PL_POSTGRES_USER", None)
REDIS_HOST = os.environ.get("PL_REDIS_HOST", "localhost")
REDIS_PORT = os.environ.get("PL_REDIS_PORT", 6379)
SENTRY_DSN = os.environ.get("PL_SENTRY_DSN")

POTLOCK_TLA = "potlock.testnet" if ENVIRONMENT == "testnet" else "potlock.near"

BLOCK_SAVE_HEIGHT = os.environ.get("BLOCK_SAVE_HEIGHT")

COINGECKO_URL = (
    "https://pro-api.coingecko.com/api/v3"
    if COINGECKO_API_KEY
    else "https://api.coingecko.com/api/v3"
)
# Number of hours around a given timestamp for querying historical prices
HISTORICAL_PRICE_QUERY_HOURS = 24

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    # "cachalot",
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

DEFAULT_PAGE_SIZE = 30

REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": DEFAULT_PAGE_SIZE,
}


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

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
]

# REDIS / CACHE CONFIGS

REDIS_SCHEMA = (
    "redis://" if ENVIRONMENT == "local" else "rediss://"
)  # rediss denotes SSL connection
REDIS_BASE_URL = f"{REDIS_SCHEMA}{REDIS_HOST}:{REDIS_PORT}"
DJANGO_CACHE_URL = f"{REDIS_BASE_URL}/2"

# Append SSL parameters as query parameters in the URL
SSL_QUERY = "?ssl_cert_reqs=CERT_NONE"  # TODO: UPDATE ACCORDING TO ENV (prod should require cert)

CELERY_BROKER_URL = f"{REDIS_BASE_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_BASE_URL}/1"


if ENVIRONMENT != "local":
    CELERY_BROKER_URL += SSL_QUERY
    CELERY_RESULT_BACKEND += SSL_QUERY


CELERY_BROKER_TRANSPORT_OPTIONS = {
    "fanout_prefix": True,
    "fanout_patterns": True,
    "visibility_timeout": 3600,  # Adjust as necessary
    # "key_prefix": f"celery_tasks:{{{hash_tag}}}", # Add hash tag to ensure that all keys involved in the same operation are located in the same redis cluster hash slot
    # "key_prefix": f"celery_tasks:{{{hash_tag}}}"
    "ssl": True,
    # "ssl_cert_reqs": "CERT_NONE",  # No client certificate required
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": DJANGO_CACHE_URL,
        "TIMEOUT": 300,  # 5 minutes
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SSL": True,
            "KEY_PREFIX": "django_cache",
            # "ssl_cert_reqs": "CERT_NONE",
        },
    }
}

# if CACHALOT_TIMEOUT:
#     CACHALOT_TIMEOUT = int(CACHALOT_TIMEOUT)
# else:
#     CACHALOT_TIMEOUT = 60 * 5  # 5 minutes

# CACHALOT_UNCACHABLE_TABLES = frozenset(("django_migrations",))


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

CACHALOT_DATABASES = {"default"}


# LOGGING

# Setting the log level from an environment variable
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, LOG_LEVEL, logging.INFO)
# print("LOG_LEVEL: ", LOG_LEVEL)

# Set log group name based on environment
log_group_name = f"django-indexer-{ENVIRONMENT}"

# Setting up the logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": log_level,
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        },
        "indexer": {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        },
        "jobs": {
            "handlers": ["console"],
            "level": log_level,
            "propagate": False,
        },
        "": {"handlers": ["console"], "level": log_level},  # root logger
    },
}

# Adding Watchtower logging handler for non-local environments
if ENVIRONMENT != "local":
    AWS_REGION_NAME = "us-east-1"
    boto3_logs_client = boto3.client("logs", region_name=AWS_REGION_NAME)
    LOGGING["handlers"]["watchtower"] = {
        "class": "watchtower.CloudWatchLogHandler",
        "boto3_client": boto3_logs_client,
        "log_group_name": log_group_name,
        "formatter": "standard",
        "level": log_level,
    }
    LOGGING["loggers"][""]["handlers"].append("watchtower")
    LOGGING["loggers"]["django"]["handlers"].append("watchtower")
    LOGGING["loggers"]["indexer"]["handlers"].append("watchtower")
    LOGGING["loggers"]["jobs"]["handlers"].append("watchtower")

# log_level = getattr(logging, LOG_LEVEL, logging.INFO)
# print("LOG_LEVEL: ", LOG_LEVEL)
# # print("log_level: ", log_level)

# if ENVIRONMENT != "local":
#     AWS_REGION_NAME = "us-east-1"
#     boto3_logs_client = boto3.client("logs", region_name=AWS_REGION_NAME)


# LOGGING = {
#     "version": 1,
#     "disable_existing_loggers": False,
#     "root": {
#         "level": log_level,
#         # Adding the watchtower handler here causes all loggers in the project that
#         # have propagate=True (the default) to send messages to watchtower. If you
#         # wish to send only from specific loggers instead, remove "watchtower" here
#         # and configure individual loggers below.
#         # "handlers": ["watchtower", "console"],
#         "handlers": ["console"],
#     },
#     "handlers": {
#         "console": {
#             "class": "logging.StreamHandler",
#         },
#         # "watchtower": {
#         #     "class": "watchtower.CloudWatchLogHandler",
#         #     "boto3_client": boto3_logs_client,
#         #     "log_group_name": "django-indexer",
#         #     # Decrease the verbosity level here to send only those logs to watchtower,
#         #     # but still see more verbose logs in the console. See the watchtower
#         #     # documentation for other parameters that can be set here.
#         #     "level": log_level,
#         # },
#     },
#     "loggers": {
#         # In the debug server (`manage.py runserver`), several Django system loggers cause
#         # deadlocks when using threading in the logging handler, and are not supported by
#         # watchtower. This limitation does not apply when running on production WSGI servers
#         # (gunicorn, uwsgi, etc.), so we recommend that you set `propagate=True` below in your
#         # production-specific Django settings file to receive Django system logs in CloudWatch.
#         "django": {"level": log_level, "handlers": ["console"], "propagate": False}
#         # Add any other logger-specific configuration here.
#     },
# }

# if ENVIRONMENT != "local":
#     LOGGING["handlers"]["watchtower"] = {
#         "class": "watchtower.CloudWatchLogHandler",
#         "boto3_client": boto3_logs_client,
#         "log_group_name": "django-indexer",
#         # Decrease the verbosity level here to send only those logs to watchtower,
#         # but still see more verbose logs in the console. See the watchtower
#         # documentation for other parameters that can be set here.
#         "level": log_level,
#     }

#     LOGGING["root"]["handlers"].append("watchtower")

sentry_sdk.init(
    environment=ENVIRONMENT,
    dsn=SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


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
# print("static root: ", STATIC_ROOT)
STATICFILES_DIRS = [os.path.join(BASE_DIR, "assets")]
STATIC_URL = "/static/"
STATICFILES_LOCATION = "static"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
