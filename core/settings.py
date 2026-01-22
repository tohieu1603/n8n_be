"""
Django settings for ImageGen API.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-change-in-production")

DEBUG = os.getenv("DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Application definition
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "corsheaders",
    "apps.users",
    "apps.auth",
    "apps.keys",
    "apps.billing",
    "apps.chat",
    "apps.usage",
    "apps.blog",
    "apps.generate",
    "apps.convert",
    "apps.admin",
    "apps.workflow",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_DATABASE", "imagegen"),
        "USER": os.getenv("DB_USERNAME", "imagegen"),
        "PASSWORD": os.getenv("DB_PASSWORD", "imagegen123"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# Custom user model
AUTH_USER_MODEL = "users.User"

# CORS
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
).split(",")
CORS_ALLOW_CREDENTIALS = True

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# API Key Settings
API_KEY_PEPPER = os.getenv("API_KEY_PEPPER", "default-api-key-pepper-change-in-production")
API_KEY_ENCRYPTION_KEY = os.getenv("API_KEY_ENCRYPTION_KEY", "default-encryption-key-32-bytes!")

# External APIs
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
KIE_API_KEY = os.getenv("KIE_API_KEY", "")
SEPAY_API_KEY = os.getenv("SEPAY_API_KEY", "")

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# LLM Provider selection: "kie" or "deepseek"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "kie")

# n8n Workflow Automation
N8N_URL = os.getenv("N8N_URL", "http://localhost:5678")  # Internal API calls
N8N_PUBLIC_URL = os.getenv("N8N_PUBLIC_URL", os.getenv("N8N_URL", "http://localhost:5678"))  # Public URL for frontend
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# MCP (Model Context Protocol) Configuration
MCP_SERVER_COMMAND = os.getenv("MCP_SERVER_COMMAND", "npx -y n8n-mcp").split()
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Email
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@imagegen.ai")

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Server
SERVER_PORT = int(os.getenv("PORT", "4000"))

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        # MCP and tool calling debug logging
        "agents.mcp": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "agents.tools": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "apps.chat": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
