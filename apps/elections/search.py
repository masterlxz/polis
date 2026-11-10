"""Busca de pessoas por nome de urna (ADR 0016, ADR 0012).

Interface única do módulo: `buscar(consulta)`. Só o nome de urna (`Person.public_name`) é
buscável: o nome social e qualquer outro dado interno ficam fora (ADR 0012). A entrada do
usuário nunca chega ao `to_tsquery` como veio: vira uma lista de tokens [a-z0-9]+ (sem
operadores) e o texto da consulta só viaja como parâmetro.

Caminho principal: todas as palavras da consulta, cada uma como prefixo, ligadas por E, no
`tsvector` indexado (`public_name_tsv`). Se vierem menos de `MINIMO_DE_RESULTADOS`, completa com
a reserva por similaridade de trigramas (`pg_trgm`, limiar `LIMIAR_DE_SIMILARIDADE`).
"""

import re
import unicodedata

from django.db import connection, transaction

MAX_CARACTERES = 100
MAX_PALAVRAS = 10
MIN_CARACTERES_UTEIS = 2
MAX_RESULTADOS = 20
MINIMO_DE_RESULTADOS = 5
LIMIAR_DE_SIMILARIDADE = 0.5

_TOKEN = re.compile(r"[a-z0-9]+")

# Pessoa + UF e partido da candidatura mais recente (uma consulta só, sem N+1).
_SELECT = """
SELECT p.cycle_year, p.tse_candidate_id, p.public_name, c.state, c.party_acronym
FROM elections_person p
LEFT JOIN LATERAL (
    SELECT ca.state, ca.party_acronym
    FROM elections_candidacy ca
    JOIN elections_election e ON e.id = ca.election_id
    WHERE ca.person_id = p.id
    ORDER BY e.date DESC, e.round DESC
    LIMIT 1
) c ON true
"""

_POR_TOKENS = (
    _SELECT
    + """
WHERE p.public_name_tsv @@ to_tsquery('simple', %s)
ORDER BY (btrim(regexp_replace(f_busca_normaliza(p.public_name), ' +', ' ', 'g')) = %s) DESC,
         length(p.public_name), p.id
LIMIT %s
"""
)

_POR_SIMILARIDADE = (
    _SELECT
    + """
WHERE f_busca_normaliza(p.public_name) %% %s
  AND similarity(f_busca_normaliza(p.public_name), %s) >= %s
ORDER BY similarity(f_busca_normaliza(p.public_name), %s) DESC, p.id
LIMIT %s
"""
)


def normalizar_consulta(consulta):
    """Texto livre -> lista de tokens [a-z0-9]+, sem acento, com teto de tamanho e de palavras."""
    texto = unicodedata.normalize("NFKD", (consulta or "")[:MAX_CARACTERES])
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return _TOKEN.findall(texto)[:MAX_PALAVRAS]


def _executar(sql, params):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _executar_reserva(params):
    """A reserva com o limiar do índice igual ao do código.

    O `%` do `pg_trgm` usa `pg_trgm.similarity_threshold` (padrão 0,3), não o nosso 0,5: com 0,3
    o índice devolve dezenas de milhares de candidatos que o `similarity >= 0,5` descarta depois
    (3 milhões de linhas: cerca de 820 ms por consulta). `set_config(..., true)` vale só até o fim
    da transação, que o `atomic()` abre aqui (em autocommit valeria só para o próprio comando de
    ajuste), então nada vaza para a conexão.
    """
    with transaction.atomic():
        _executar(
            "SELECT set_config('pg_trgm.similarity_threshold', %s, true)",
            [str(LIMIAR_DE_SIMILARIDADE)],
        )
        return _executar(_POR_SIMILARIDADE, params)


def _resultado(linha, *, aproximado):
    ciclo, sq, nome, uf, partido = linha
    return {
        "id": f"{ciclo}-{sq}",
        "nome": nome,
        "ciclo": ciclo,
        "uf": uf,
        "partido": partido,
        "aproximado": aproximado,
    }


def buscar(consulta):
    tokens = normalizar_consulta(consulta)
    if sum(len(token) for token in tokens) < MIN_CARACTERES_UTEIS:
        return []
    frase = " ".join(tokens)
    tsquery = " & ".join(f"{token}:*" for token in tokens)

    exatos = _executar(_POR_TOKENS, [tsquery, frase, MAX_RESULTADOS])
    resultados = [_resultado(linha, aproximado=False) for linha in exatos]
    if len(exatos) < MINIMO_DE_RESULTADOS:
        ja_vistos = {(linha[0], linha[1]) for linha in exatos}
        similares = _executar_reserva([frase, frase, LIMIAR_DE_SIMILARIDADE, frase, MAX_RESULTADOS])
        resultados += [
            _resultado(linha, aproximado=True)
            for linha in similares
            if (linha[0], linha[1]) not in ja_vistos
        ]
    return resultados[:MAX_RESULTADOS]
