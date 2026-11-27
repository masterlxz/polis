"""Leitura de uma linha do bruto de `camara/proposicoes-tramitacoes-2026`, sem banco (ADR 0034).

Mesmas regras de `camara_voting_parsing` (dado externo, falha fechada, erro só com o NOME da
coluna; o bruto guarda tudo como TEXTO). Diferenças que vêm dos dados medidos em 2026-11-27:
- o id da proposição só existe dentro de `uriProposicao` (`.../api/v2/proposicoes/14666`); a URI em
  si não é gravada;
- `sequencia` é vazia em 1 linha de 118.724: vira `None`; fora isso só dígitos;
- `dataHora` vem sem fuso (`2026-05-07T16:58:00`) e é gravada como horário de Brasília, que é um
  palpite não verificado (ADR 0034, decisão 7);
- `siglaOrgao` (até 10 medidos, teto 30) e `descricaoTramitacao` (até 57 medidos, teto 200) são
  obrigatórias e não têm nenhum caractere de controle (nenhum medido).
"""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .camara_voting_parsing import _count
from .models import CamaraPropositionStep
from .parsing import RowError, _text

_PROPOSITION_URI = re.compile(r"https?://[^\s/]+/(?:[^\s/]+/)*proposicoes/([0-9]{1,10})")
_DATE_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")
_BRASILIA = ZoneInfo("America/Sao_Paulo")


def _proposition_id(values):
    value = values.get("uriProposicao")
    match = _PROPOSITION_URI.fullmatch(value) if type(value) is str else None
    if match is None or int(match.group(1)) == 0:
        raise RowError("uriProposicao")
    return str(int(match.group(1)))


def _sequence(values):
    if values.get("sequencia") == "":
        return None
    return _count(values, "sequencia")


def _occurred_at(values):
    value = values.get("dataHora")
    moment = None
    if type(value) is str and _DATE_TIME.fullmatch(value):
        try:
            moment = datetime.fromisoformat(value)
        except ValueError:
            moment = None
    if moment is None:
        raise RowError("dataHora")
    return moment.replace(tzinfo=_BRASILIA)


def parse_row(values):
    """Os campos de `CamaraPropositionStep` de uma linha (sem a execução), ou `RowError`."""
    field = CamaraPropositionStep._meta.get_field
    return {
        "camara_proposition_id": _proposition_id(values),
        "sequence": _sequence(values),
        "occurred_at": _occurred_at(values),
        "organ_code": _text(values, "siglaOrgao", field("organ_code").max_length, required=True),
        "description": _text(
            values, "descricaoTramitacao", field("description").max_length, required=True
        ),
    }
