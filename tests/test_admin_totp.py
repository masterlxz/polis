"""O admin só aceita operador verificado por TOTP (ADR 0019, decisões 2 e 3)."""

import pytest
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

SENHA = "uma-senha-longa-so-de-teste-9731"
ADMIN_INDEX = "/admin/"
ADMIN_LISTA_FONTES = "/admin/sources/source/"

pytestmark = pytest.mark.django_db


def _operador(**extra):
    campos = {"is_staff": True, **extra}
    return get_user_model().objects.create_user("operador", password=SENHA, **campos)


def _dispositivo(usuario):
    return TOTPDevice.objects.create(user=usuario, name="celular", confirmed=True)


def _token_valido(dispositivo, deriva=0):
    codigo = totp(
        dispositivo.bin_key,
        dispositivo.step,
        dispositivo.t0,
        dispositivo.digits,
        dispositivo.drift + deriva,
    )
    return f"{codigo:0{dispositivo.digits}d}"


def _token_invalido(dispositivo):
    aceitos = {_token_valido(dispositivo, d) for d in range(-dispositivo.tolerance - 1, 3)}
    candidato = 0
    while f"{candidato:0{dispositivo.digits}d}" in aceitos:
        candidato += 1
    return f"{candidato:0{dispositivo.digits}d}"


def _entrar(client, usuario, dispositivo, token):
    dados = {
        "username": usuario.get_username(),
        "password": SENHA,
        "otp_device": dispositivo.persistent_id if dispositivo else "",
        "otp_token": token,
        "next": ADMIN_INDEX,
    }
    return client.post(reverse("admin:login"), dados)


def _admin_acessivel(client):
    return client.get(ADMIN_INDEX).status_code == 200


def test_anonimo_e_enviado_ao_login(client):
    resposta = client.get(ADMIN_INDEX)
    assert resposta.status_code == 302
    assert "/admin/login/" in resposta["Location"]


def test_senha_certa_sem_dispositivo_totp_nao_entra(client):
    usuario = _operador()
    resposta = _entrar(client, usuario, None, "123456")
    assert resposta.status_code == 200
    assert not _admin_acessivel(client)


def test_senha_certa_e_token_errado_nao_entra(client):
    usuario = _operador()
    dispositivo = _dispositivo(usuario)
    resposta = _entrar(client, usuario, dispositivo, _token_invalido(dispositivo))
    assert resposta.status_code == 200
    assert not _admin_acessivel(client)


def test_senha_certa_e_token_certo_entram(client):
    usuario = _operador()
    dispositivo = _dispositivo(usuario)
    resposta = _entrar(client, usuario, dispositivo, _token_valido(dispositivo))
    assert resposta.status_code == 302
    assert _admin_acessivel(client)


def test_mesmo_token_nao_vale_duas_vezes():
    usuario = _operador()
    dispositivo = _dispositivo(usuario)
    token = _token_valido(dispositivo)
    primeiro, segundo = Client(), Client()
    assert _entrar(primeiro, usuario, dispositivo, token).status_code == 302
    assert _entrar(segundo, usuario, dispositivo, token).status_code == 200
    assert not _admin_acessivel(segundo)


def test_sessao_so_com_senha_nao_acessa_nenhuma_pagina_do_admin(client):
    usuario = _operador()
    _dispositivo(usuario)
    client.force_login(usuario)
    for caminho in (ADMIN_INDEX, ADMIN_LISTA_FONTES):
        resposta = client.get(caminho)
        assert resposta.status_code == 302, caminho
        assert "/admin/login/" in resposta["Location"], caminho


def test_codigo_de_recuperacao_entra_uma_vez_so():
    usuario = _operador()
    recuperacao = StaticDevice.objects.create(user=usuario, name="recuperacao", confirmed=True)
    codigo = "abc12345"
    StaticToken.objects.create(device=recuperacao, token=codigo)
    primeiro, segundo = Client(), Client()
    assert _entrar(primeiro, usuario, recuperacao, codigo).status_code == 302
    assert _admin_acessivel(primeiro)
    assert _entrar(segundo, usuario, recuperacao, codigo).status_code == 200
    assert not _admin_acessivel(segundo)


def test_usuario_inativo_nao_entra_mesmo_com_token_certo(client):
    usuario = _operador(is_active=False)
    dispositivo = _dispositivo(usuario)
    resposta = _entrar(client, usuario, dispositivo, _token_valido(dispositivo))
    assert resposta.status_code == 200
    assert not _admin_acessivel(client)


def test_usuario_sem_is_staff_nao_entra_mesmo_com_token_certo(client):
    usuario = _operador(is_staff=False)
    dispositivo = _dispositivo(usuario)
    resposta = _entrar(client, usuario, dispositivo, _token_valido(dispositivo))
    assert resposta.status_code == 200
    assert not _admin_acessivel(client)


def test_token_de_outro_operador_nao_vale():
    dono = _operador()
    dispositivo_do_dono = _dispositivo(dono)
    intruso = get_user_model().objects.create_user("intruso", password=SENHA, is_staff=True)
    client = Client()
    resposta = _entrar(client, intruso, dispositivo_do_dono, _token_valido(dispositivo_do_dono))
    assert resposta.status_code == 200
    assert not _admin_acessivel(client)


def test_middleware_otp_vem_depois_da_autenticacao():
    middlewares = settings.MIDDLEWARE
    auth = middlewares.index("django.contrib.auth.middleware.AuthenticationMiddleware")
    otp = middlewares.index("django_otp.middleware.OTPMiddleware")
    assert otp > auth


def test_site_do_admin_exige_otp_e_mantem_o_namespace_admin():
    from django_otp.admin import OTPAdminSite

    assert isinstance(admin.site, OTPAdminSite)
    assert admin.site.name == "admin"
    assert reverse("admin:index") == ADMIN_INDEX
