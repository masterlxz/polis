#!/usr/bin/env bash
# Uma execução do backup (ADR 0011, 0025): `pg_dump -Fc` -> `age` (chave PÚBLICA) -> S3.
# O remoto `destino` do rclone vem das variáveis RCLONE_CONFIG_DESTINO_* do Compose.
# O objeto vai primeiro com sufixo `.parcial` e só vira `.dump.age` quando o envio termina:
# um dump cortado nunca parece um backup válido. Depois do sucesso, poda os backups com data
# no nome mais antiga que BACKUP_RETENCAO_DIAS, só no prefixo `polis/`.
set -euo pipefail

: "${BACKUP_S3_BUCKET:?defina BACKUP_S3_BUCKET}"
: "${BACKUP_AGE_RECIPIENTS:?defina BACKUP_AGE_RECIPIENTS (chaves públicas age, separadas por vírgula)}"
retencao=${BACKUP_RETENCAO_DIAS:-14}
[[ $retencao =~ ^[0-9]+$ && $retencao -ge 1 ]] || { echo "BACKUP_RETENCAO_DIAS inválido: $retencao" >&2; exit 2; }

prefixo="destino:${BACKUP_S3_BUCKET}/polis"
nome="$(date -u +%Y-%m-%dT%H%M%SZ).dump.age"

destinatarios=()
IFS=, read -ra chaves <<<"$BACKUP_AGE_RECIPIENTS"
for chave in "${chaves[@]}"; do
  [[ $chave == age1* ]] || { echo "destinatário não parece uma chave pública age (age1...)" >&2; exit 2; }
  destinatarios+=(-r "$chave")
done

limpar_parcial() { rclone deletefile "$prefixo/$nome.parcial" 2>/dev/null || true; }
trap limpar_parcial ERR

pg_dump --format=custom --no-owner | age "${destinatarios[@]}" | rclone rcat "$prefixo/$nome.parcial"
rclone moveto "$prefixo/$nome.parcial" "$prefixo/$nome"
echo "backup: $nome enviado"

# Poda: só arquivos com nome no formato exato, só em polis/, só depois de um envio bem-sucedido.
corte=$(date -u -d "-${retencao} days" +%Y-%m-%d)
while IFS= read -r antigo; do
  [[ $antigo =~ ^([0-9]{4}-[0-9]{2}-[0-9]{2})T[0-9]{6}Z\.dump\.age$ ]] || continue
  if [[ ${BASH_REMATCH[1]} < $corte ]]; then
    rclone deletefile "$prefixo/$antigo"
    echo "backup: removido $antigo (anterior a $corte)"
  fi
done < <(rclone lsf --files-only "$prefixo/")
