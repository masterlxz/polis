"""Imprime o `EXPLAIN (ANALYZE, BUFFERS)` das duas consultas da busca (ADR 0016) para 3 consultas
de amostra tiradas do arquivo de nomes: exata, com erro de digitação e prefixo.

Uso (no CI, depois do semeador): `python scripts/carga_busca/plano.py consultas.txt`.
Cada consulta roda 2 vezes e só o plano da segunda é impresso (a primeira esquenta o cache).
"""

import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection, transaction  # noqa: E402

from apps.elections import search  # noqa: E402


def explicar(titulo, sql, params, limiar=None):
    # `limiar`: o mesmo ajuste que `search._executar_reserva` faz (set_config local à transação).
    with transaction.atomic(), connection.cursor() as cursor:
        if limiar is not None:
            cursor.execute("SELECT set_config('pg_trgm.similarity_threshold', %s, true)", [limiar])
        for _ in range(2):
            cursor.execute("EXPLAIN (ANALYZE, BUFFERS) " + sql, params)
            linhas = [linha[0] for linha in cursor.fetchall()]
    print(f"\n=== {titulo} ===")
    print("\n".join(linhas))


def main(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        nome = next(linha.strip() for linha in arquivo if len(linha.split()) >= 2)
    palavras = nome.split()
    amostras = {
        "exata": " ".join(palavras[:2]),
        "erro": " ".join(palavras[:2])[:3] + " ".join(palavras[:2])[4:],
        "prefixo": " ".join(p[:3] for p in palavras[:2]),
    }
    for classe, consulta in amostras.items():
        tokens = search.normalizar_consulta(consulta)
        frase = " ".join(tokens)
        tsquery = " & ".join(f"{token}:*" for token in tokens)
        print(f"\n##### {classe}: {consulta!r}")
        explicar(
            f"{classe}: caminho por tokens",
            search._POR_TOKENS,
            [tsquery, None, None, None, None, frase, search.MAX_RESULTADOS],
        )
        explicar(
            f"{classe}: reserva por trigramas",
            search._POR_SIMILARIDADE,
            [
                frase,
                frase,
                search.LIMIAR_DE_SIMILARIDADE,
                None,
                None,
                None,
                None,
                frase,
                search.MAX_RESULTADOS,
            ],
            limiar=str(search.LIMIAR_DE_SIMILARIDADE),
        )


if __name__ == "__main__":
    main(sys.argv[1])
