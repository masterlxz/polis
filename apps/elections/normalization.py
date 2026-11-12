"""Normaliza o bruto do TSE (`consulta-cand-2026`) em Election, Person e Candidacy.

Regras (ADR 0005 e ADR 0009, plano da Sessão 39):
- Lê a execução mais recente que gravou linhas; não faz requisição de rede.
- O bruto traz cada candidatura duas vezes (o `BRASIL.csv` repete os arquivos por UF, cópias
  idênticas, medido). Cópias iguais viram uma; qualquer conflito (cópias que divergem, eleição
  descrita de dois jeitos, mesmo `SQ_CANDIDATO` com dois nomes no ciclo) para tudo.
- Falha fechada: linha inválida ou conflito não gravam nada. A gravação é uma só transação.
- Idempotente: upsert pela chave. Só apaga pela retirada da fonte (ADR 0005, decisão 9;
  `retirement.py`): candidatura ausente de uma carga íntegra vira lápide, com disjuntor.
- As mensagens de erro citam só nomes de coluna e contagens, nunca valores.

Atenção: duas normalizações simultâneas não são barradas (falta o agendador); o resultado seria
o mesmo conjunto de chaves, mas a contagem de "criadas" poderia sair errada.
"""

from collections import Counter
from dataclasses import dataclass

from django.db import transaction

from apps.sources.models import Dataset, IngestionRun, RawRecord
from apps.sources.normalization import NormalizationRefused as SharedRefused

from . import retirement
from .models import Candidacy, Election, Person
from .retirement import RetirementsHeld  # noqa: F401  (reexportada: faz parte da interface)
from .tse import RowError, parse_row

SOURCE_SLUG = "tse"
DATASET_SLUG = "consulta-cand-2026"
BATCH_SIZE = 1000
READ_CHUNK = 2000


def _updatable(model, *keys):
    """Campos que o upsert reescreve: todos, menos a chave primária e a chave do conflito."""
    skip = {"id", *keys}
    return [field.name for field in model._meta.concrete_fields if field.name not in skip]


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
        detail = ", ".join(f"{name}: {n}" for name, n in sorted(conflicts.items()))
        super().__init__(
            f"Normalização recusada: dados conflitantes entre linhas do bruto ({detail}). "
            "Nada foi gravado."
        )


@dataclass(frozen=True)
class Result:
    rows_read: int
    unique: int
    created: int
    existing: int
    retired: int = 0


@dataclass(frozen=True)
class _Collected:
    rows_read: int
    elections: dict
    persons: dict
    candidacies: dict


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


def normalize(run, accept_retirements=False):
    """Normaliza `run`. Candidaturas que sumiram dela são retiradas (lápide, ADR 0005, dec. 9).

    Acima do limite do disjuntor a normalização inteira é recusada, a menos que
    `accept_retirements` (só o comando manual passa; o agendador nunca).
    """
    return _write(run, _collect(run), accept_retirements)


def normalize_latest(dataset):
    """O passo que o agendador encadeia: normaliza a carga mais recente que ainda não foi.

    Devolve `None` se não há carga com linhas ou se ela já foi normalizada (alguma candidatura
    aponta para ela; a gravação é uma transação só, então ou todas apontam ou nenhuma).
    """
    run = latest_run(dataset)
    if run is None or Candidacy.objects.filter(ingestion_run=run).exists():
        return None
    return normalize(run)


def _register(table, key, value, conflicts, name):
    if key in table:
        if table[key] != value:
            conflicts[name] += 1
    else:
        table[key] = value


def _collect(run):
    """Lê, valida e deduplica o bruto de `run`. Não toca nas tabelas normalizadas."""
    invalid, conflicts = Counter(), Counter()
    elections, persons, candidacies = {}, {}, {}
    rows_read = 0
    rows = RawRecord.objects.filter(run=run).values_list("values", flat=True)
    for values in rows.iterator(chunk_size=READ_CHUNK):
        rows_read += 1
        try:
            row = parse_row(values)
        except RowError as error:
            invalid[error.column] += 1
            continue
        election_key = (row.election["tse_code"], row.election["round"])
        person_key = (row.person["cycle_year"], row.person["tse_candidate_id"])
        _register(elections, election_key, row.election, conflicts, "eleições")
        _register(persons, person_key, row.person, conflicts, "pessoas")
        _register(candidacies, (election_key, person_key), row, conflicts, "candidaturas")
    if invalid:
        raise InvalidRowsError(invalid)
    if conflicts:
        raise ConflictError(conflicts)
    return _Collected(rows_read, elections, persons, candidacies)


def _upsert(model, objects, unique_fields):
    update_fields = _updatable(model, *unique_fields)
    for start in range(0, len(objects), BATCH_SIZE):
        model.objects.bulk_create(
            objects[start : start + BATCH_SIZE],
            update_conflicts=True,
            unique_fields=unique_fields,
            update_fields=update_fields,
        )


def _write(run, collected, accept_retirements=False):
    present = retirement.present_keys(collected.candidacies)
    with transaction.atomic():
        # Antes de gravar qualquer coisa: se o disjuntor levantar, nada foi mexido.
        missing = retirement.plan(run.dataset, present, accept_retirements)
        before = Candidacy.objects.count()

        _upsert(
            Election,
            [Election(**fields) for fields in collected.elections.values()],
            ["tse_code", "round"],
        )
        election_ids = {
            (code, round_): pk
            for code, round_, pk in Election.objects.values_list("tse_code", "round", "pk")
        }

        _upsert(
            Person,
            [Person(**fields) for fields in collected.persons.values()],
            ["cycle_year", "tse_candidate_id"],
        )
        cycles = {cycle for cycle, _ in collected.persons}
        saved_persons = Person.objects.filter(cycle_year__in=cycles)
        person_ids = {
            (cycle, candidate_id): pk
            for cycle, candidate_id, pk in saved_persons.values_list(
                "cycle_year", "tse_candidate_id", "pk"
            )
        }

        _upsert(
            Candidacy,
            [
                Candidacy(
                    election_id=election_ids[election_key],
                    person_id=person_ids[person_key],
                    ingestion_run=run,
                    **row.candidacy,
                )
                for (election_key, person_key), row in collected.candidacies.items()
            ],
            ["election", "person"],
        )
        created = Candidacy.objects.count() - before
        retired = retirement.apply(run, missing, present)

    unique = len(collected.candidacies)
    return Result(collected.rows_read, unique, created, unique - created, retired)
