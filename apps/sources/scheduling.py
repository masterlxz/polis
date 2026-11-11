"""Agendador da coleta: decide quais conjuntos estão vencidos e os coleta (ADR 0008, decisão 6).

Não é um processo residente: `collect_due` roda quando alguém o chama (cron ou timer, a cada
minuto) e o estado todo vive em `Dataset.next_collection_at`. Regras (plano da Sessão 57):
- Entra o conjunto habilitado, com intervalo, de fonte em integração ou ativa.
- Conjunto nunca armado não coleta: sorteia a primeira data (assim ela também cai em minuto
  sorteado).
- Vencido: `next_collection_at` passou e a hora UTC já alcançou `earliest_hour_utc`.
- O sorteio mantém a hora do dia e só muda o minuto, sempre entre 1 e 59 e nunca múltiplo de 5
  (nunca horário redondo); se a hora ficar antes da janela, sobe para a hora da janela.
- Antes de coletar, o conjunto é reservado por um `UPDATE` condicional: quem perde a corrida pula
  o conjunto, e um processo que morre no meio volta a tentar em `RETRY_HOURS`.
- Falha esperada, portão recusado e erro inesperado voltam a tentar em `RETRY_HOURS`; só o
  erro inesperado faz o comando terminar com erro.
- Depois de uma coleta `succeeded` (inclusive "arquivo igual"), o conjunto é normalizado se
  tiver normalizador em `settings.NORMALIZERS`. Recusa ou erro na normalização não desfazem a
  coleta nem pausam o conjunto: o bruto fica, o comando termina com erro e a normalização é
  retentada na próxima coleta bem-sucedida.

Atenção: o minuto sorteado só vale se o disparo for a cada minuto; num disparo mais espaçado a
coleta cai no minuto do disparo. Uma coleta manual (`ingest_dataset`) ao mesmo tempo não é barrada.
"""

import random
from dataclasses import dataclass, field
from datetime import UTC, timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.module_loading import import_string

from .ingestion import IngestionError, ingest
from .models import Dataset, IngestionRun, Source
from .normalization import NormalizationRefused

RETRY_HOURS = 6
ALLOWED_MINUTES = [minute for minute in range(1, 60) if minute % 5]
SCHEDULABLE_STATUSES = (Source.Status.INTEGRATING, Source.Status.ACTIVE)


@dataclass
class Result:
    lines: list = field(default_factory=list)
    unexpected: int = 0
    normalization_failed: int = 0


def draw_next(now, hours, earliest_hour, rng):
    """Momento daqui a `hours` horas, na mesma hora do dia, com o minuto sorteado.

    Se a hora ficar antes de `earliest_hour`, sobe para essa hora.
    """
    candidate = (now.astimezone(UTC) + timedelta(hours=hours)).replace(
        minute=rng.choice(ALLOWED_MINUTES), second=0, microsecond=0
    )
    if candidate.hour < earliest_hour:
        candidate = candidate.replace(hour=earliest_hour)
    return candidate


def collect_due(client, *, now=None, rng=None):
    """Coleta os conjuntos vencidos com `client` (um só para todos) e devolve o resumo."""
    now = now or timezone.now()
    rng = rng or random.SystemRandom()
    result = Result()
    datasets = Dataset.objects.select_related("source").filter(
        enabled=True,
        schedule_interval_hours__isnull=False,
        source__status__in=SCHEDULABLE_STATUSES,
    )
    for dataset in list(datasets):
        _handle(dataset, client, now, rng, result)
    return result


def _claim(pk, seen, new):
    """Troca `next_collection_at` de `seen` para `new`; só um chamador concorrente consegue."""
    taken = Dataset.objects.filter(pk=pk, next_collection_at=seen)
    return taken.update(next_collection_at=new) == 1


def _stamp(moment):
    return f"{moment:%Y-%m-%d %H:%M} UTC"


def _handle(dataset, client, now, rng, result):
    name = str(dataset)
    earliest = dataset.earliest_hour_utc
    seen = dataset.next_collection_at

    if seen is None:
        first = draw_next(now, 1, earliest, rng)
        if _claim(dataset.pk, None, first):
            result.lines.append(f"{name}: armado, próxima {_stamp(first)}")
        return
    if seen > now or now.astimezone(UTC).hour < earliest:
        return

    retry = draw_next(now, RETRY_HOURS, earliest, rng)
    if not _claim(dataset.pk, seen, retry):
        return
    try:
        run = ingest(dataset, client)
    except ValueError:
        result.lines.append(f"{name}: recusado pelo portão, próxima {_stamp(retry)}")
        return
    except IngestionError:
        result.unexpected += 1
        result.lines.append(f"{name}: erro inesperado, próxima {_stamp(retry)}")
        return

    succeeded = run.state == IngestionRun.State.SUCCEEDED
    if succeeded:
        following = draw_next(now, dataset.schedule_interval_hours, earliest, rng)
        Dataset.objects.filter(pk=dataset.pk).update(next_collection_at=following)
    else:
        following = retry
    result.lines.append(
        f"{name}: {run.state}, erro {run.error_code or '-'}, próxima {_stamp(following)}"
    )
    if succeeded:
        _normalize(dataset, name, result)


def _normalize(dataset, name, result):
    """Normaliza o bruto de `dataset` se ele tiver normalizador registrado.

    Recusa (falha fechada) mostra a mensagem, que é segura por contrato; qualquer outra exceção
    vira uma linha genérica, porque a mensagem de um erro do banco cita valores da linha.
    """
    path = settings.NORMALIZERS.get(name)
    if path is None:
        return
    failed = False
    try:
        summary = import_string(path)(dataset)
    except NormalizationRefused as error:
        result.lines.append(f"{name}: normalização recusada: {error}")
        result.normalization_failed += 1
        return
    except Exception:
        failed = True
    if failed:
        result.lines.append(f"{name}: normalização falhou de forma inesperada")
        result.normalization_failed += 1
        return
    if summary is not None:
        result.lines.append(
            f"{name}: normalizado, linhas lidas {summary.rows_read}, "
            f"criadas {summary.created}, já existentes {summary.existing}"
        )
