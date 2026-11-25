"""Leitura de uma linha do bruto de `camara/votacoes-2026` e de `camara/votos-2026`, sem banco
(ADR 0031).

Mesmas regras do `parsing` dos deputados (dado externo, falha fechada, erro só com o NOME da
coluna). O bruto guarda tudo como TEXTO (o leitor de CSV). Número é convertido aqui; sinal, espaço,
hexadecimal ou dígito que não seja ASCII são recusados.

Diferenças que vêm dos dados medidos em 2026-11-24 (`fontes/camara.md`, Rodada 3):
- os totais de votos e o id da proposição valem `0` (8.984 de 9.153 e 4.101 de 9.153): por isso não
  usam o `_int` do parsing dos deputados, que recusa `0`; o `0` é gravado como vem;
- o id da votação é texto `<n>-<n>`, comparado como texto;
- `descricao` tem quebra de linha em 5 registros: cada quebra vira um espaço (decisão do dono); o
  bruto guarda o texto como veio, e qualquer outro caractere de controle recusa a linha;
- `voto` vazio é gravado vazio (a votação `2645346-18` tem 466): é "sem posição", não um voto;
- `aprovacao` é `1`, `0` ou vazio e fica como vem, sem interpretar; outro valor recusa a linha.

Os horários (`dataHoraRegistro`, `dataHoraVoto`) não são lidos: a fonte não diz o fuso.
"""

import re
from datetime import date

from .models import CamaraVote, CamaraVoting
from .parsing import INT32, RowError, _int, _text

_VOTING_ID = re.compile(r"[0-9]{1,10}-[0-9]{1,10}")
_VOTING_ID_MAX = CamaraVoting._meta.get_field("camara_voting_id").max_length
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_COUNT = re.compile(r"[0-9]{1,10}")
# Quebras de linha: CRLF, CR, LF e os separadores de linha e de parágrafo do Unicode (U+2028 e
# U+2029), que não são caracteres de controle e passariam pelo `_text`.
_LINE_BREAK = re.compile("\r\n|[\r\n  ]")
_DESCRIPTION_MAX = 5000
_APPROVALS = ("", "0", "1")


def _voting_id(values, column):
    value = values.get(column)
    if type(value) is not str or not _VOTING_ID.fullmatch(value) or len(value) > _VOTING_ID_MAX:
        raise RowError(column)
    return value


def _date(values, column):
    value = values.get(column)
    if type(value) is not str or not _DATE.fullmatch(value):
        raise RowError(column)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RowError(column) from None


def _count(values, column):
    """Inteiro não negativo que cabe no int32, com `0` aceito."""
    value = values.get(column)
    if type(value) is not str or not _COUNT.fullmatch(value) or int(value) > INT32:
        raise RowError(column)
    return int(value)


def _approval(values):
    value = values.get("aprovacao")
    if value not in _APPROVALS:
        raise RowError("aprovacao")
    return value


def _description(values):
    value = values.get("descricao")
    if type(value) is str:
        value = _LINE_BREAK.sub(" ", value)
    return _text({"descricao": value}, "descricao", _DESCRIPTION_MAX, required=False)


def parse_voting(values):
    """Campos de `CamaraVoting` de uma linha de `votacoes`, ou `RowError`."""
    field = CamaraVoting._meta.get_field
    return {
        "camara_voting_id": _voting_id(values, "id"),
        "voted_on": _date(values, "data"),
        "organ_acronym": _text(
            values, "siglaOrgao", field("organ_acronym").max_length, required=True
        ),
        "approval": _approval(values),
        "total_yes": _count(values, "votosSim"),
        "total_no": _count(values, "votosNao"),
        "total_other": _count(values, "votosOutros"),
        "description": _description(values),
        "proposition_id": _count(values, "ultimaApresentacaoProposicao_idProposicao"),
    }


def parse_vote(values):
    """`(id da votação, campos de `CamaraVote`)` de uma linha de `votos`, ou `RowError`."""
    field = CamaraVote._meta.get_field
    return _voting_id(values, "idVotacao"), {
        "camara_id": _int(values, "deputado_id"),
        "legislature_id": _int(values, "deputado_idLegislatura"),
        "party_acronym": _text(
            values, "deputado_siglaPartido", field("party_acronym").max_length, required=False
        ),
        "vote": _text(values, "voto", field("vote").max_length, required=False),
    }
