"""Leitura de uma linha do bruto do TSE (`consulta_cand`), sem banco.

Parsing de dado externo é código crítico: tudo que sai daqui já cabe nos campos dos modelos, para
que o banco nunca seja a primeira defesa (a mensagem de um erro de banco cita valores da linha,
onde há dado pessoal). Falha fechada (ADR 0005, decisão 6): coluna ausente, valor fora do formato
ou marcador num campo obrigatório recusam a linha. O erro cita só o NOME da coluna, nunca o valor,
e é levantado fora de qualquer `except`, para não encadear a exceção original.

Marcadores do TSE (`leiame.pdf`, medido na Sessão 39): `#NULO`/`#NE` (e `-1`/`-3`/`-4` nos
campos numéricos) e `NÃO DIVULGÁVEL` valem "ausente" nos campos opcionais.

Não tratado: caracteres de formatação Unicode (por exemplo inversão de direção); são questão da
camada de exibição. O fuso de `DT_GERACAO` e `HH_GERACAO` (Brasília) é suposição.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from .models import Candidacy, Election, Person

SOURCE_TIMEZONE = ZoneInfo("America/Sao_Paulo")
MARKERS = frozenset({"#NULO", "#NULO#", "#NE", "#NE#", "-1", "-3", "-4", "NÃO DIVULGÁVEL", ""})
COALITION_COMPOSITION_MAX = 2000
INT16, INT32, INT64 = 2**15 - 1, 2**31 - 1, 2**63 - 1

_DIGITS = re.compile(r"[0-9]{1,18}")
_DATE = re.compile(r"([0-9]{2})/([0-9]{2})/([0-9]{4})")
_TIME = re.compile(r"([0-9]{2}):([0-9]{2}):([0-9]{2})")


class RowError(Exception):
    """Linha recusada. Guarda só o nome da coluna."""

    def __init__(self, column):
        super().__init__(f"coluna inválida: {column}")
        self.column = column


@dataclass(frozen=True)
class ParsedRow:
    election: dict
    person: dict
    candidacy: dict


def _limit(model, field):
    return model._meta.get_field(field).max_length


def _text(values, column):
    value = values.get(column)
    if type(value) is not str:
        raise RowError(column)
    value = value.strip()
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise RowError(column)
    return value


def _required_text(values, column, limit):
    value = _text(values, column)
    if value in MARKERS or len(value) > limit:
        raise RowError(column)
    return value


def _optional_text(values, column, limit):
    value = _text(values, column)
    if value in MARKERS:
        return ""
    if len(value) > limit:
        raise RowError(column)
    return value


def _integer(value, column, maximum):
    if not _DIGITS.fullmatch(value) or int(value) > maximum:
        raise RowError(column)
    return int(value)


def _required_int(values, column, maximum):
    return _integer(_text(values, column), column, maximum)


def _optional_int(values, column, maximum):
    value = _text(values, column)
    return None if value in MARKERS else _integer(value, column, maximum)


def _date(values, column):
    match = _DATE.fullmatch(_text(values, column))
    parsed = None
    if match:
        day, month, year = (int(group) for group in match.groups())
        try:
            parsed = date(year, month, day)
        except ValueError:
            parsed = None
    if parsed is None:
        raise RowError(column)
    return parsed


def _time(values, column):
    match = _TIME.fullmatch(_text(values, column))
    parsed = None
    if match:
        hour, minute, second = (int(group) for group in match.groups())
        try:
            parsed = time(hour, minute, second)
        except ValueError:
            parsed = None
    if parsed is None:
        raise RowError(column)
    return parsed


def parse_row(values):
    """Converte uma linha do bruto em campos de `Election`, `Person` e `Candidacy`."""
    year = _required_int(values, "ANO_ELEICAO", INT16)
    election = {
        "tse_code": _required_int(values, "CD_ELEICAO", INT32),
        "round": _required_int(values, "NR_TURNO", INT16),
        "year": year,
        "kind_code": _required_int(values, "CD_TIPO_ELEICAO", INT16),
        "kind_name": _required_text(values, "NM_TIPO_ELEICAO", _limit(Election, "kind_name")),
        "description": _required_text(values, "DS_ELEICAO", _limit(Election, "description")),
        "date": _date(values, "DT_ELEICAO"),
    }
    person = {
        "cycle_year": year,
        "tse_candidate_id": _required_int(values, "SQ_CANDIDATO", INT64),
        "public_name": _required_text(values, "NM_URNA_CANDIDATO", _limit(Person, "public_name")),
        "social_name": _optional_text(values, "NM_SOCIAL_CANDIDATO", _limit(Person, "social_name")),
    }
    generated_date = _date(values, "DT_GERACAO")
    generated_time = _time(values, "HH_GERACAO")
    candidacy = {
        "ballot_number": _required_int(values, "NR_CANDIDATO", INT32),
        "office_code": _required_int(values, "CD_CARGO", INT16),
        "office_name": _required_text(values, "DS_CARGO", _limit(Candidacy, "office_name")),
        "scope": _required_text(values, "TP_ABRANGENCIA", _limit(Candidacy, "scope")),
        "state": _required_text(values, "SG_UF", _limit(Candidacy, "state")),
        "electoral_unit_code": _required_text(
            values, "SG_UE", _limit(Candidacy, "electoral_unit_code")
        ),
        "electoral_unit_name": _required_text(
            values, "NM_UE", _limit(Candidacy, "electoral_unit_name")
        ),
        "party_number": _required_int(values, "NR_PARTIDO", INT16),
        "party_acronym": _required_text(values, "SG_PARTIDO", _limit(Candidacy, "party_acronym")),
        "party_name": _required_text(values, "NM_PARTIDO", _limit(Candidacy, "party_name")),
        "federation_acronym": _optional_text(
            values, "SG_FEDERACAO", _limit(Candidacy, "federation_acronym")
        ),
        "federation_name": _optional_text(
            values, "NM_FEDERACAO", _limit(Candidacy, "federation_name")
        ),
        "coalition_name": _optional_text(
            values, "NM_COLIGACAO", _limit(Candidacy, "coalition_name")
        ),
        "coalition_composition": _optional_text(
            values, "DS_COMPOSICAO_COLIGACAO", COALITION_COMPOSITION_MAX
        ),
        "status_code": _optional_int(values, "CD_SITUACAO_CANDIDATURA", INT16),
        "status_name": _optional_text(
            values, "DS_SITUACAO_CANDIDATURA", _limit(Candidacy, "status_name")
        ),
        "result_code": _optional_int(values, "CD_SIT_TOT_TURNO", INT16),
        "result_name": _optional_text(values, "DS_SIT_TOT_TURNO", _limit(Candidacy, "result_name")),
        "source_generated_at": datetime.combine(
            generated_date, generated_time, tzinfo=SOURCE_TIMEZONE
        ),
    }
    return ParsedRow(election=election, person=person, candidacy=candidacy)
