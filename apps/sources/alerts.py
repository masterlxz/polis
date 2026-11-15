"""Alerta ativo das fontes (Etapa 0, plano da Sessão 76).

Avisa por MUDANÇA de situação, não por condição: "está atrasado" é verdade a cada minuto, e avisar a
cada minuto vira ruído que se aprende a ignorar. Cada `Dataset` lembra o último aviso
(`last_alert_situation`, `last_alert_at`) e, por conjunto, a regra é (`decide`):

1. situação ruim diferente do último aviso: **alerta** (piorou ou mudou);
2. situação ruim igual ao último aviso, e já passaram 24 h: **lembrete**;
3. situação que deixou de ser ruim, com aviso aberto: **recuperação**;
4. senão, nada.

`send_pending` junta tudo o que precisa de aviso numa mensagem só (4 conjuntos ruins = 1 aviso) e
só grava que avisou DEPOIS de o envio dar certo: se o webhook estiver fora do ar o aviso não se
perde, e o pior caso é avisar de novo na volta seguinte.

A mensagem leva só `fonte/conjunto`, a situação e, quando há, o rótulo do código de erro da coleta
ou a mensagem da recusa da normalização (segura por contrato: só colunas e contagens). Nunca a URL
do conjunto nem a do webhook.
"""

from dataclasses import dataclass
from datetime import timedelta

from . import monitoring
from .freshness import Situation
from .models import Dataset, IngestionRun
from .webhook import WebhookError

ALERT = "alert"
REMINDER = "reminder"
RECOVERY = "recovery"

REMINDER_AFTER = timedelta(hours=24)
BAD_SITUATIONS = frozenset({Situation.LATE, Situation.FAILED, Situation.NORMALIZATION_FAILED})


@dataclass
class Result:
    sent: int = 0
    failed: bool = False


def decide(*, situation, last_alert_situation, last_alert_at, now):
    """`ALERT`, `REMINDER`, `RECOVERY` ou `None` para um conjunto, nesta volta."""
    if situation in BAD_SITUATIONS:
        if last_alert_situation != situation.value or last_alert_at is None:
            return ALERT
        return REMINDER if now - last_alert_at >= REMINDER_AFTER else None
    return RECOVERY if last_alert_situation else None


def _detail(dataset, situation):
    if situation == Situation.NORMALIZATION_FAILED:
        return f" ({dataset.last_normalization_error})"
    if situation == Situation.FAILED and dataset.last_error_code:
        return f" ({IngestionRun.ErrorCode(dataset.last_error_code).label})"
    return ""


def _line(dataset, kind, situation):
    name = str(dataset)
    if kind == RECOVERY:
        return f"RECUPERADO {name}: agora {situation.label}"
    prefix = "ALERTA" if kind == ALERT else "LEMBRETE"
    return f"{prefix} {name}: {situation.label}{_detail(dataset, situation)}"


def send_pending(now, sender):
    """Manda os avisos devidos com `sender(texto)`; o estado só é gravado se o envio deu certo."""
    notices = []
    for dataset in monitoring.annotate(Dataset.objects.select_related("source")):
        situation = monitoring.situation_of(dataset, now)
        kind = decide(
            situation=situation,
            last_alert_situation=dataset.last_alert_situation,
            last_alert_at=dataset.last_alert_at,
            now=now,
        )
        if kind is not None:
            notices.append((dataset, kind, situation))
    if not notices:
        return Result()

    text = "\n".join(_line(dataset, kind, situation) for dataset, kind, situation in notices)
    try:
        sender(text)
    except WebhookError:
        return Result(failed=True)

    for dataset, kind, situation in notices:
        Dataset.objects.filter(pk=dataset.pk).update(
            last_alert_situation="" if kind == RECOVERY else situation.value,
            last_alert_at=now,
        )
    return Result(sent=len(notices))
