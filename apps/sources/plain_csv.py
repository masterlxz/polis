"""Leitor de CSV simples (fora de ZIP) em fluxo, com allowlist de colunas (ADR 0005, ADR 0031).

É o `ZipCsvReader` com a fonte dos bytes trocada: em vez de itens de um ZIP, lê um arquivo.
Tudo o mais é herdado e vale igual: leitura pelo NOME da coluna, só a allowlist sai, falha fechada
se uma coluna permitida faltar ou se repetir, coluna nova só é ignorada e registrada, linha de
largura errada é rejeitada e contada, e nenhuma mensagem de erro cita valor de linha.

O que muda para os arquivos anuais da Câmara (medidos em 2026-11-24):
- UTF-8 com BOM por padrão (`utf-8-sig` lê com ou sem BOM);
- `allow_multiline_records` existe porque `votacoes` tem registros em mais de uma linha física;
- `max_bytes` (padrão 100 MB; o maior arquivo real foi 58 MB) recusa a carga antes de ler.

Usa `_open_text`, `_read_layout` e `_read_item` do `ZipCsvReader` com um item de mentira (só
`filename` e `flag_bits`), porque esses métodos só tocam o ZIP para abrir o item. Se o
`ZipCsvReader` mudar esse contrato, os testes de `tests/test_plain_csv.py` pegam.
"""

import io
import os
from pathlib import Path
from types import SimpleNamespace

from .zip_csv import _FOREIGN_ERRORS, InvalidFormatError, ZipCsvReader, _Rejected

MAX_BYTES = 100 * 1024**2


class PlainCsvReader(ZipCsvReader):
    def __init__(
        self,
        path,
        allowed_columns,
        *,
        encoding="utf-8-sig",
        allow_multiline_records=False,
        max_bytes=MAX_BYTES,
        **limits,
    ):
        super().__init__(
            path,
            allowed_columns,
            encoding=encoding,
            allow_multiline_records=allow_multiline_records,
            max_uncompressed_bytes=max_bytes,
            **limits,
        )

    def _rows(self):
        failure = None
        try:
            if os.stat(self.path).st_size > self.max_uncompressed_bytes:
                raise _Rejected("arquivo acima do limite de bytes")
            item = SimpleNamespace(filename=Path(self.path).name, flag_bits=0)
            indices, width, self.ignored_columns = self._read_layout(None, item)
            yield from self._read_item(None, item, indices, width)
        except _Rejected as exc:
            failure = exc.reason
        except (*_FOREIGN_ERRORS, OSError) as exc:
            failure = type(exc).__name__
        if failure is not None:
            # Fora do `except`: sem __context__ e sem os quadros da falha original.
            raise InvalidFormatError(f"CSV inválido: {failure}.")

    def _open_text(self, zf, info):
        return io.TextIOWrapper(open(self.path, "rb"), encoding=self.encoding, newline="")
