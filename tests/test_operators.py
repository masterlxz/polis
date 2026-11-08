"""Comandos de operador: criar com TOTP e recuperar a conta (ADR 0019, decisões 2, 5 e 6)."""

import getpass
import logging
import re
from base64 import b32encode
from io import StringIO
from urllib.parse import parse_qs, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

SENHA = "uma-senha-longa-so-de-teste-9731"
OUTRA_SENHA = "outra-senha-longa-so-de-teste-4482"

pytestmark = pytest.mark.django_db


@pytest.fixture
def digitar(monkeypatch):
    """Simula as duas digitações da senha (senha e confirmação) do `getpass`."""

    def _digitar(*respostas):
        fila = iter(respostas)
        monkeypatch.setattr(getpass, "getpass", lambda prompt="": next(fila))

    return _digitar


def _rodar(comando, *args):
    saida = StringIO()
    call_command(comando, *args, stdout=saida)
    return saida.getvalue()


def _criar(digitar, nome="operador", *args, senha=SENHA):
    digitar(senha, senha)
    return _rodar("create_operator", nome, *args)


def _usuario(nome="operador"):
    return get_user_model().objects.get(username=nome)


def _codigo_totp(dispositivo):
    codigo = totp(
        dispositivo.bin_key,
        dispositivo.step,
        dispositivo.t0,
        dispositivo.digits,
        dispositivo.drift,
    )
    return f"{codigo:0{dispositivo.digits}d}"


def _entrar(dispositivo, token, senha=SENHA):
    client = Client()
    resposta = client.post(
        reverse("admin:login"),
        {
            "username": dispositivo.user.get_username(),
            "password": senha,
            "otp_device": dispositivo.persistent_id,
            "otp_token": token,
            "next": "/admin/",
        },
    )
    entrou = resposta.status_code == 302 and client.get("/admin/").status_code == 200
    return entrou


def _dispositivo_totp(usuario):
    return TOTPDevice.objects.get(user=usuario)


def _dispositivo_recuperacao(usuario):
    return StaticDevice.objects.get(user=usuario)


# --- create_operator ---


def test_cria_operador_staff_sem_ser_superusuario(digitar):
    _criar(digitar)
    usuario = _usuario()
    assert usuario.is_staff and usuario.is_active
    assert not usuario.is_superuser
    assert usuario.check_password(SENHA)


def test_superuser_so_com_a_opcao_explicita(digitar):
    _criar(digitar, "chefe", "--superuser")
    assert _usuario("chefe").is_superuser


def test_cria_dispositivo_totp_confirmado_e_10_codigos_de_recuperacao(digitar):
    _criar(digitar)
    usuario = _usuario()
    assert _dispositivo_totp(usuario).confirmed
    assert _dispositivo_recuperacao(usuario).token_set.count() == 10


def test_opcao_codes_muda_a_quantidade_de_codigos(digitar):
    _criar(digitar, "operador", "--codes", "3")
    assert _dispositivo_recuperacao(_usuario()).token_set.count() == 3


def test_imprime_a_url_otpauth_e_os_codigos_uma_vez(digitar):
    saida = _criar(digitar)
    usuario = _usuario()
    dispositivo = _dispositivo_totp(usuario)
    url = re.search(r"otpauth://\S+", saida).group(0)
    consulta = parse_qs(urlparse(url).query)
    assert consulta["secret"][0] == b32encode(dispositivo.bin_key).decode()
    assert consulta["issuer"][0] == "polis"
    for codigo in _dispositivo_recuperacao(usuario).token_set.values_list("token", flat=True):
        assert saida.count(codigo) == 1


def test_a_senha_nunca_aparece_na_saida_nem_nos_logs(digitar, caplog):
    caplog.set_level(logging.DEBUG)
    saida = _criar(digitar)
    segredos = [
        SENHA,
        _dispositivo_totp(_usuario()).key,
        *_dispositivo_recuperacao(_usuario()).token_set.values_list("token", flat=True),
    ]
    for segredo in segredos:
        assert segredo not in caplog.text
    assert SENHA not in saida


def test_login_com_o_token_do_dispositivo_criado_funciona(digitar):
    _criar(digitar)
    dispositivo = _dispositivo_totp(_usuario())
    assert _entrar(dispositivo, _codigo_totp(dispositivo))


def test_codigo_de_recuperacao_impresso_entra_uma_vez_so(digitar):
    saida = _criar(digitar)
    recuperacao = _dispositivo_recuperacao(_usuario())
    codigo = next(c for c in recuperacao.token_set.values_list("token", flat=True) if c in saida)
    assert _entrar(recuperacao, codigo)
    assert not _entrar(recuperacao, codigo)


def test_senha_fraca_e_recusada_e_nada_e_criado(digitar):
    with pytest.raises(CommandError, match="Senha recusada"):
        _criar(digitar, senha="12345678")
    assert not get_user_model().objects.filter(username="operador").exists()


def test_confirmacao_diferente_da_senha_e_recusada(digitar):
    digitar(SENHA, OUTRA_SENHA)
    with pytest.raises(CommandError, match="não conferem"):
        _rodar("create_operator", "operador")
    assert not get_user_model().objects.filter(username="operador").exists()


def test_usuario_existente_nao_e_alterado(digitar):
    _criar(digitar)
    antes = _dispositivo_totp(_usuario()).key
    digitar(OUTRA_SENHA, OUTRA_SENHA)
    with pytest.raises(CommandError, match="já existe"):
        _rodar("create_operator", "operador")
    usuario = _usuario()
    assert usuario.check_password(SENHA)
    assert _dispositivo_totp(usuario).key == antes


def test_falha_ao_criar_o_dispositivo_nao_deixa_usuario_sem_segundo_fator(digitar, monkeypatch):
    def falha(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr("apps.operators.enrollment.enroll", falha)
    with pytest.raises(RuntimeError):
        _criar(digitar)
    assert not get_user_model().objects.filter(username="operador").exists()


def test_a_senha_nao_e_aceita_como_argumento(digitar):
    with pytest.raises(CommandError, match="unrecognized arguments"):
        _rodar("create_operator", "operador", f"--password={SENHA}")
    assert not get_user_model().objects.filter(username="operador").exists()


# --- reset_totp ---


def test_reset_invalida_token_e_codigos_antigos_e_vale_o_novo(digitar):
    _criar(digitar)
    usuario = _usuario()
    antigo = _dispositivo_totp(usuario)
    token_antigo = _codigo_totp(antigo)
    codigo_antigo = _dispositivo_recuperacao(usuario).token_set.first().token

    saida = _rodar("reset_totp", "operador")

    novo = _dispositivo_totp(usuario)
    nova_recuperacao = _dispositivo_recuperacao(usuario)
    assert TOTPDevice.objects.filter(user=usuario).count() == 1
    assert StaticDevice.objects.filter(user=usuario).count() == 1
    assert not StaticToken.objects.filter(token=codigo_antigo).exists()
    assert not _entrar(antigo, token_antigo)
    assert _entrar(novo, _codigo_totp(novo))
    assert re.search(r"otpauth://\S+", saida)
    for codigo in nova_recuperacao.token_set.values_list("token", flat=True):
        assert codigo in saida


def test_reset_nao_muda_a_senha_do_operador(digitar):
    _criar(digitar)
    _rodar("reset_totp", "operador")
    assert _usuario().check_password(SENHA)


def test_reset_de_usuario_inexistente_e_recusado():
    with pytest.raises(CommandError, match="não existe"):
        _rodar("reset_totp", "fantasma")
