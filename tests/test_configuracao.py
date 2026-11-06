import os
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
