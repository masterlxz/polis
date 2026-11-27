"""Normaliza o bruto de `camara/proposicoes-tramitacoes-2026` em `CamaraPropositionStep` (ADR 0034,
Rodada 5 de `fontes/camara.md`).

Mesmas regras de `camara_proposition_normalization`, com as diferenças que vêm da medição de
2026-11-27:
- A chave é (proposição, `sequencia`, `dataHora`, `siglaOrgao`, `descricaoTramitacao`);
  `idTramitacao` não é lido (400 valores em 118.724 linhas). Duas linhas iguais na chave valem UMA
  e não são recusa (38 chaves em 2026, todas iguais na allowlist).
- Não há conflito possível: toda coluna lida faz parte da chave.
- Sem chave para `CamaraProposition` (a maioria das proposições do arquivo não está lá): guarda o
  id em texto e a junção é na leitura, então não há espera por outra coleta.

Não faz requisição de rede. Linha inválida para tudo. Falha fechada: a gravação é uma só
transação. Idempotente: upsert pela chave. Nunca apaga. As mensagens de erro citam só nomes de
coluna e contagens.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused

from .camara_tramitacao_parsing import parse_row
from .models import CamaraPropositionStep
from .parsing import RowError

SOURCE_SLUG = "camara"
DATASET_SLUG = "proposicoes-tramitacoes-2026"
BATCH_SIZE = 1000
READ_CHUNK = 2000
# Teto de linhas por carga (medido: 118.724 em 2026): a normalização guarda tudo em memória.
MAX_ROWS = 500_000
KEY = ["camara_proposition_id", "sequence", "occurred_at", "organ_code", "description"]
UPDATABLE = ["ingestion_run"]


class NormalizationRefused(SharedRefused):
    """A normalização parou antes de gravar. A mensagem é segura: sem valores de linha."""


class InvalidRowsError(NormalizationRefused):
    def __init__(self, invalid):
        columns = ", ".join(f"{column} ({n})" for column, n in sorted(invalid.items()))
        super().__init__(
            f"Normalização recusada: linhas inválidas: {sum(invalid.values())}; "
            f"colunas: {columns}. Nada foi gravado."
        )


class RunTooLargeError(NormalizationRefused):
    def __init__(self, rows):
        super().__init__(
            f"Normalização recusada: carga acima do limite de linhas ({rows}). Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    """`rows_read`, `created` e `existing` seguem o contrato do agendador (ADR 0023).

    `unique`, `created` e `existing` contam tramitações distintas na chave.
    """

    rows_read: int
    unique: int
    created: int
    existing: int


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
    if run.rows_loaded > MAX_ROWS:
        raise RunTooLargeError(run.rows_loaded)
    rows_read, steps = _collect(run)
    return _write(run, rows_read, steps)


def normalize_latest(dataset):
    """O passo que o agendador encadeia depois da coleta do conjunto.

    Devolve `None` se o conjunto não tem carga com linhas ou se a mais recente já foi normalizada
    (alguma tramitação aponta para ela).
    """
    run = latest_run(dataset)
    if run is None:
        return None
    if CamaraPropositionStep.objects.filter(ingestion_run=run).exists():
        return None
    return normalize(run)


def _rows(run):
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    return rows.iterator(chunk_size=READ_CHUNK)


def _collect(run):
    """Lê, valida e deduplica o bruto pela chave. Não toca nas tabelas normalizadas."""
    invalid = Counter()
    steps = {}
    rows_read = 0
    for values in _rows(run):
        rows_read += 1
        try:
            fields = parse_row(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        steps[tuple(fields[name] for name in KEY[:2])] = fields
    if invalid:
        raise InvalidRowsError(invalid)
    return rows_read, steps


def _write(run, rows_read, steps):
    objects = [CamaraPropositionStep(ingestion_run=run, **fields) for fields in steps.values()]
    with transaction.atomic():
        before = CamaraPropositionStep.objects.count()
        for start in range(0, len(objects), BATCH_SIZE):
            CamaraPropositionStep.objects.bulk_create(
                objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=KEY,
                update_fields=UPDATABLE,
            )
        created = CamaraPropositionStep.objects.count() - before
    unique = len(objects)
    return Result(rows_read, unique, created, unique - created)
