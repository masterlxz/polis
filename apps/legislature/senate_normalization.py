"""Normaliza o bruto de `senado/senadores` em `Senator` (ADR 0005, 0009 e 0028).

Mesmas regras de `normalization` (Câmara), com a chave só no código do parlamentar:
- Lê a execução mais recente que gravou linhas; não faz requisição de rede.
- Linhas idênticas viram uma; o mesmo código com dados diferentes para tudo.
- Falha fechada: linha inválida ou conflito não gravam nada. A gravação é uma só transação.
- Idempotente: upsert pela chave. Nunca apaga; quem some da lista sai do exercício
  (`in_office=False`, `left_list_at` = início desta execução, ADR 0027); quem volta, volta. Só a
  carga MAIS RECENTE mexe nesse estado.
- As mensagens de erro citam só nomes de coluna e contagens, nunca valores.

O código da Câmara foi copiado, não generalizado (como o ADR 0022 já fez): a duplicação é
candidata a refatoração depois. Duas normalizações simultâneas continuam sem trava.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import Dataset, IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused

from .models import Senator
from .parsing import RowError
from .senate_parsing import parse_row

SOURCE_SLUG = "senado"
DATASET_SLUG = "senadores"
BATCH_SIZE = 1000
READ_CHUNK = 2000
KEY = ("senate_id",)
UPDATABLE = ["name", "party_acronym", "state", "ingestion_run"]
OFFICE_STATE = ["in_office", "left_list_at"]


class NormalizationRefused(SharedRefused):
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
            f"(senadores: {count}). Nada foi gravado."
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
    rows_read, senators = _collect(run)
    return _write(run, rows_read, senators)


def normalize_latest(dataset):
    """O passo que o agendador encadeia: normaliza a carga mais recente que ainda não foi.

    Devolve `None` se não há carga com linhas ou se ela já foi normalizada (algum senador aponta
    para ela; a gravação é uma transação só, então ou todos apontam ou nenhum).
    """
    run = latest_run(dataset)
    if run is None or Senator.objects.filter(ingestion_run=run).exists():
        return None
    return normalize(run)


def _collect(run):
    """Lê, valida e deduplica o bruto de `run`. Não toca em `Senator`."""
    invalid = Counter()
    conflicts = 0
    senators = {}
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
        if key not in senators:
            senators[key] = row
        elif senators[key] != row:
            conflicts += 1
    if invalid:
        raise InvalidRowsError(invalid)
    if conflicts:
        raise ConflictError(conflicts)
    return rows_read, senators


def _write(run, rows_read, senators):
    objects = [Senator(ingestion_run=run, **row) for row in senators.values()]
    latest = latest_run(run.dataset)
    is_latest = latest is not None and latest.pk == run.pk
    update_fields = UPDATABLE + OFFICE_STATE if is_latest else UPDATABLE
    with transaction.atomic():
        before = Senator.objects.count()
        for start in range(0, len(objects), BATCH_SIZE):
            Senator.objects.bulk_create(
                objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=list(KEY),
                update_fields=update_fields,
            )
        created = Senator.objects.count() - before
        if is_latest:
            # Quem estava em exercício e não veio nesta carga saiu da lista (nunca apaga).
            Senator.objects.filter(ingestion_run__dataset=run.dataset, in_office=True).exclude(
                ingestion_run=run
            ).update(in_office=False, left_list_at=__import__("django.utils.timezone").utils.timezone.now())
    unique = len(objects)
    return Result(rows_read, unique, created, unique - created)
