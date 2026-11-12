"""Retirada pela fonte e lápide, só para o TSE (ADR 0005, decisão 9; ADR 0026).

Uma candidatura já normalizada que NÃO está numa carga íntegra (execução `succeeded` com
linhas, a única que `normalize` recebe) foi retirada pela fonte: some da interface e da API (a
linha é apagada, junto com a pessoa se for a última candidatura dela), as linhas brutas dela
somem das cargas retidas e fica uma lápide só com ids. Falha técnica e "arquivo igual" nunca
chegam aqui: não geram carga com linhas.

Disjuntor: apagar é irreversível e a fonte pode publicar um arquivo "íntegro" mas incompleto.
Mais de `max(20, 1% das candidaturas já normalizadas)` retiradas numa carga recusam a
normalização inteira, até o dono rodar `normalize_tse --aceitar-retiradas`. O limite é
escolha minha, não medida (só há um dia de dados do TSE).

Mensagens citam só contagens, nunca valores. Deputado da Câmara não passa por aqui (ADR 0022).
"""

from django.db import transaction
from django.utils import timezone

from apps.sources.models import RawRecord, Tombstone
from apps.sources.normalization import NormalizationRefused

from .models import Candidacy, Person

MIN_LIMIT = 20
LIMIT_PERCENT = 1
READ_CHUNK = 2000
DELETE_CHUNK = 1000


class RetirementsHeld(NormalizationRefused):
    """O disjuntor segurou a carga. A mensagem é segura: só contagens."""

    def __init__(self, count, limit):
        super().__init__(
            f"Normalização recusada: {count} candidaturas sumiram do arquivo (limite {limit}). "
            "Nada foi gravado nem apagado. Se a retirada é legítima, rode "
            "normalize_tse --aceitar-retiradas."
        )


def make_key(cycle_year, candidate_id, election_code, round_):
    """Id de origem da candidatura: só números da fonte, nenhum dado pessoal."""
    return f"{cycle_year}:{candidate_id}:{election_code}:{round_}"


def present_keys(candidacies):
    """Chaves das candidaturas de uma carga (as chaves de `_Collected.candidacies`)."""
    return {
        make_key(cycle, candidate_id, code, round_)
        for (code, round_), (cycle, candidate_id) in candidacies
    }


def _stored(dataset):
    """Candidaturas já normalizadas deste conjunto: (pk, pessoa, chave)."""
    rows = Candidacy.objects.filter(ingestion_run__dataset=dataset).values_list(
        "pk",
        "person_id",
        "person__cycle_year",
        "person__tse_candidate_id",
        "election__tse_code",
        "election__round",
    )
    return [(pk, person_id, make_key(*parts)) for pk, person_id, *parts in rows]


def plan(dataset, present, accept):
    """Chaves retiradas por esta carga; levanta `RetirementsHeld` acima do limite.

    Deve rodar ANTES de qualquer gravação: se levantar, nada foi mexido.
    """
    stored = _stored(dataset)
    missing = {key for _, _, key in stored} - present
    limit = max(MIN_LIMIT, len(stored) * LIMIT_PERCENT // 100)
    if len(missing) > limit and not accept:
        raise RetirementsHeld(len(missing), limit)
    return missing


def _raw_key(values):
    """Chave de uma linha do bruto, ou `None` se ela não tem os números esperados."""
    try:
        return make_key(
            int(values["ANO_ELEICAO"]),
            int(values["SQ_CANDIDATO"]),
            int(values["CD_ELEICAO"]),
            int(values["NR_TURNO"]),
        )
    except KeyError, TypeError, ValueError:
        return None


def erase(dataset, keys):
    """Apaga candidaturas, pessoas órfãs e linhas brutas das chaves. Idempotente.

    Devolve `(candidaturas, pessoas, linhas_brutas)` apagadas. A leitura do bruto é uma
    varredura das cargas retidas do conjunto (só roda quando há o que apagar; custo não
    medido): é lenta de propósito, mas não depende de o valor estar formatado de um jeito só.
    """
    if not keys:
        return 0, 0, 0
    with transaction.atomic():
        hits = [(pk, person_id) for pk, person_id, key in _stored(dataset) if key in keys]
        Candidacy.objects.filter(pk__in=[pk for pk, _ in hits]).delete()
        persons, _ = Person.objects.filter(
            pk__in={person_id for _, person_id in hits}, candidacies__isnull=True
        ).delete()
        raw = _erase_raw(dataset, keys)
    return len(hits), persons, raw


def _erase_raw(dataset, keys):
    pending, erased = [], 0
    rows = RawRecord.objects.filter(run__dataset=dataset).values_list("pk", "values")
    for pk, values in rows.iterator(chunk_size=READ_CHUNK):
        if _raw_key(values) in keys:
            pending.append(pk)
            if len(pending) >= DELETE_CHUNK:
                erased += RawRecord.objects.filter(pk__in=pending).delete()[0]
                pending = []
    if pending:
        erased += RawRecord.objects.filter(pk__in=pending).delete()[0]
    return erased


def apply(run, missing, present):
    """Efetiva a retirada e atualiza as lápides. Roda na mesma transação da normalização.

    Registra as lápides das chaves retiradas (reabrindo uma reativada) e marca como reativadas
    as ativas cujo registro voltou na carga. Devolve quantas candidaturas foram retiradas.
    """
    dataset = run.dataset
    now = timezone.now()
    active = set(
        Tombstone.objects.filter(dataset=dataset, reinstated_at__isnull=True).values_list(
            "source_key", flat=True
        )
    )
    back = active & present
    if back:
        Tombstone.objects.filter(
            dataset=dataset, source_key__in=back, reinstated_at__isnull=True
        ).update(reinstated_at=now)

    retired, _, _ = erase(dataset, missing)
    Tombstone.objects.bulk_create(
        [
            Tombstone(
                dataset=dataset,
                source_key=key,
                retired_at=now,
                retired_in_run=run,
                reinstated_at=None,
            )
            for key in missing
        ],
        update_conflicts=True,
        unique_fields=["dataset", "source_key"],
        update_fields=["retired_at", "retired_in_run", "reinstated_at"],
    )
    return retired


def active_keys(dataset):
    """Chaves das lápides ativas (não reativadas) do conjunto."""
    return set(
        Tombstone.objects.filter(dataset=dataset, reinstated_at__isnull=True).values_list(
            "source_key", flat=True
        )
    )
