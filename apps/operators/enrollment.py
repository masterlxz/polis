"""Segundo fator do operador: dispositivo TOTP e códigos de recuperação (ADR 0019).

Nada de criptografia própria: a chave do TOTP e os códigos vêm do `django-otp`. Eles ficam
em texto no banco (ver a nota de implementação do ADR 0019), então o backup precisa ser cifrado.
"""

from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

DEFAULT_RECOVERY_CODES = 10


def enroll(user, codes):
    """Cria o dispositivo TOTP e `codes` códigos de recuperação; devolve ambos."""
    device = TOTPDevice.objects.create(user=user, name="totp", confirmed=True)
    recovery = StaticDevice.objects.create(user=user, name="recuperacao", confirmed=True)
    tokens = [StaticToken.random_token() for _ in range(codes)]
    StaticToken.objects.bulk_create([StaticToken(device=recovery, token=t) for t in tokens])
    return device, tokens


def render(device, tokens):
    """Texto para o terminal. O segredo aparece só aqui, uma vez, e nunca vai para log."""
    linhas = [
        "Cadastre esta URL no app autenticador. Ela aparece só desta vez:",
        device.config_url,
        "",
        "Códigos de recuperação (guarde fora do banco; cada um vale uma vez):",
        *(f"  {token}" for token in tokens),
    ]
    return "\n".join(linhas)
