#!/usr/bin/env bash
# Restaura um backup (ADR 0025). Uso:
#   AGE_IDENTITY=/chaves/privada.txt restaurar.sh <objeto.dump.age> <banco_destino> [--substituir]
# A chave privada é um arquivo informado na hora; ela não existe no servidor de produção.
# Decifra ANTES de tocar em qualquer banco (chave errada ou objeto corrompido não deixam rastro).
# Nunca escreve sobre um banco que já existe sem `--substituir` (e o `dropdb` falha se o banco
# estiver em uso: pare o `web` e o `agendador` antes).
set -euo pipefail

objeto=${1:?uso: restaurar.sh <objeto.dump.age> <banco_destino> [--substituir]}
destino=${2:?uso: restaurar.sh <objeto.dump.age> <banco_destino> [--substituir]}
substituir=${3:-}
[[ -z $substituir || $substituir == --substituir ]] || { echo "terceiro argumento inválido: $substituir" >&2; exit 2; }
: "${AGE_IDENTITY:?defina AGE_IDENTITY (arquivo da chave privada)}"
: "${BACKUP_S3_BUCKET:?defina BACKUP_S3_BUCKET}"
[[ -r $AGE_IDENTITY ]] || { echo "não consigo ler AGE_IDENTITY: $AGE_IDENTITY" >&2; exit 2; }
[[ $objeto =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z\.dump\.age$ ]] || { echo "nome de objeto inválido: $objeto" >&2; exit 2; }
[[ $destino =~ ^[a-z_][a-z0-9_]*$ ]] || { echo "nome de banco inválido: $destino" >&2; exit 2; }

tmp=$(mktemp -d)
criado=0
limpar() {
  rm -rf "$tmp"
  # Se criamos o banco e a restauração falhou, não deixa um banco pela metade.
  if [[ $criado == 1 && ${restaurado:-0} != 1 ]]; then dropdb --if-exists "$destino" 2>/dev/null || true; fi
}
trap limpar EXIT

# 1. Decifra primeiro. O dump em claro fica só neste diretório temporário, apagado ao sair.
rclone cat "destino:${BACKUP_S3_BUCKET}/polis/$objeto" | age --decrypt -i "$AGE_IDENTITY" > "$tmp/dump"
[[ -s $tmp/dump ]] || { echo "dump vazio depois de decifrar" >&2; exit 1; }

# 2. Só então olha o destino.
existe=$(psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$destino'")
if [[ $existe == 1 ]]; then
  [[ $substituir == --substituir ]] || { echo "o banco $destino já existe; use --substituir (apaga o atual)" >&2; exit 1; }
  dropdb "$destino"
fi
createdb "$destino"
criado=1

pg_restore --no-owner --exit-on-error --dbname="$destino" "$tmp/dump"
restaurado=1
echo "restaurado em $destino a partir de $objeto"
echo "lembrete: antes de subir o web, rode 'manage.py apply_tombstones' (lápides da retirada pela fonte, ADR 0005 e 0026)"
