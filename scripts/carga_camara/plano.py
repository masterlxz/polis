"""Imprime o `EXPLAIN (ANALYZE, BUFFERS)` das consultas REAIS das views das tramitações da Câmara
(ADR 0010, 0035), com o banco no volume de `semear_volume.py`.

Uso (no CI, depois dos semeadores): `PYTHONPATH=. python scripts/carga_camara/plano.py`.
Em vez de reescrever as consultas aqui (e deixá-las divergir das views), pede cada página à API
pelo cliente de teste do Django, captura o SQL que a view de fato executou e roda o `EXPLAIN`
nele. Cada consulta roda 2 vezes e só o plano da segunda é impresso (a primeira esquenta o cache).
Sai com erro se alguma página não devolver o status esperado (um plano de 404 não diz nada).
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402
from django.test import Client  # noqa: E402
from django.test.utils import CaptureQueriesContext  # noqa: E402

# (título, caminho, status esperado)
PAGINAS = (
    ("proposição com 98 tramitações", "/internal/v1/camara/proposicoes/14669/", 200),
    ("proposição com ementa longa", "/internal/v1/camara/proposicoes/14668/", 200),
    ("votação com 213 proposições", "/internal/v1/camara/votacoes/9000002-1/", 200),
    ("votação de volume (6 proposições)", "/internal/v1/camara/votacoes/8000000-1/", 200),
)


def main():
    cliente = Client(HTTP_HOST="127.0.0.1")
    for titulo, caminho, esperado in PAGINAS:
        with CaptureQueriesContext(connection) as contexto:
            resposta = cliente.get(caminho)
        if resposta.status_code != esperado:
            sys.exit(f"{caminho}: esperava {esperado}, veio {resposta.status_code}")
        print(f"\n##### {titulo}: {caminho} ({len(contexto)} consultas)")
        for numero, consulta in enumerate(contexto.captured_queries, 1):
            sql = consulta["sql"]
            with connection.cursor() as cursor:
                for _ in range(2):
                    cursor.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql)
                    linhas = [linha[0] for linha in cursor.fetchall()]
            print(f"\n=== consulta {numero} ===\n{sql[:400]}\n" + "\n".join(linhas))


if __name__ == "__main__":
    main()
