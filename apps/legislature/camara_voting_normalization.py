"""Normaliza o bruto de `camara/votacoes-2026` e `camara/votos-2026` em `CamaraVoting` e
`CamaraVote` (ADR 0005 e 0031).

Mesmas regras de `senate_voting_normalization`, com uma diferença que vem da fonte: são DOIS
conjuntos (dois arquivos), cada um com a sua carga, e a normalização lê a mais recente de cada um:
- Não faz requisição de rede. Linha inválida (em qualquer dos dois) ou conflito param tudo.
- Linhas idênticas viram uma; a mesma chave com dados diferentes é conflito: a mesma votação, ou
  o mesmo voto (votação + deputado).
- Falha fechada: nada é gravado se algo recusa. A gravação é uma só transação.
- Idempotente: upsert pela chave, então a fonte que corrige descrição, aprovação ou voto atualiza.
- Nunca apaga. O voto não aponta para `Deputy`.
- As mensagens de erro citam só nomes de coluna e contagens, nunca valores.

A corrida entre as duas coletas: o agendador coleta cada conjunto em hora sorteada e normaliza
depois de cada coleta, então o arquivo de votos pode chegar antes do de votações. Voto sem votação
só é recusa quando a carga de votações é tão nova quanto a de votos ou mais (a votação deveria
estar lá); se a de votos é mais nova por até 48 h, `normalize_latest` levanta `NormalizationWaiting`
e espera a coleta de votações. Nesse caso o agendador não grava sucesso nem erro: o resultado da
última normalização fica como estava no painel das fontes. Passadas as 48 h (votações paradas,
conjunto desabilitado, votação que não vem), vira recusa.
Compara o início das duas execuções que gravaram linhas, ou seja, a última vez que cada arquivo
MUDOU: "arquivo igual" não cria execução com linhas.

O código dos senadores e das votações do Senado foi copiado, não generalizado (como o ADR 0022 já
fez): a duplicação é candidata a refatoração depois. Duas normalizações simultâneas continuam sem
trava.
"""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import timedelta

from django.db import transaction

from apps.sources.models import Dataset, IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused
from apps.sources.normalization import NormalizationWaiting

from .camara_voting_parsing import parse_vote, parse_voting
from .models import CamaraVote, CamaraVoting
from .parsing import RowError

SOURCE_SLUG = "camara"
VOTINGS_SLUG = "votacoes-2026"
VOTES_SLUG = "votos-2026"
BATCH_SIZE = 1000
READ_CHUNK = 2000
# A espera por votações acaba depois de 48 h (dois ciclos de coleta): passado isso, voto sem
# votação é anomalia e aparece como recusa.
MAX_WAIT = timedelta(hours=48)
# Teto de linhas por carga, medido contra o real (9.153 votações e 57.855 votos em 2026; até
# ~175 mil votos em 2025): a normalização guarda tudo em memória.
MAX_VOTINGS = 50_000
MAX_VOTES = 500_000
VOTING_UPDATABLE = [
    "voted_on",
    "organ_acronym",
    "approval",
    "total_yes",
    "total_no",
    "total_other",
    "description",
    "proposition_id",
    "ingestion_run",
]
VOTE_UPDATABLE = ["legislature_id", "party_acronym", "vote", "ingestion_run"]


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


class RunTooLargeError(NormalizationRefused):
    def __init__(self, votings, votes):
        super().__init__(
            "Normalização recusada: carga acima do limite de linhas "
            f"(votações: {votings}, votos: {votes}). Nada foi gravado."
        )


class MissingVotingError(NormalizationRefused):
    def __init__(self, votes):
        super().__init__(
            f"Normalização recusada: votos sem votação na carga de votações: {votes}. "
            "Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    """`rows_read`, `created` e `existing` seguem o contrato do agendador (ADR 0023).

    `rows_read` soma as linhas das duas cargas; `created` e `existing` contam os votos.
    `datasets` são os conjuntos que a normalização leu (só `normalize_latest` os preenche): o
    agendador grava o sucesso em todos, não só no que disparou o passo (P-21).
    """

    rows_read: int
    unique: int
    created: int
    existing: int
    votings_created: int
    datasets: tuple = ()


def find_datasets():
    """`(conjunto de votações, conjunto de votos)`; cada um é `None` se não foi cadastrado."""
    datasets = Dataset.objects.filter(source__slug=SOURCE_SLUG, slug__in=[VOTINGS_SLUG, VOTES_SLUG])
    by_slug = {dataset.slug: dataset for dataset in datasets}
    return by_slug.get(VOTINGS_SLUG), by_slug.get(VOTES_SLUG)


def latest_run(dataset):
    """Execução bem-sucedida mais recente que gravou linhas (arquivo igual grava 0)."""
    return (
        IngestionRun.objects.filter(
            dataset=dataset, state=IngestionRun.State.SUCCEEDED, rows_loaded__gt=0
        )
        .order_by("-started_at", "-pk")
        .first()
    )


def normalize(votings_run, votes_run):
    if votings_run.rows_loaded > MAX_VOTINGS or votes_run.rows_loaded > MAX_VOTES:
        raise RunTooLargeError(votings_run.rows_loaded, votes_run.rows_loaded)
    rows_read, votings, votes = _collect(votings_run, votes_run)
    return _write(votings_run, votes_run, rows_read, votings, votes)


def normalize_latest(dataset):
    """O passo que o agendador encadeia, depois da coleta de QUALQUER dos dois conjuntos.

    `dataset` não decide nada: a normalização usa a carga mais recente de cada conjunto. Devolve
    `None` se falta uma das cargas ou se as duas já foram normalizadas (alguma votação aponta para
    a de votações e algum voto para a de votos). Levanta `NormalizationWaiting` se a carga de votos
    é mais nova que a de votações por até 48 h e há voto sem votação (espera a coleta de votações):
    `None` quer dizer "em dia", e a espera não está em dia.
    """
    votings_dataset, votes_dataset = find_datasets()
    if votings_dataset is None or votes_dataset is None:
        return None
    votings_run = latest_run(votings_dataset)
    votes_run = latest_run(votes_dataset)
    if votings_run is None or votes_run is None:
        return None
    if (
        CamaraVoting.objects.filter(ingestion_run=votings_run).exists()
        and CamaraVote.objects.filter(ingestion_run=votes_run).exists()
    ):
        return None
    try:
        result = normalize(votings_run, votes_run)
    except MissingVotingError:
        if timedelta(0) < votes_run.started_at - votings_run.started_at <= MAX_WAIT:
            raise NormalizationWaiting from None
        raise
    return replace(result, datasets=(votings_dataset, votes_dataset))


def _rows(run):
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    return rows.iterator(chunk_size=READ_CHUNK)


def _collect(votings_run, votes_run):
    """Lê, valida e deduplica o bruto das duas cargas. Não toca nas tabelas normalizadas."""
    invalid = Counter()
    voting_conflicts = 0
    vote_conflicts = 0
    votings = {}
    votes = {}
    rows_read = 0
    for values in _rows(votings_run):
        rows_read += 1
        try:
            voting = parse_voting(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        code = voting["camara_voting_id"]
        if code not in votings:
            votings[code] = voting
        elif votings[code] != voting:
            voting_conflicts += 1
    for values in _rows(votes_run):
        rows_read += 1
        try:
            code, vote = parse_vote(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        key = (code, vote["camara_id"])
        if key not in votes:
            votes[key] = vote
        elif votes[key] != vote:
            vote_conflicts += 1
    if invalid:
        raise InvalidRowsError(invalid)
    if voting_conflicts or vote_conflicts:
        raise ConflictError(voting_conflicts, vote_conflicts)
    orphans = sum(1 for code, _ in votes if code not in votings)
    if orphans:
        raise MissingVotingError(orphans)
    return rows_read, votings, votes


def _write(votings_run, votes_run, rows_read, votings, votes):
    voting_objects = [CamaraVoting(ingestion_run=votings_run, **v) for v in votings.values()]
    with transaction.atomic():
        votings_before = CamaraVoting.objects.count()
        for start in range(0, len(voting_objects), BATCH_SIZE):
            CamaraVoting.objects.bulk_create(
                voting_objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["camara_voting_id"],
                update_fields=VOTING_UPDATABLE,
            )
        votings_created = CamaraVoting.objects.count() - votings_before
        ids = {}
        codes = list(votings)
        for start in range(0, len(codes), BATCH_SIZE):
            batch = codes[start : start + BATCH_SIZE]
            found = CamaraVoting.objects.filter(camara_voting_id__in=batch)
            ids.update(found.values_list("camara_voting_id", "pk"))
        vote_objects = [
            CamaraVote(voting_id=ids[code], ingestion_run=votes_run, **vote)
            for (code, _), vote in votes.items()
        ]
        votes_before = CamaraVote.objects.count()
        for start in range(0, len(vote_objects), BATCH_SIZE):
            CamaraVote.objects.bulk_create(
                vote_objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["voting", "camara_id"],
                update_fields=VOTE_UPDATABLE,
            )
        created = CamaraVote.objects.count() - votes_before
    unique = len(vote_objects)
    return Result(rows_read, unique, created, unique - created, votings_created)
