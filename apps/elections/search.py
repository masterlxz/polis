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

# Filtros opcionais sobre a candidatura que a página mostra (a do LATERAL). Parâmetro nulo apaga a
# condição; o psycopg embute o literal, então o planner resolve o `IS NULL`. A UF vem validada
# contra as 27 siglas e o partido normalizado como o texto: nada da entrada vira SQL.
_FILTROS = """
  AND (%s::text IS NULL OR c.state = %s)
  AND (%s::text IS NULL OR btrim(f_busca_normaliza(c.party_acronym)) = %s)
"""

_POR_TOKENS = (
    _SELECT
    + """
WHERE p.public_name_tsv @@ to_tsquery('simple', %s)"""
    + _FILTROS
    + """
ORDER BY (btrim(regexp_replace(f_busca_normaliza(p.public_name), ' +', ' ', 'g')) = %s) DESC,
         length(p.public_name), p.id
LIMIT %s
"""
)

_POR_SIMILARIDADE = (
    _SELECT
    + """
WHERE f_busca_normaliza(p.public_name) %% %s
  AND similarity(f_busca_normaliza(p.public_name), %s) >= %s"""
    + _FILTROS
    + """
ORDER BY similarity(f_busca_normaliza(p.public_name), %s) DESC, p.id
LIMIT %s
"""
)


def normalizar_consulta(consulta):
    """Texto livre -> lista de tokens [a-z0-9]+, sem acento, com teto de tamanho e de palavras."""
    texto = unicodedata.normalize("NFKD", (consulta or "")[:MAX_CARACTERES])
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return _TOKEN.findall(texto)[:MAX_PALAVRAS]


_UFS = frozenset(
    "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
)
MAX_CARACTERES_DO_PARTIDO = 20  # tamanho do campo `party_acronym`

# Filtro presente mas que nenhuma pessoa pode ter (UF que não existe, sigla longa demais): a busca
# devolve lista vazia, em vez de ignorar o filtro (que mostraria o que o usuário excluiu).
_NADA = object()


def normalizar_uf(valor):
    """None sem filtro; a sigla em caixa alta se for uma das 27; `_NADA` se for outra coisa."""
    texto = (valor or "").strip()[:MAX_CARACTERES].upper()
    if not texto:
        return None
    return texto if texto in _UFS else _NADA


def normalizar_partido(valor):
    """None se não há filtro; a sigla normalizada como o texto da busca (sem caixa, acento nem
    pontuação); `_NADA` se passar do tamanho do campo."""
    sigla = " ".join(normalizar_consulta(valor))
    if not sigla:
        return None
    return sigla if len(sigla) <= MAX_CARACTERES_DO_PARTIDO else _NADA


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


def buscar(consulta, uf=None, partido=None):
    """Pessoas pelo nome de urna; `uf` e `partido` só refinam (sem nome não há busca)."""
    tokens = normalizar_consulta(consulta)
    if sum(len(token) for token in tokens) < MIN_CARACTERES_UTEIS:
        return []
    uf = normalizar_uf(uf)
    partido = normalizar_partido(partido)
    if uf is _NADA or partido is _NADA:
        return []
    frase = " ".join(tokens)
    tsquery = " & ".join(f"{token}:*" for token in tokens)
    filtros = [uf, uf, partido, partido]

    exatos = _executar(_POR_TOKENS, [tsquery, *filtros, frase, MAX_RESULTADOS])
    resultados = [_resultado(linha, aproximado=False) for linha in exatos]
    if len(exatos) < MINIMO_DE_RESULTADOS:
        ja_vistos = {(linha[0], linha[1]) for linha in exatos}
        similares = _executar_reserva(
            [frase, frase, LIMIAR_DE_SIMILARIDADE, *filtros, frase, MAX_RESULTADOS]
        )
        resultados += [
            _resultado(linha, aproximado=True)
            for linha in similares
            if (linha[0], linha[1]) not in ja_vistos
        ]
    return resultados[:MAX_RESULTADOS]
