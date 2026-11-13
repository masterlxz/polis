"""Normaliza o bruto de `senado/votacoes` em `SenateVoting` e `SenateVote` (ADR 0005 e 0029).

Mesmas regras de `senate_normalization` (lista de senadores), com duas chaves: o código da votação
e (votação, código do parlamentar):
- Lê a execução mais recente que gravou linhas; não faz requisição de rede.
- Linhas idênticas viram uma; a mesma chave com dados diferentes para tudo (conflito), inclusive a
  mesma votação com dados diferentes entre linhas.
- Falha fechada: linha inválida ou conflito não gravam nada. A gravação é uma só transação.
- Idempotente: upsert pela chave, então a fonte que corrige resultado, ementa ou voto atualiza.
- Nunca apaga: votação ou voto que saiu da janela de coleta continua no banco.
- O voto não aponta para `Senator`: guarda código, nome, partido e UF do momento do voto.
- As mensagens de erro citam só nomes de coluna e contagens, nunca valores.

O código da lista de senadores foi copiado, não generalizado (como o ADR 0022 já fez): a duplicação
é candidata a refatoração depois. Duas normalizações simultâneas continuam sem trava.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import Dataset, IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused

from .models import SenateVote, SenateVoting
from .parsing import RowError
from .senate_voting_parsing import parse_row

SOURCE_SLUG = "senado"
DATASET_SLUG = "votacoes"
BATCH_SIZE = 1000
READ_CHUNK = 2000
VOTING_UPDATABLE = [
    "voted_on",
    "type_acronym",
    "number",
    "year",
    "identification",
    "summary",
    "result",
    "secret",
    "total_yes",
    "total_no",
    "total_abstention",
    "process_id",
    "matter_id",
    "ingestion_run",
]
VOTE_UPDATABLE = ["name", "party_acronym", "state", "vote_code", "ingestion_run"]


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
    def __init__(self, votings, votes):
        super().__init__(
            "Normalização recusada: dados conflitantes entre linhas do bruto "
            f"(votações: {votings}, votos: {votes}). Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    """`rows_read`, `created` e `existing` seguem o contrato do agendador (ADR 0023)."""

    rows_read: int
    unique: int
    created: int
    existing: int
    votings_created: int


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
    rows_read, votings, votes = _collect(run)
    return _write(run, rows_read, votings, votes)


def normalize_latest(dataset):
    """O passo que o agendador encadeia: normaliza a carga mais recente que ainda não foi.

    Devolve `None` se não há carga com linhas ou se ela já foi normalizada (alguma votação aponta
    para ela; a gravação é uma transação só, então ou todas apontam ou nenhuma).
    """
    run = latest_run(dataset)
    if run is None or SenateVoting.objects.filter(ingestion_run=run).exists():
        return None
    return normalize(run)


def _collect(run):
    """Lê, valida e deduplica o bruto de `run`. Não toca nas tabelas normalizadas."""
    invalid = Counter()
    voting_conflicts = 0
    vote_conflicts = 0
    votings = {}
    votes = {}
    rows_read = 0
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    for values in rows.iterator(chunk_size=READ_CHUNK):
        rows_read += 1
        try:
            voting, vote = parse_row(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        code = voting["session_voting_code"]
        if code not in votings:
            votings[code] = voting
        elif votings[code] != voting:
            voting_conflicts += 1
        key = (code, vote["senate_id"])
        if key not in votes:
            votes[key] = vote
        elif votes[key] != vote:
            vote_conflicts += 1
    if invalid:
        raise InvalidRowsError(invalid)
    if voting_conflicts or vote_conflicts:
        raise ConflictError(voting_conflicts, vote_conflicts)
    return rows_read, votings, votes


def _write(run, rows_read, votings, votes):
    voting_objects = [SenateVoting(ingestion_run=run, **v) for v in votings.values()]
    with transaction.atomic():
        votings_before = SenateVoting.objects.count()
        SenateVoting.objects.bulk_create(
            voting_objects,
            update_conflicts=True,
            unique_fields=["session_voting_code"],
            update_fields=VOTING_UPDATABLE,
        )
        votings_created = SenateVoting.objects.count() - votings_before
        ids = dict(
            SenateVoting.objects.filter(session_voting_code__in=list(votings)).values_list(
                "session_voting_code", "pk"
            )
        )
        vote_objects = [
            SenateVote(voting_id=ids[code], ingestion_run=run, **vote)
            for (code, _), vote in votes.items()
        ]
        votes_before = SenateVote.objects.count()
        for start in range(0, len(vote_objects), BATCH_SIZE):
            SenateVote.objects.bulk_create(
                vote_objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["voting", "senate_id"],
                update_fields=VOTE_UPDATABLE,
            )
        created = SenateVote.objects.count() - votes_before
    unique = len(vote_objects)
    return Result(rows_read, unique, created, unique - created, votings_created)
