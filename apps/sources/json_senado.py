"""Coleta da lista de senadores em exercício (API do Senado, ADR 0028) para a camada bruta.

A resposta é uma só, aninhada (sem paginação):
`ListaParlamentarEmExercicio.Parlamentares.Parlamentar[].IdentificacaoParlamentar`. Aqui ela é
desembrulhada num arquivo `{"dados": [IdentificacaoParlamentar, ...]}`, ordenado pelo código, e o
resto do pipeline é o mesmo da Câmara (`JsonListReader`: leitura por nome de campo, só a allowlist,
tolerância zero, ADR 0005). O mesmo conteúdo dá o mesmo SHA-256, mesmo se a fonte trocar a ordem.

Falha fechada: a API responde 200 com um corpo vazio para "não existe" (medido), então envelope
ausente, lista vazia, item sem identificação, código repetido, arquivo grande ou itens demais
recusam a carga (`JsonListError`), em vez de virar uma lista de zero linhas que marcaria todos
como fora da lista. As mensagens de erro nunca citam valores.
"""

import hashlib
import json
from pathlib import Path

from .http_client import DownloadResult
from .json_list import DuplicateItemError, InvalidJsonError, _refuse_constant

MAX_BYTES = 5 * 1024 * 1024
MAX_ITEMS = 500
ID_FIELD = "CodigoParlamentar"


def _senators(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise InvalidJsonError("arquivo grande demais")
    try:
        body = json.loads(path.read_bytes(), parse_constant=_refuse_constant)
    except ValueError, RecursionError:
        raise InvalidJsonError("JSON inválido") from None
    node = body
    for key in ("ListaParlamentarEmExercicio", "Parlamentares", "Parlamentar"):
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, list):
        raise InvalidJsonError("esperava a lista de parlamentares no envelope")
    if len(node) > MAX_ITEMS:
        raise InvalidJsonError("itens demais")
    items = []
    for entry in node:
        item = entry.get("IdentificacaoParlamentar") if isinstance(entry, dict) else None
        if not isinstance(item, dict):
            raise InvalidJsonError("parlamentar sem identificação")
        items.append(item)
    return items


def fetch_senate_list(client, url, destination):
    """Baixa `url` e grava em `destination` o arquivo `{"dados": [...]}` desembrulhado."""
    destination = Path(destination)
    raw_file = destination.with_name(destination.name + ".bruto")
    client.download(url, raw_file)
    try:
        items = _senators(raw_file)
    finally:
        raw_file.unlink(missing_ok=True)
    seen = {}
    for item in items:
        key = item.get(ID_FIELD)
        if not isinstance(key, str | int) or isinstance(key, bool):
            raise InvalidJsonError("item sem identificador escalar")
        if key in seen:
            raise DuplicateItemError("identificador repetido")
        seen[key] = item
    ordered = [seen[key] for key in sorted(seen, key=str)]
    data = json.dumps(
        {"dados": ordered}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    destination.write_bytes(data)
    return DownloadResult(
        path=destination,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        etag="",
        last_modified="",
    )
