"""Situação dos conjuntos de dados lida do banco: o que o painel e o alerta têm em comum.

`freshness.py` é a regra pura; este módulo a alimenta com o que o banco sabe (última coleta com
sucesso e estado da última execução concluída, por subconsulta, sem N+1) e é o único lugar que
monta os argumentos dela. O painel do admin (`admin.py`) e o alerta (`alerts.py`) usam as mesmas
duas funções, então os dois nunca discordam sobre o que é "atrasado".
"""

from django.db.models import OuterRef, Subquery

from .freshness import situation
from .models import IngestionRun


def annotate(queryset):
    """Acrescenta ao queryset de `Dataset` o que a regra precisa e o painel mostra.

    Execução em andamento fica de fora: ela ainda não é sucesso nem falha.
    """
    finished = IngestionRun.objects.filter(dataset=OuterRef("pk")).exclude(
        state=IngestionRun.State.RUNNING
    )
    succeeded = finished.filter(state=IngestionRun.State.SUCCEEDED)
    latest_success = succeeded.order_by("-finished_at").values("finished_at")[:1]
    latest = finished.order_by("-finished_at", "-pk")
    return queryset.annotate(
        last_success_at=Subquery(latest_success),
        last_finished_state=Subquery(latest.values("state")[:1]),
        last_error_code=Subquery(latest.values("error_code")[:1]),
    )


def situation_of(dataset, now):
    """A `Situation` de um `Dataset` que passou por `annotate`."""
    return situation(
        enabled=dataset.enabled,
        interval_hours=dataset.schedule_interval_hours,
        next_collection_at=dataset.next_collection_at,
        last_success_at=dataset.last_success_at,
        last_finished_state=dataset.last_finished_state,
        normalization_failed=bool(dataset.last_normalization_error),
        now=now,
    )
