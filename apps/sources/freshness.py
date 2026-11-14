"""Situação de um conjunto de dados para o monitoramento (Etapa 0, plano da Sessão 74).

Função pura: recebe o estado do conjunto e o relógio e devolve uma `Situation`. Não lê o banco
nem o relógio do sistema, então a mesma regra serve ao admin hoje e a um comando de checagem ou
a um alerta depois. Ordem das regras:

1. Desabilitado vence tudo; depois, sem intervalo de coleta ("sem agenda").
2. A última execução concluída ter falhado aparece antes do atraso: é o motivo mais útil.
3. Atrasado é passar de `LATE_FACTOR` intervalos sem coleta bem-sucedida. Dois intervalos cobrem
   uma tentativa perdida e o retentar do agendador (`RETRY_HOURS`, em `scheduling.py`).
4. Conjunto que nunca coletou só é atrasado se a próxima coleta venceu há mais de `LATE_FACTOR`
   intervalos; recém-habilitado ainda não tem data e está "em dia".
"""

from datetime import timedelta

from django.db import models

LATE_FACTOR = 2


class Situation(models.TextChoices):
    ON_TIME = "on_time", "Em dia"
    LATE = "late", "Atrasado"
    FAILED = "failed", "Última coleta falhou"
    NO_SCHEDULE = "no_schedule", "Sem agenda"
    DISABLED = "disabled", "Desabilitado"


def situation(
    *,
    enabled,
    interval_hours,
    next_collection_at,
    last_success_at,
    last_finished_state,
    now,
):
    """`last_finished_state`: estado da última execução concluída (`succeeded` ou `failed`)."""
    if not enabled:
        return Situation.DISABLED
    if interval_hours is None:
        return Situation.NO_SCHEDULE
    if last_finished_state == "failed":
        return Situation.FAILED

    tolerance = timedelta(hours=LATE_FACTOR * interval_hours)
    if last_success_at is None:
        overdue = next_collection_at is not None and now - next_collection_at > tolerance
        return Situation.LATE if overdue else Situation.ON_TIME
    return Situation.LATE if now - last_success_at > tolerance else Situation.ON_TIME
