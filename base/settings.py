"""
Django settings for indexer project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-=r_v_es6w6rxv42^#kc2hca6p%=fe_*cog_5!t%19zea!enlju"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Env vars
AWS_ACCESS_KEY_ID = os.environ.get("PL_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("PL_AWS_SECRET_ACCESS_KEY")
CELERY_BROKER_URL = os.environ.get("PL_CELERY_BROKER_URL")
POSTGRES_DB = os.environ.get("PL_POSTGRES_DB")
POSTGRES_HOST = os.environ.get("PL_POSTGRES_HOST", None)
POSTGRES_PASS = os.environ.get("PL_POSTGRES_PASS", None)
POSTGRES_PORT = os.environ.get("PL_POSTGRES_PORT", None)
POSTGRES_READONLY_PASS = os.environ.get("PL_POSTGRES_READONLY_PASS", None)
POSTGRES_READONLY_USER = os.environ.get("PL_POSTGRES_READONLY_USER", None)
POSTGRES_USER = os.environ.get("PL_POSTGRES_USER", None)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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

ROOT_URLCONF = "indexer.urls"

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

WSGI_APPLICATION = "indexer.wsgi.application"


###############################################################################
# DATABASE CONFIGS
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
###############################################################################
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": POSTGRES_DB,
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASS,
        "HOST": POSTGRES_HOST,
        "PORT": POSTGRES_PORT,
    },
    "default_readonly": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
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

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
