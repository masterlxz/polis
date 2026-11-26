"""Leitura de uma linha do bruto de `camara/votacoes-proposicoes-2026` e de
`camara/votacoes-objetos-2026`, sem banco (Rodada 4 de `fontes/camara.md`).

Mesmas regras de `camara_voting_parsing` (dado externo, falha fechada, erro só com o NOME da
coluna; o bruto guarda tudo como TEXTO). Diferenças que vêm dos dados medidos em 2026-11-26:
- `proposicao_ementa` tem quebra de linha e TAB (o único controle real, 7 + 35 ocorrências): cada
  um vira um espaço; qualquer outro caractere de controle recusa a linha; vazia é válida (404
  proposições); o teto é 20.000 caracteres (o maior medido foi 5.259);
- `proposicao_ano` é vazio em 32.899 linhas de `votacoesObjetos`: vira `None`;
- o id da proposição tem até 7 dígitos e nunca é `0` (o `0` é do campo da votação, não deste).
"""

import re

from .camara_voting_parsing import _LINE_BREAK, _count, _voting_id
from .models import CamaraProposition
from .parsing import _int, _text

_EMENTA_MAX = 20_000
# Quebra de linha (inclui U+2028 e U+2029) e TAB: viram um espaço, como a `descricao` da votação.
_BREAK_OR_TAB = re.compile(f"{_LINE_BREAK.pattern}|\t")


def _ementa(values):
    value = values.get("proposicao_ementa")
    if type(value) is str:
        value = _BREAK_OR_TAB.sub(" ", value)
    return _text({"proposicao_ementa": value}, "proposicao_ementa", _EMENTA_MAX, required=False)


def _year(values):
    value = values.get("proposicao_ano")
    if value == "":
        return None
    return _count(values, "proposicao_ano")


def parse_row(values):
    """`(id da votação, campos de `CamaraProposition`)` de uma linha, ou `RowError`."""
    field = CamaraProposition._meta.get_field
    return _voting_id(values, "idVotacao"), {
        "camara_id": _int(values, "proposicao_id"),
        "title": _text(values, "proposicao_titulo", field("title").max_length, required=True),
        "type_acronym": _text(
            values, "proposicao_siglaTipo", field("type_acronym").max_length, required=True
        ),
        "number": _count(values, "proposicao_numero"),
        "year": _year(values),
        "ementa": _ementa(values),
    }
