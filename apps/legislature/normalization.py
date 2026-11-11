"""Normaliza o bruto de `camara/deputados` em `Deputy` (ADR 0005, 0009, 0021 e 0022).

Regras (plano da Sessão 54, espelhando `apps/elections/normalization.py`):
- Lê a execução mais recente que gravou linhas; não faz requisição de rede.
- Linhas idênticas viram uma; a mesma chave (legislatura, id da Câmara) com dados diferentes para
  tudo.
- Falha fechada: linha inválida ou conflito não gravam nada. A gravação é uma só transação.
- Idempotente: upsert pela chave. Nunca apaga; quem some da lista fica com a execução antiga
  (a lápide e a saída do exercício são outra fatia).
- As mensagens de erro citam só nomes de coluna e contagens, nunca valores.

Atenção: duas normalizações simultâneas não são barradas (falta o agendador); o resultado seria o
mesmo conjunto de chaves, mas a contagem de "criadas" poderia sair errada.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import Dataset, IngestionRun, RawRecord

from .models import Deputy
from .parsing import RowError, parse_row

SOURCE_SLUG = "camara"
DATASET_SLUG = "deputados"
BATCH_SIZE = 1000
READ_CHUNK = 2000
KEY = ("legislature_id", "camara_id")
UPDATABLE = ["name", "party_acronym", "state", "ingestion_run"]


class NormalizationRefused(Exception):
    """A normalização parou antes de gravar. A mensagem é segura: sem valores de linha."""


class InvalidRowsError(NormalizationRefused):
    def __init__(self, invalid):
        columns = ", ".join(f"{column} ({n})" for column, n in sorted(invalid.items()))
        super().__init__(
            f"Normalização recusada: linhas inválidas: {sum(invalid.values())}; "
            f"colunas: {columns}. Nada foi gravado."
        )


class ConflictError(NormalizationRefused):
    def __init__(self, count):
        super().__init__(
            "Normalização recusada: dados conflitantes entre linhas do bruto "
            f"(deputados: {count}). Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    rows_read: int
    unique: int
    created: int
    existing: int


def find_dataset():
    return Dataset.objects.filter(source__slug=SOURCE_SLUG, slug=DATASET_SLUG).first()


def latest_run(dataset):
    """Execução bem-sucedida mais recente que gravou linhas (arquivo igual grava 0)."""
    return (
        IngestionRun.objects.filter(
            dataset=dataset, state=IngestionRun.State.SUCCEEDED, rows_loaded__gt=0
        )
        .order_by("-started_at", "-pk")
        .first()
    )


def normalize(run):
    rows_read, deputies = _collect(run)
    return _write(run, rows_read, deputies)


def _collect(run):
    """Lê, valida e deduplica o bruto de `run`. Não toca em `Deputy`."""
    invalid = Counter()
    conflicts = 0
    deputies = {}
    rows_read = 0
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    for values in rows.iterator(chunk_size=READ_CHUNK):
        rows_read += 1
        try:
            row = parse_row(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        key = tuple(row[name] for name in KEY)
        if key not in deputies:
            deputies[key] = row
        elif deputies[key] != row:
            conflicts += 1
    if invalid:
        raise InvalidRowsError(invalid)
    if conflicts:
        raise ConflictError(conflicts)
    return rows_read, deputies


def _write(run, rows_read, deputies):
    objects = [Deputy(ingestion_run=run, **row) for row in deputies.values()]
    with transaction.atomic():
        before = Deputy.objects.count()
        for start in range(0, len(objects), BATCH_SIZE):
            Deputy.objects.bulk_create(
                objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=list(KEY),
                update_fields=UPDATABLE,
            )
        created = Deputy.objects.count() - before
    unique = len(objects)
    return Result(rows_read, unique, created, unique - created)
