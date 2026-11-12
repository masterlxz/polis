#!/usr/bin/env bash
# Laço diário do backup (ADR 0025), no molde do agendador da coleta: dorme até 03:17 UTC, roda
# o backup, repete. Erro do comando não derruba o laço. O batimento só é renovado quando o
# backup TERMINA COM SUCESSO: se ele parar de funcionar, o healthcheck do serviço acusa.
#
# Variáveis (só para teste; em produção valem os padrões):
#   BACKUP_COMANDO     comando de cada volta (padrão: bash scripts/backup.sh)
#   BACKUP_VOLTAS      para depois de N voltas (padrão: 0 = não para nunca)
#   BACKUP_ESPERA      segundos antes de cada volta (padrão: até o próximo 03:17 UTC)
#   BACKUP_BATIMENTO   arquivo tocado após cada sucesso (padrão: /tmp/batimento)
set -u

comando=${BACKUP_COMANDO:-bash scripts/backup.sh}
voltas=${BACKUP_VOLTAS:-0}
batimento=${BACKUP_BATIMENTO:-/tmp/batimento}
feitas=0

# Sem isto o healthcheck acusaria falha logo na subida, antes da primeira volta.
[ -f "$batimento" ] || touch "$batimento"

espera_ate_o_horario() {
  local agora alvo
  agora=$(date -u +%s)
  alvo=$(date -u -d "today 03:17" +%s)
  [ "$alvo" -gt "$agora" ] || alvo=$(date -u -d "tomorrow 03:17" +%s)
  echo $((alvo - agora))
}

while :; do
  sleep "${BACKUP_ESPERA:-$(espera_ate_o_horario)}"
  # shellcheck disable=SC2086  # o comando é uma linha simples, dividida de propósito
  if $comando; then
    touch "$batimento"
  else
    echo "backup-laco: o comando terminou com erro (código $?)" >&2
  fi
  feitas=$((feitas + 1))
  if [ "$voltas" -gt 0 ] && [ "$feitas" -ge "$voltas" ]; then
    break
  fi
done
