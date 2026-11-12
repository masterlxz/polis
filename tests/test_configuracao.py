import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection

RAIZ = Path(__file__).resolve().parent.parent


def _importar_settings(env_extra, remover=()):
    """Importa config.settings num processo limpo, com o ambiente controlado."""
    env = {k: v for k, v in os.environ.items() if k not in remover}
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", "from config import settings; print(settings.DEBUG)"],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_sem_secret_key_o_projeto_recusa_subir():
    resultado = _importar_settings({}, remover=("DJANGO_SECRET_KEY",))
    assert resultado.returncode != 0
    assert "DJANGO_SECRET_KEY" in resultado.stderr


def test_secret_key_vazia_tambem_e_recusada():
    resultado = _importar_settings({"DJANGO_SECRET_KEY": ""})
    assert resultado.returncode != 0
    assert "DJANGO_SECRET_KEY" in resultado.stderr


def test_debug_e_falso_quando_nao_definido():
    resultado = _importar_settings({"DJANGO_SECRET_KEY": "x"}, remover=("DJANGO_DEBUG",))
    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "False"


def test_debug_so_liga_com_valor_explicito():
    resultado = _importar_settings({"DJANGO_SECRET_KEY": "x", "DJANGO_DEBUG": "1"})
    assert resultado.stdout.strip() == "True"


def test_banco_e_postgresql():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"


@pytest.mark.django_db
def test_banco_responde_select_1():
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)


@pytest.mark.django_db
def test_banco_e_postgresql_18():
    assert connection.pg_version // 10000 == 18


def test_sem_migracao_pendente():
    resultado = subprocess.run(
        [sys.executable, "manage.py", "makemigrations", "--check", "--dry-run"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_admin_login_responde_200(client):
    assert client.get("/admin/login/").status_code == 200


def test_url_inexistente_responde_404(client):
    assert client.get("/nao-existe/").status_code == 404


# --- Produção atrás de um proxy (ADR 0011, plano da Sessão 59) ---
# Tudo por variável de ambiente, e sem variável o comportamento é o de desenvolvimento.

VARIAVEIS_DE_PRODUCAO = (
    "DJANGO_HTTPS",
    "DJANGO_BEHIND_PROXY",
    "DJANGO_HSTS_SECONDS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
)
CHAVE_LONGA = "k7Qz-Xr2mW9vLp4NbT8yHc3JdF6sGa1UeV5oIx0RnMw2Zq8YtKj4Pl7Dh9Sf3AbC6"


def _configuracao(env_extra=None):
    """Importa config.settings num processo limpo e devolve os valores de produção em JSON."""
    codigo = (
        "import json; from config import settings as s; "
        "print(json.dumps({'sessao': s.SESSION_COOKIE_SECURE, 'csrf': s.CSRF_COOKIE_SECURE, "
        "'proxy': s.SECURE_PROXY_SSL_HEADER, 'hsts': s.SECURE_HSTS_SECONDS, "
        "'origens': s.CSRF_TRUSTED_ORIGINS}))"
    )
    env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_DE_PRODUCAO}
    env.update({"DJANGO_SECRET_KEY": "x", **(env_extra or {})})
    return subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _valores(env_extra=None):
    resultado = _configuracao(env_extra)
    assert resultado.returncode == 0, resultado.stderr
    return json.loads(resultado.stdout)


def test_sem_variaveis_de_producao_tudo_fica_como_em_desenvolvimento():
    assert _valores() == {
        "sessao": False,
        "csrf": False,
        "proxy": None,
        "hsts": 0,
        "origens": [],
    }


@pytest.mark.parametrize("valor", ["1", "true", "TRUE"])
def test_https_liga_os_cookies_seguros(valor):
    valores = _valores({"DJANGO_HTTPS": valor})
    assert valores["sessao"] is True
    assert valores["csrf"] is True


@pytest.mark.parametrize("valor", ["0", "", "yes", "sim", "2"])
def test_https_so_liga_com_1_ou_true(valor):
    valores = _valores({"DJANGO_HTTPS": valor})
    assert valores["sessao"] is False
    assert valores["csrf"] is False


def test_atras_do_proxy_confia_no_cabecalho_de_protocolo_so_quando_pedido():
    assert _valores()["proxy"] is None
    assert _valores({"DJANGO_BEHIND_PROXY": "1"})["proxy"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert _valores({"DJANGO_BEHIND_PROXY": "0"})["proxy"] is None


def test_hsts_usa_o_inteiro_informado():
    assert _valores({"DJANGO_HSTS_SECONDS": "31536000"})["hsts"] == 31536000


@pytest.mark.parametrize("valor", ["abc", "-1", "1.5", "1 ano"])
def test_hsts_invalido_recusa_subir_citando_a_variavel(valor):
    resultado = _configuracao({"DJANGO_HSTS_SECONDS": valor})
    assert resultado.returncode != 0
    assert "DJANGO_HSTS_SECONDS" in resultado.stderr


def test_origens_csrf_viram_uma_lista():
    valores = _valores(
        {"DJANGO_CSRF_TRUSTED_ORIGINS": "https://polis.example.org, https://admin.example.org"}
    )
    assert valores["origens"] == ["https://polis.example.org", "https://admin.example.org"]


@pytest.mark.parametrize(
    "valor",
    ["polis.example.org", "https://ok.example.org,polis.example.org", "ftp://x.example.org"],
)
def test_origem_csrf_sem_http_ou_https_recusa_subir(valor):
    resultado = _configuracao({"DJANGO_CSRF_TRUSTED_ORIGINS": valor})
    assert resultado.returncode != 0
    assert "DJANGO_CSRF_TRUSTED_ORIGINS" in resultado.stderr


def test_arquivos_estaticos_sao_coletados_em_staticfiles_na_raiz():
    assert Path(settings.STATIC_ROOT) == RAIZ / "staticfiles"


def _check_deploy(env_extra):
    env = {k: v for k, v in os.environ.items() if k not in VARIAVEIS_DE_PRODUCAO}
    env.pop("DJANGO_DEBUG", None)
    env.update({"DJANGO_SECRET_KEY": CHAVE_LONGA, "DJANGO_ALLOWED_HOSTS": "polis.example.org"})
    env.update(env_extra)
    resultado = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy"],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return set(re.findall(r"security\.W\d+", resultado.stdout + resultado.stderr))


def test_check_deploy_em_producao_so_deixa_os_avisos_aceitos():
    avisos = _check_deploy({"DJANGO_HTTPS": "1", "DJANGO_BEHIND_PROXY": "1"})
    # W004: HSTS desligado até o dono decidir. W008: o redirecionamento para HTTPS é do proxy.
    assert avisos == {"security.W004", "security.W008"}


def test_check_deploy_sem_https_aponta_os_cookies_inseguros():
    avisos = _check_deploy({})
    assert {"security.W012", "security.W016"} <= avisos


def test_o_gunicorn_aceita_a_aplicacao():
    resultado = subprocess.run(
        [sys.executable, "-m", "gunicorn", "--check-config", "config.wsgi:application"],
        cwd=RAIZ,
        env={**os.environ, "DJANGO_SECRET_KEY": "x"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
