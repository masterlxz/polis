"""Configurações do polis.

Tudo que varia entre ambientes vem de variáveis de ambiente (ver `.env.example`).
Falha fechada: sem `DJANGO_SECRET_KEY` o projeto não sobe, e `DEBUG` é falso
a menos que `DJANGO_DEBUG` seja definido explicitamente.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("A variável de ambiente DJANGO_SECRET_KEY é obrigatória.")

DEBUG = os.environ.get("DJANGO_DEBUG", "").lower() in {"1", "true"}

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "config.apps.PolisAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "apps.sources",
    "apps.elections",
    "apps.legislature",
    "apps.operators",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "polis"),
        "USER": os.environ.get("POSTGRES_USER", "polis"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Nome que o app autenticador mostra para o TOTP (ADR 0019).
OTP_TOTP_ISSUER = "polis"

# Normalizador de cada conjunto coletado, que o agendador chama depois de cada coleta
# bem-sucedida (ADR 0023): "fonte/conjunto" -> caminho da função `normalize_latest(dataset)`.
# Fica aqui para `apps.sources` não importar os apps que normalizam.
NORMALIZERS = {
    "tse/consulta-cand-2026": "apps.elections.normalization.normalize_latest",
    "camara/deputados": "apps.legislature.normalization.normalize_latest",
    "senado/senadores": "apps.legislature.senate_normalization.normalize_latest",
    "senado/votacoes": "apps.legislature.senate_voting_normalization.normalize_latest",
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Onde o `collectstatic` junta os arquivos do admin para o proxy servir (imagem de produção).
STATIC_ROOT = BASE_DIR / "staticfiles"

# Produção atrás de um proxy com TLS (ADR 0011). Tudo por variável de ambiente e, sem variável,
# o comportamento é o de desenvolvimento. Valor inválido recusa subir, como a SECRET_KEY vazia.
_LIGADO = {"1", "true"}
_HTTPS = os.environ.get("DJANGO_HTTPS", "").lower() in _LIGADO
SESSION_COOKIE_SECURE = _HTTPS
CSRF_COOKIE_SECURE = _HTTPS

# Só com o proxy na frente: ele precisa SOBRESCREVER `X-Forwarded-Proto` e ser o único caminho
# até o Django, senão um cliente forja o cabeçalho e finge falar HTTPS.
SECURE_PROXY_SSL_HEADER = None
if os.environ.get("DJANGO_BEHIND_PROXY", "").lower() in _LIGADO:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS "gruda" no navegador: fica 0 (desligado) até o dono decidir.
_HSTS = os.environ.get("DJANGO_HSTS_SECONDS", "0")
if not _HSTS.isascii() or not _HSTS.isdigit():
    raise ImproperlyConfigured("DJANGO_HSTS_SECONDS deve ser um inteiro não negativo.")
SECURE_HSTS_SECONDS = int(_HSTS)

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]
if not all(o.startswith(("https://", "http://")) for o in CSRF_TRUSTED_ORIGINS):
    raise ImproperlyConfigured(
        "DJANGO_CSRF_TRUSTED_ORIGINS: cada origem precisa começar com https:// ou http://."
    )

# Webhook do alerta ativo (Sessão 76). Vazio = alerta desligado. A URL costuma carregar o segredo
# (token, tópico), então a mensagem de erro não a mostra.
ALERT_WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
if ALERT_WEBHOOK_URL:
    _alert_url = urlsplit(ALERT_WEBHOOK_URL)
    if _alert_url.scheme != "https" or not _alert_url.hostname:
        raise ImproperlyConfigured(
            "ALERT_WEBHOOK_URL: precisa ser uma URL https com host (o valor não é mostrado)."
        )

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
