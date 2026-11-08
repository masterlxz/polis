import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

SENHA_DO_ADMIN_DE_TESTE = "uma-senha-longa-so-de-teste-9731"


@pytest.fixture
def admin_client(db):
    """Cliente de superusuário que passou pelo TOTP, como o admin real exige (ADR 0019).

    Sobrescreve o `admin_client` do pytest-django, que usa `force_login` (só senha)
    e seria recusado pelo `PolisAdminSite`.
    """
    usuario = get_user_model().objects.create_superuser(
        "admin-de-teste", password=SENHA_DO_ADMIN_DE_TESTE
    )
    dispositivo = TOTPDevice.objects.create(user=usuario, name="teste", confirmed=True)
    codigo = totp(
        dispositivo.bin_key, dispositivo.step, dispositivo.t0, dispositivo.digits, dispositivo.drift
    )
    client = Client()
    resposta = client.post(
        reverse("admin:login"),
        {
            "username": usuario.get_username(),
            "password": SENHA_DO_ADMIN_DE_TESTE,
            "otp_device": dispositivo.persistent_id,
            "otp_token": f"{codigo:0{dispositivo.digits}d}",
        },
    )
    assert resposta.status_code == 302, "o login com TOTP do fixture falhou"
    return client
