"""Leitura de uma linha do bruto de `senado/votacoes`, sem banco (ADR 0029).

Mesmas regras do `parsing` da Câmara (dado externo, falha fechada, erro só com o NOME da coluna).
O bruto guarda tudo como TEXTO (o leitor JSON converte número em texto) e traz uma linha por voto,
com os campos da votação repetidos. `parse_row` devolve as duas metades: os campos da votação e
os do voto. Número é convertido aqui; sinal, espaço, hexadecimal ou dígito que não seja ASCII são
recusados. A sigla do voto e o resultado são gravados como vêm, sem interpretar (o significado de
AP, LS, P-NRV e outras não foi verificado). Os totais vêm vazios nas votações abertas (viram
`None`) e preenchidos nas secretas.
"""

import re
from datetime import date

from .models import SenateVote, SenateVoting
from .parsing import INT32, RowError, _int, _text

_UF = re.compile(r"[A-Z]{2}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_COUNT = re.compile(r"[0-9]{1,10}")
_SUMMARY_MAX = 5000
SMALLINT = 32767


def _date(values, column):
    value = values.get(column)
    if type(value) is not str or not _DATE.fullmatch(value):
        raise RowError(column)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RowError(column) from None


def _secret(values):
    value = values.get("votacaoSecreta")
    if value not in ("S", "N"):
        raise RowError("votacaoSecreta")
    return value == "S"


def _count(values, column):
    """Total de votos: vazio é `None` (a fonte não diz); número inteiro não negativo."""
    value = values.get(column)
    if value == "":
        return None
    if type(value) is not str or not _COUNT.fullmatch(value) or int(value) > INT32:
        raise RowError(column)
    return int(value)


def _year(values):
    year = _int(values, "ano")
    if year > SMALLINT:
        raise RowError("ano")
    return year


def parse_row(values):
    """Devolve `(campos da votação, campos do voto)` de uma linha do bruto, ou `RowError`."""
    voting_f = SenateVoting._meta.get_field
    vote_f = SenateVote._meta.get_field
    voting = {
        "session_voting_code": _int(values, "codigoSessaoVotacao"),
        "voted_on": _date(values, "dataSessao"),
        "type_acronym": _text(values, "sigla", voting_f("type_acronym").max_length, required=True),
        "number": _text(values, "numero", voting_f("number").max_length, required=True),
        "year": _year(values),
        "identification": _text(
            values, "identificacao", voting_f("identification").max_length, required=True
        ),
        "summary": _text(values, "ementa", _SUMMARY_MAX, required=False),
        "result": _text(values, "resultadoVotacao", voting_f("result").max_length, required=True),
        "secret": _secret(values),
        "total_yes": _count(values, "totalVotosSim"),
        "total_no": _count(values, "totalVotosNao"),
        "total_abstention": _count(values, "totalVotosAbstencao"),
        "process_id": _int(values, "idProcesso"),
        "matter_id": _int(values, "codigoMateria"),
    }
    state = _text(values, "siglaUFParlamentar", 2, required=True)
    if not _UF.fullmatch(state):
        raise RowError("siglaUFParlamentar")
    vote = {
        "senate_id": _int(values, "codigoParlamentar"),
        "name": _text(values, "nomeParlamentar", vote_f("name").max_length, required=True),
        "party_acronym": _text(
            values, "siglaPartidoParlamentar", vote_f("party_acronym").max_length, required=False
        ),
        "state": state,
        "vote_code": _text(
            values, "siglaVotoParlamentar", vote_f("vote_code").max_length, required=True
        ),
    }
    return voting, vote
