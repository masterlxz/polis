"""Normaliza o bruto de `camara/votacoes-proposicoes-2026` e `camara/votacoes-objetos-2026` em
`CamaraProposition` e `CamaraVotingProposition` (Rodada 4 de `fontes/camara.md`).

Mesmas regras de `camara_voting_normalization`, com duas diferenças que vêm da medição de
2026-11-26 (os dois arquivos não repetem nenhum par votação-proposição, e as 21 proposições comuns
têm dados idênticos):
- Cada arquivo é normalizado SOZINHO, a partir da carga mais recente do próprio conjunto. Entre os
  dois arquivos vale a última gravação; divergência entre eles não é recusa, para a espera de um
  arquivo não travar o outro.
- A ligação não tem chave para `CamaraVoting`: guarda o id da votação em texto e a junção é na
  leitura. Por isso não há espera por votação nem a corrida entre coletas do ADR 0031.

Não faz requisição de rede. Linha inválida ou conflito (a mesma proposição com dados diferentes
dentro do arquivo) param tudo. Falha fechada: a gravação é uma só transação. Idempotente: upsert
pela chave. Nunca apaga. As mensagens de erro citam só nomes de coluna e contagens.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused

from .camara_proposition_parsing import parse_row
from .models import CamaraProposition, CamaraVotingProposition
from .parsing import RowError

SOURCE_SLUG = "camara"
# slug do conjunto -> `origin` da ligação
ORIGIN_BY_SLUG = {
    "votacoes-proposicoes-2026": "proposicoes",
    "votacoes-objetos-2026": "objetos",
}
BATCH_SIZE = 1000
READ_CHUNK = 2000
# Teto de linhas por carga (medido: 7.160 e 39.416 em 2026): a normalização guarda tudo em memória.
MAX_ROWS = 500_000
PROPOSITION_UPDATABLE = ["title", "type_acronym", "number", "year", "ementa", "ingestion_run"]
LINK_UPDATABLE = ["origin", "ingestion_run"]


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
    def __init__(self, conflicts):
        super().__init__(
            "Normalização recusada: dados conflitantes entre linhas do bruto "
            f"(proposições: {conflicts}). Nada foi gravado."
        )


class RunTooLargeError(NormalizationRefused):
    def __init__(self, rows):
        super().__init__(
            f"Normalização recusada: carga acima do limite de linhas ({rows}). Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    """`rows_read`, `created` e `existing` seguem o contrato do agendador (ADR 0023).

    `unique`, `created` e `existing` contam proposições; `links_created` conta as ligações novas.
    """

    rows_read: int
    unique: int
    created: int
    existing: int
    links_created: int


def latest_run(dataset):
    """Execução bem-sucedida mais recente que gravou linhas (arquivo igual grava 0)."""
    return (
        IngestionRun.objects.filter(
            dataset=dataset, state=IngestionRun.State.SUCCEEDED, rows_loaded__gt=0
        )
        .order_by("-started_at", "-pk")
        .first()
    )


def normalize(run, origin):
    if run.rows_loaded > MAX_ROWS:
        raise RunTooLargeError(run.rows_loaded)
    rows_read, propositions, links = _collect(run)
    return _write(run, origin, rows_read, propositions, links)


def normalize_latest(dataset):
    """O passo que o agendador encadeia depois da coleta do conjunto.

    Devolve `None` se o conjunto não tem carga com linhas ou se a mais recente já foi normalizada
    (alguma ligação desta origem aponta para ela).
    """
    origin = ORIGIN_BY_SLUG[dataset.slug]
    run = latest_run(dataset)
    if run is None:
        return None
    if CamaraVotingProposition.objects.filter(ingestion_run=run, origin=origin).exists():
        return None
    return normalize(run, origin)


def _rows(run):
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    return rows.iterator(chunk_size=READ_CHUNK)


def _collect(run):
    """Lê, valida e deduplica o bruto. Não toca nas tabelas normalizadas."""
    invalid = Counter()
    conflicts = 0
    propositions = {}
    links = set()
    rows_read = 0
    for values in _rows(run):
        rows_read += 1
        try:
            voting_id, proposition = parse_row(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        code = proposition["camara_id"]
        if code not in propositions:
            propositions[code] = proposition
        elif propositions[code] != proposition:
            conflicts += 1
        links.add((voting_id, code))
    if invalid:
        raise InvalidRowsError(invalid)
    if conflicts:
        raise ConflictError(conflicts)
    return rows_read, propositions, links


def _write(run, origin, rows_read, propositions, links):
    proposition_objects = [
        CamaraProposition(ingestion_run=run, **fields) for fields in propositions.values()
    ]
    with transaction.atomic():
        before = CamaraProposition.objects.count()
        for start in range(0, len(proposition_objects), BATCH_SIZE):
            CamaraProposition.objects.bulk_create(
                proposition_objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["camara_id"],
                update_fields=PROPOSITION_UPDATABLE,
            )
        created = CamaraProposition.objects.count() - before
        ids = {}
        codes = list(propositions)
        for start in range(0, len(codes), BATCH_SIZE):
            batch = codes[start : start + BATCH_SIZE]
            found = CamaraProposition.objects.filter(camara_id__in=batch)
            ids.update(found.values_list("camara_id", "pk"))
        link_objects = [
            CamaraVotingProposition(
                camara_voting_id=voting_id,
                proposition_id=ids[code],
                origin=origin,
                ingestion_run=run,
            )
            for voting_id, code in sorted(links)
        ]
        links_before = CamaraVotingProposition.objects.count()
        for start in range(0, len(link_objects), BATCH_SIZE):
            CamaraVotingProposition.objects.bulk_create(
                link_objects[start : start + BATCH_SIZE],
                update_conflicts=True,
                unique_fields=["camara_voting_id", "proposition"],
                update_fields=LINK_UPDATABLE,
            )
        links_created = CamaraVotingProposition.objects.count() - links_before
    unique = len(proposition_objects)
    return Result(rows_read, unique, created, unique - created, links_created)
