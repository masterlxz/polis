"""Coleta de listas JSON paginadas (API da Câmara, `/deputados`) para a camada bruta.

Mesmo desenho do `ZipCsvReader`, para o `ingest` não mudar: as páginas viram **um arquivo** com
um SHA-256 (não reler carga igual, retenção, falha que não apaga a anterior) e o leitor devolve
`(item, {coluna: texto})` só com as colunas da allowlist (ADR 0005).

- `fetch_pages`: baixa as páginas em série pelo `PoliteClient` (pausa, recuo e parada em 403 são
  dele; `itens` ≤ 100, ADR 0008), junta tudo num arquivo ordenado pelo id (o mesmo conteúdo dá o
  mesmo SHA-256 mesmo se a fonte trocar a ordem) e para na primeira página incompleta. Falha
  fechada: página fora do formato, id repetido ou páginas demais (`MAX_PAGES`).
- `JsonListReader`: leitura por **nome** de campo; campo permitido que falta é erro; campo novo é
  ignorado e contado; valor que não seja texto, número ou nulo rejeita a linha (tolerância zero,
  quem decide é o `ingest`). As mensagens de erro nunca citam valores, só nomes de campo.
"""

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .http_client import DownloadResult

PAGE_SIZE = 100
MAX_PAGES = 20
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_ITEMS = 10_000
MAX_VALUE_CHARS = 2_000

ITEM_NAME = "dados"


class JsonListError(Exception):
    """Base dos erros de formato da lista JSON. A mensagem nunca cita valores."""


class InvalidJsonError(JsonListError):
    pass


class MissingFieldError(JsonListError):
    pass


class DuplicateItemError(JsonListError):
    pass


class TooManyPagesError(JsonListError):
    pass


def _refuse_constant(_name):
    raise InvalidJsonError("constante JSON não permitida")


def _load_items(path, max_bytes):
    """Lê `{"dados": [objeto, ...]}` de `path`; qualquer outra forma é `InvalidJsonError`."""
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise InvalidJsonError("arquivo grande demais")
    try:
        body = json.loads(path.read_bytes(), parse_constant=_refuse_constant)
    except ValueError, RecursionError:
        raise InvalidJsonError("JSON inválido") from None
    if not isinstance(body, dict) or not isinstance(body.get("dados"), list):
        raise InvalidJsonError('esperava um objeto com a lista "dados"')
    items = body["dados"]
    if not all(isinstance(item, dict) for item in items):
        raise InvalidJsonError("os itens da lista precisam ser objetos")
    return items


def _page_url(url, number):
    parts = urlparse(url)
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "pagina"]
    query.append(("pagina", str(number)))
    return urlunparse(parts._replace(query=urlencode(query)))


def fetch_pages(
    client, url, destination, *, page_size=PAGE_SIZE, max_pages=None, unique_field="id"
):
    """Baixa as páginas de `url` e grava um arquivo único em `destination`.

    Devolve um `DownloadResult` do arquivo juntado (SHA-256 e tamanho dele, sem ETag). Erros de
    download e bloqueio do cliente passam sem mudança; erros de formato são `JsonListError`.
    """
    destination = Path(destination)
    limit = MAX_PAGES if max_pages is None else max_pages
    page_file = destination.with_name(destination.name + ".pagina")
    items = {}
    for number in range(1, limit + 1):
        client.download(_page_url(url, number), page_file)
        try:
            page = _load_items(page_file, MAX_PAGE_BYTES)
        finally:
            page_file.unlink(missing_ok=True)
        for item in page:
            key = item.get(unique_field)
            if not isinstance(key, str | int) or isinstance(key, bool):
                raise InvalidJsonError("item sem identificador escalar")
            if key in items:
                raise DuplicateItemError("identificador repetido entre as páginas")
            items[key] = item
        if len(page) < page_size:
            break
    else:
        raise TooManyPagesError("mais páginas do que o teto")

    ordered = [items[key] for key in sorted(items, key=str)]
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


class JsonListReader:
    def __init__(
        self,
        path,
        allowed_columns,
        *,
        max_items=MAX_ITEMS,
        max_value_chars=MAX_VALUE_CHARS,
    ):
        if isinstance(allowed_columns, str):
            raise ValueError("A allowlist deve ser uma lista de nomes, não um texto.")
        columns = list(allowed_columns)
        if not columns:
            raise ValueError("A allowlist de campos não pode ser vazia (ADR 0005, decisão 1).")
        if not all(isinstance(column, str) and column for column in columns):
            raise ValueError("A allowlist deve ter só nomes de campo não vazios.")
        if len(set(columns)) != len(columns):
            raise ValueError("A allowlist de campos tem nomes repetidos.")
        if not all(isinstance(limit, int) and limit > 0 for limit in (max_items, max_value_chars)):
            raise ValueError("Os limites devem ser inteiros positivos.")
        self.path = path
        self.allowed_columns = columns
        self.max_items = max_items
        self.max_value_chars = max_value_chars
        self.rows_read = 0
        self.rejected_rows = 0
        self.ignored_columns = set()

    def rows(self) -> Iterator[tuple[str, dict[str, str]]]:
        """Gera `(ITEM_NAME, {campo: texto})` só com os campos da allowlist."""
        items = _load_items(self.path, MAX_FILE_BYTES)
        if len(items) > self.max_items:
            raise InvalidJsonError("itens demais")
        allowed = set(self.allowed_columns)
        for item in items:
            self.rows_read += 1
            missing = [column for column in self.allowed_columns if column not in item]
            if missing:
                raise MissingFieldError(f"campo permitido ausente: {missing[0]}")
            self.ignored_columns |= set(item) - allowed
            values = {column: self._text(item[column]) for column in self.allowed_columns}
            if any(value is None for value in values.values()):
                self.rejected_rows += 1
                continue
            yield ITEM_NAME, values

    def _text(self, value):
        """Texto do valor escalar; `None` se inaceitável (objeto, lista, booleano, longo)."""
        if value is None:
            return ""
        if isinstance(value, bool) or not isinstance(value, str | int | float):
            return None
        text = value if isinstance(value, str) else str(value)
        return text if len(text) <= self.max_value_chars else None
