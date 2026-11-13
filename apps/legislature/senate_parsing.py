"""Leitura de uma linha do bruto de `senado/senadores`, sem banco (ADR 0028).

Mesmas regras do `parsing` da Câmara (dado externo, falha fechada, erro só com o NOME da coluna).
Diferença que importa: o bruto guarda tudo como TEXTO (o leitor JSON converte número em texto),
então o código do parlamentar chega como "5895" e é convertido aqui; inteiro de verdade, booleano,
espaço, sinal, hexadecimal ou dígito que não seja ASCII são recusados.

Suposição, não medida: `SiglaPartidoParlamentar` pode vir vazia ou nula (vira ""); código, nome e
UF são obrigatórios.
"""

import re

from .models import Senator
from .parsing import INT32, RowError, _text

_UF = re.compile(r"[A-Z]{2}")
_CODE = re.compile(r"[0-9]{1,10}")


def _code(values):
    value = values.get("CodigoParlamentar")
    if type(value) is not str or not _CODE.fullmatch(value) or not 0 < int(value) <= INT32:
        raise RowError("CodigoParlamentar")
    return int(value)


def parse_row(values):
    """Devolve os campos de `Senator` de uma linha do bruto, ou levanta `RowError`."""
    name_max = Senator._meta.get_field("name").max_length
    party_max = Senator._meta.get_field("party_acronym").max_length
    senate_id = _code(values)
    name = _text(values, "NomeParlamentar", name_max, required=True)
    party = _text(values, "SiglaPartidoParlamentar", party_max, required=False)
    state = _text(values, "UfParlamentar", 2, required=True)
    if not _UF.fullmatch(state):
        raise RowError("UfParlamentar")
    return {"senate_id": senate_id, "name": name, "party_acronym": party, "state": state}
