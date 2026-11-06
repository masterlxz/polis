"""Leitor de ZIP de CSV em fluxo, com allowlist de colunas (ADR 0005).

Decisões do ADR 0005 que este módulo aplica:
- lê pelo NOME da coluna do cabeçalho, nunca pela posição (decisão 6);
- devolve só as colunas da allowlist; o resto é descartado na leitura (decisão 1);
- falha fechada: se qualquer item do ZIP tiver coluna permitida ausente ou duplicada,
  nenhuma linha de nenhum item é devolvida (decisão 6). Um ZIP sem nenhum CSV também falha:
  ele não pode passar por "arquivo íntegro sem registros" (decisão 9);
- coluna nova fora da allowlist: ignorada e registrada em `ignored_columns`;
- linha com número de colunas diferente do cabeçalho, ou registro que ocupa mais de uma
  linha física (aspas abertas juntam linhas), é rejeitado e contado em `rejected_rows`.
  O conteúdo nunca é guardado nem citado.

Segurança dos erros: as mensagens citam só NOMES de item e de coluna, nunca valores. O erro
final é levantado fora de qualquer `except`, então não carrega `__context__` nem os quadros
(com variáveis locais, que têm linhas do arquivo) da falha original.

O módulo não escreve nada em disco (itens lidos em memória, em fluxo) e não importa Django.

Contadores: `rows_read` conta linhas físicas não vazias e `rejected_rows` as rejeitadas.
O consumidor conta quantas linhas recebeu.

Atenção para quem consome:
- O leitor é de uso único: `rows()` só pode ser chamado uma vez.
- Um CRC inválido só é detectado ao fim da leitura de um item; as linhas anteriores já
  foram entregues. A atomicidade da carga é da transação de quem consome.
- Se todas as linhas forem rejeitadas, o leitor não falha: o consumidor deve olhar
  `rows_read` e `rejected_rows` antes de tratar o arquivo como íntegro.
- Item que começa com BOM UTF-8 falha: decodificar UTF-8 como ISO-8859-1 nunca dá erro e
  corromperia os acentos em silêncio.
- `csv.field_size_limit` (global do processo) não é alterado.
- Limites de recursos (colunas, caracteres por linha, itens, tamanho descomprimido
  declarado) têm padrões folgados e são configuráveis. O `zipfile` não lê além do tamanho
  declarado de cada item. Tempo de CPU não é limitado.
"""

import codecs
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

_ZIP_ENCRYPTED_FLAG = 0x1

_FOREIGN_ERRORS = (
    zipfile.BadZipFile,
    csv.Error,
    zlib.error,
    NotImplementedError,  # compressão não suportada pelo zipfile
    EOFError,
    UnicodeError,
    MemoryError,
    OverflowError,
)


class ZipCsvError(Exception):
    """Base dos erros do leitor. As mensagens nunca contêm valores de linha."""


class MissingColumnError(ZipCsvError):
    """Coluna da allowlist ausente no cabeçalho de um item."""


class DuplicateColumnError(ZipCsvError):
    """Coluna da allowlist repetida no cabeçalho de um item."""


class InvalidFormatError(ZipCsvError):
    """ZIP ou CSV inválido: corrompido, truncado, com CRC errado, acima dos limites etc."""


class _Rejected(Exception):
    """Interna: falha com motivo seguro (sem valores), convertida em InvalidFormatError."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class ZipCsvReader:
    def __init__(
        self,
        path,
        allowed_columns,
        *,
        delimiter=";",
        encoding="iso-8859-1",
        allow_multiline_records=False,
        max_columns=1_000,
        max_line_chars=200_000,
        max_items=1_000,
        max_uncompressed_bytes=64 * 1024**3,
    ):
        if isinstance(allowed_columns, str):
            raise ValueError("A allowlist deve ser uma lista de nomes, não um texto.")
        columns = list(allowed_columns)
        if not columns:
            raise ValueError("A allowlist de colunas não pode ser vazia (ADR 0005, decisão 1).")
        if not all(isinstance(column, str) and column for column in columns):
            raise ValueError("A allowlist deve ter só nomes de coluna não vazios.")
        if len(set(columns)) != len(columns):
            raise ValueError("A allowlist de colunas tem nomes repetidos.")
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise ValueError("O delimitador deve ter exatamente um caractere.")
        try:
            codecs.lookup(encoding)
        except LookupError:
            raise ValueError("Codificação desconhecida.") from None
        limits = (max_columns, max_line_chars, max_items, max_uncompressed_bytes)
        if not all(isinstance(limit, int) and limit > 0 for limit in limits):
            raise ValueError("Os limites devem ser inteiros positivos.")
        self.path = path
        self.allowed_columns = columns
        self.delimiter = delimiter
        self.encoding = encoding
        self.allow_multiline_records = allow_multiline_records
        self.max_columns = max_columns
        self.max_line_chars = max_line_chars
        self.max_items = max_items
        self.max_uncompressed_bytes = max_uncompressed_bytes
        self.rows_read = 0
        self.rejected_rows = 0
        self.ignored_columns = set()
        self._started = False

    def rows(self) -> Iterator[tuple[str, dict[str, str]]]:
        """Gera `(nome_do_item, {coluna: valor})` só com as colunas da allowlist."""
        if self._started:
            raise RuntimeError("O leitor é de uso único: rows() só pode ser chamado uma vez.")
        self._started = True
        return self._rows()

    def _rows(self):
        failure = None
        try:
            with zipfile.ZipFile(self.path) as zf:
                items = self._csv_items(zf)
                layouts = [(info, *self._read_layout(zf, info)) for info in items]
                self.ignored_columns = set().union(*(ignored for _, _, _, ignored in layouts))
                for info, indices, width, _ in layouts:
                    yield from self._read_item(zf, info, indices, width)
        except _Rejected as exc:
            failure = exc.reason
        except _FOREIGN_ERRORS as exc:
            raise InvalidFormatError(f"ZIP ou CSV inválido: {type(exc).__name__}.")  # noqa: B904
        if failure is not None:
            # Fora do `except`: sem __context__ e sem os quadros da falha original.
            raise InvalidFormatError(f"ZIP ou CSV inválido: {failure}.")

    def _csv_items(self, zf):
        items = [info for info in zf.infolist() if info.filename.lower().endswith(".csv")]
        if False and not items:
            raise _Rejected("nenhum item CSV no ZIP")
        if len(items) > self.max_items:
            raise _Rejected(f"mais de {self.max_items} itens CSV")
        names = Counter(info.filename for info in items)
        duplicated = sorted(name for name, count in names.items() if count > 1)
        if duplicated:
            raise _Rejected(f"itens com nome repetido: {duplicated!r}")
        if sum(info.file_size for info in items) > self.max_uncompressed_bytes:
            raise _Rejected("tamanho descomprimido declarado acima do limite")
        return items

    def _open_text(self, zf, info):
        return io.TextIOWrapper(zf.open(info), encoding=self.encoding, newline="")

    def _lines(self, text):
        """Linhas do item, com teto de caracteres por linha (um `;` repetido é uma bomba)."""
        while True:
            line = text.readline(self.max_line_chars + 1)
            size = len(line)
            if not size:
                return
            if size > self.max_line_chars:
                del line  # o quadro tem a linha inteira; não deixar no traceback
                raise _Rejected(f"linha com mais de {self.max_line_chars} caracteres")
            yield line

    def _read_layout(self, zf, info):
        """Valida o cabeçalho de um item: (índices das permitidas, largura, colunas ignoradas)."""
        name = repr(info.filename)
        if info.flag_bits & _ZIP_ENCRYPTED_FLAG:
            raise InvalidFormatError(f"{name}: item protegido por senha.")
        with self._open_text(zf, info) as text:
            # O cabeçalho vai direto como argumento: nenhuma variável local o guarda,
            # porque num arquivo sem cabeçalho a "primeira linha" são dados.
            reader = csv.reader(self._lines(text), delimiter=self.delimiter)
            error, payload = self._analyze(next(reader, None))
        if error is not None:
            raise error[0](f"{name}: {error[1]}")
        return payload

    def _analyze(self, header):
        """Devolve ((ErroClasse, mensagem), None) ou (None, (índices, largura, ignoradas))."""
        if not header:
            return (MissingColumnError, f"item sem cabeçalho; faltam {self.allowed_columns}."), None
        if len(header) > self.max_columns:
            return (InvalidFormatError, f"cabeçalho com mais de {self.max_columns} colunas."), None
        if header[0].startswith(_DECODED_BOMS):
            return (InvalidFormatError, "BOM UTF-8 no início do item; a codificação mudou."), None
        occurrences = Counter(header)
        missing = [column for column in self.allowed_columns if column not in occurrences]
        if missing:
            return (MissingColumnError, f"faltam as colunas {missing}."), None
        duplicated = [column for column in self.allowed_columns if occurrences[column] > 1]
        if duplicated:
            return (DuplicateColumnError, f"colunas repetidas no cabeçalho: {duplicated}."), None
        indices = [(column, header.index(column)) for column in self.allowed_columns]
        return None, (indices, len(header), set(header) - set(self.allowed_columns))

    def _read_item(self, zf, info, indices, width):
        with self._open_text(zf, info) as text:
            reader = csv.reader(self._lines(text), delimiter=self.delimiter)
            next(reader, None)  # cabeçalho, já validado
            previous = reader.line_num
            for record in reader:
                physical = reader.line_num - previous
                previous = reader.line_num
                if not record:
                    continue
                self.rows_read += physical
                multiline = False
                if len(record) != width or multiline:
                    self.rejected_rows += physical
                    continue
                yield info.filename, {column: record[index] for column, index in indices}


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
