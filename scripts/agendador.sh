#!/usr/bin/env bash
# Agendador da coleta (ADR 0023, 0024): chama `collect_due` a cada minuto e grava um batimento.
# O minuto sorteado do ADR 0008 só vale com disparo a cada minuto; por isso um laço, alinhado ao
# começo do minuto. Erro do comando não derruba o laço (o `collect_due` sai com erro quando uma
# normalização é recusada, e a coleta seguinte tem de continuar).
#
# Variáveis (só para teste; em produção valem os padrões):
#   AGENDADOR_COMANDO    comando chamado a cada volta (padrão: python manage.py collect_due)
#   AGENDADOR_VOLTAS     para depois de N voltas (padrão: 0 = não para nunca)
#   AGENDADOR_ESPERA     segundos entre voltas (padrão: o que falta para o próximo minuto)
#   AGENDADOR_BATIMENTO  arquivo tocado ao fim de cada volta (padrão: /tmp/batimento)
set -u

comando=${AGENDADOR_COMANDO:-python manage.py collect_due}
voltas=${AGENDADOR_VOLTAS:-0}
batimento=${AGENDADOR_BATIMENTO:-/tmp/batimento}
feitas=0

while :; do
  # shellcheck disable=SC2086  # o comando é uma linha simples, dividida de propósito
  $comando || echo "agendador: o comando terminou com erro (código $?)" >&2
  touch "$batimento"
  feitas=$((feitas + 1))
  if [ "$voltas" -gt 0 ] && [ "$feitas" -ge "$voltas" ]; then
    break
  fi
  sleep "${AGENDADOR_ESPERA:-$((60 - 10#$(date +%S)))}"
done
