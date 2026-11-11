"""Leitura de uma linha do bruto de `camara/deputados`, sem banco (ADR 0021).

Parsing de dado externo é código crítico: tudo que sai daqui já cabe nos campos do modelo, para
que o banco nunca seja a primeira defesa (a mensagem de um erro de banco cita valores da linha).
Falha fechada (ADR 0005, decisão 6): campo ausente ou fora do formato recusa a linha. O erro cita
só o NOME da coluna do bruto, nunca o valor, e é levantado fora de qualquer `except`, para não
encadear a exceção original.

Suposição, não medida: `siglaPartido` pode vir vazia ou nula (vira ""); id, legislatura, nome e
UF são obrigatórios.
"""

import re
import unicodedata

from .models import Deputy

INT32 = 2**31 - 1
_UF = re.compile(r"[A-Z]{2}")


class RowError(Exception):
    """Linha recusada. Guarda só o nome da coluna."""

    def __init__(self, column):
        super().__init__(f"coluna inválida: {column}")
        self.column = column


def _int(values, column):
    value = values.get(column)
    if type(value) is not int or not 0 < value <= INT32:
        raise RowError(column)
    return value


def _text(values, column, max_length, *, required):
    value = values.get(column)
    if value is None and not required:
        return ""
    if type(value) is not str:
        raise RowError(column)
    value = value.strip()
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise RowError(column)
    if (required and not value) or len(value) > max_length:
        raise RowError(column)
    return value


def parse_row(values):
    """Devolve os campos de `Deputy` de uma linha do bruto, ou levanta `RowError`."""
    name_max = Deputy._meta.get_field("name").max_length
    party_max = Deputy._meta.get_field("party_acronym").max_length
    legislature_id = _int(values, "idLegislatura")
    camara_id = _int(values, "id")
    name = _text(values, "nome", name_max, required=True)
    party = _text(values, "siglaPartido", party_max, required=False)
    state = _text(values, "siglaUf", 2, required=True)
    if not _UF.fullmatch(state):
        raise RowError("siglaUf")
    return {
        "legislature_id": legislature_id,
        "camara_id": camara_id,
        "name": name,
        "party_acronym": party,
        "state": state,
    }
