"""Leitor de ZIP de CSV em fluxo, com allowlist de colunas (ADR 0005).

Decisões do ADR 0005 que este módulo aplica:
- lê pelo NOME da coluna do cabeçalho, nunca pela posição (decisão 6);
- devolve só as colunas da allowlist; o resto é descartado na leitura (decisão 1);
- falha fechada: se qualquer item do ZIP tiver coluna permitida ausente ou duplicada,
  nenhuma linha de nenhum item é devolvida (decisão 6);
- coluna nova fora da allowlist: ignorada e registrada em `ignored_columns`;
- linha com número de colunas diferente do cabeçalho: rejeitada e contada em
  `rejected_rows`. O conteúdo da linha nunca é guardado nem citado.

Os erros citam só NOMES de item e de coluna, nunca valores. O módulo não escreve nada
em disco (os itens são lidos em memória, em fluxo) e não importa Django.

Atenção para quem consome:
- `rows()` é um gerador: a validação dos cabeçalhos acontece no primeiro `next()`.
- Um CRC inválido só é detectado ao fim da leitura de um item; as linhas anteriores
  já foram entregues. A atomicidade da carga é da transação de quem consome.
- Um item que começa com BOM UTF-8 falha, porque decodificar UTF-8 como ISO-8859-1
  nunca dá erro e corromperia os acentos em silêncio.
- `csv.field_size_limit` (global do processo) não é alterado: campo acima do limite
  padrão falha.
"""

import csv
import hashlib
import io
import zipfile
import zlib
from collections import Counter
from collections.abc import Iterator

# BOM UTF-8 como aparece depois de decodificar: em UTF-8 (U+FEFF) e em ISO-8859-1/cp1252
# (bytes EF BB BF).
_DECODED_BOMS = ("﻿", "ï»¿")

_FORMAT_ERRORS = (
    zipfile.BadZipFile,
    csv.Error,
    zlib.error,
    NotImplementedError,  # compressão não suportada pelo zipfile
    RuntimeError,  # item protegido por senha
    EOFError,
    UnicodeError,
)


class ZipCsvError(Exception):
    """Base dos erros do leitor. As mensagens nunca contêm valores de linha."""


class MissingColumnError(ZipCsvError):
    """Coluna da allowlist ausente no cabeçalho de um item."""


class DuplicateColumnError(ZipCsvError):
    """Coluna da allowlist repetida no cabeçalho de um item."""


class InvalidFormatError(ZipCsvError):
    """ZIP ou CSV inválido: corrompido, truncado, com CRC errado, codificação trocada etc."""


class ZipCsvReader:
    def __init__(self, path, allowed_columns, *, delimiter=";", encoding="iso-8859-1"):
        columns = list(allowed_columns)
        if not columns:
            raise ValueError("A allowlist de colunas não pode ser vazia (ADR 0005, decisão 1).")
        if len(set(columns)) != len(columns):
            raise ValueError("A allowlist de colunas tem nomes repetidos.")
        self.path = path
        self.allowed_columns = columns
        self.delimiter = delimiter
        self.encoding = encoding
        self.rows_read = 0
        self.rejected_rows = 0
        self.ignored_columns = set()

    def rows(self) -> Iterator[tuple[str, dict[str, str]]]:
        """Gera `(nome_do_item, {coluna: valor})` só com as colunas da allowlist."""
        self.rows_read = 0
        self.rejected_rows = 0
        self.ignored_columns = set()
        try:
            with zipfile.ZipFile(self.path) as zf:
                items = [
                    info
                    for info in zf.infolist()
                    if not info.is_dir() and info.filename.lower().endswith(".csv")
                ]
                layouts = [(info, *self._read_layout(zf, info)) for info in items]
                self.ignored_columns = set().union(*(ignored for _, _, _, ignored in layouts))
                for info, indices, width, _ in layouts:
                    yield from self._read_item(zf, info, indices, width)
        except _FORMAT_ERRORS as exc:
            # `from None`: a mensagem original do csv/zipfile não é repassada.
            raise InvalidFormatError(f"ZIP ou CSV inválido ({type(exc).__name__}).") from None

    def _open_text(self, zf, info):
        return io.TextIOWrapper(zf.open(info), encoding=self.encoding, newline="")

    def _read_layout(self, zf, info):
        """Valida o cabeçalho de um item: (índices das permitidas, largura, colunas ignoradas)."""
        with self._open_text(zf, info) as text:
            header = next(csv.reader(text, delimiter=self.delimiter), None)
        name = info.filename
        if header is None:
            raise MissingColumnError(f"{name}: item sem cabeçalho; faltam {self.allowed_columns}.")
        if header[0].startswith(_DECODED_BOMS):
            raise InvalidFormatError(
                f"{name}: BOM UTF-8 no início do item; a codificação da fonte mudou."
            )
        occurrences = Counter(header)
        missing = [column for column in self.allowed_columns if column not in occurrences]
        if missing:
            raise MissingColumnError(f"{name}: faltam as colunas {missing}.")
        duplicated = [column for column in self.allowed_columns if occurrences[column] > 1]
        if duplicated:
            raise DuplicateColumnError(f"{name}: colunas repetidas no cabeçalho: {duplicated}.")
        indices = [(column, i) for i, column in enumerate(self.allowed_columns)]
        ignored = set(header) - set(self.allowed_columns)
        return indices, len(header), ignored

    def _read_item(self, zf, info, indices, width):
        with self._open_text(zf, info) as text:
            reader = csv.reader(text, delimiter=self.delimiter)
            next(reader, None)  # cabeçalho, já validado
            for line in reader:
                if not line:
                    continue
                self.rows_read += 1
                if len(line) != width:
                    self.rejected_rows += 1
                    continue
                yield info.filename, {column: line[index] for column, index in indices}


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
