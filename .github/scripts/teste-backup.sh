#!/usr/bin/env bash
# Testes do backup cifrado e da restauração (ADR 0011, 0025). Roda SÓ no CI (ADR 0009 do
# workspace), com a pilha de produção no ar e um S3 descartável (`rclone serve s3`).
# Pré-requisitos: COMPOSE_FILE="compose.prod.yaml:.github/ci/compose.backup.yaml", POSTGRES_PASSWORD,
# DJANGO_SECRET_KEY e BACKUP_* no ambiente, `db` e `s3` de pé.
set -euo pipefail

dc() { docker compose "$@"; }
# Roda um comando dentro da imagem de backup, ligada à rede do Compose e sem TTY.
no_backup() { dc run --rm -T --no-deps backup "$@"; }
rclone_s3() { no_backup rclone "$@"; }
psql_db() { dc exec -T db psql -U "$POSTGRES_USER" -d "${2:-$POSTGRES_DB}" -tAc "$1"; }
ok() { echo "ok: $*"; }
falha() { echo "::error::$*"; exit 1; }

MARCA="TOTP-CHAVE-DE-TESTE-9f3a1c7e5b2d"
PREFIXO="${BACKUP_S3_BUCKET}/polis"

# --- chaves age: A (certa) e B (errada), geradas dentro da imagem, sem instalar nada no runner
gerar_chave() { no_backup age-keygen 2>/dev/null; }
CHAVE_A=$(gerar_chave); CHAVE_B=$(gerar_chave)
PUB_A=$(grep -o 'age1[a-z0-9]*' <<<"$CHAVE_A" | head -1)
mkdir -p "$RUNNER_TEMP/chaves"
grep '^AGE-SECRET-KEY' <<<"$CHAVE_A" > "$RUNNER_TEMP/chaves/a.txt"
grep '^AGE-SECRET-KEY' <<<"$CHAVE_B" > "$RUNNER_TEMP/chaves/b.txt"
export BACKUP_AGE_RECIPIENTS="$PUB_A"

# --- dado de origem com marca reconhecível
psql_db "CREATE TABLE IF NOT EXISTS marca_ci (valor text); TRUNCATE marca_ci; INSERT INTO marca_ci VALUES ('$MARCA');"
ORIGEM_MIGRACOES=$(psql_db "SELECT count(*) FROM django_migrations")
test "$ORIGEM_MIGRACOES" -gt 0 || falha "o banco de origem não tem migrações"

# --- 1. backup gera exatamente um objeto .dump.age
no_backup bash scripts/backup.sh
OBJETOS=$(rclone_s3 lsf "destino:$PREFIX/")
echo "$OBJETOS"
test "$(grep -c '\.dump\.age$' <<<"$OBJETOS")" -eq 1 || falha "esperava 1 objeto .dump.age"
OBJETO=$(grep '\.dump\.age$' <<<"$OBJETOS" | tr -d '\r')
ok "backup gerou $OBJETO"

# --- 2. o objeto não é texto claro
mkdir -p "$RUNNER_TEMP/baixado"
rclone_s3 cat "destino:$PREFIX/$OBJETO" > "$RUNNER_TEMP/baixado/objeto.age"
test -s "$RUNNER_TEMP/baixado/objeto.age" || falha "objeto vazio"
if grep -aq 'PGDMP' "$RUNNER_TEMP/baixado/objeto.age"; then falha "o objeto contém a assinatura PGDMP (sem cifra)"; fi
if grep -aq "$MARCA" "$RUNNER_TEMP/baixado/objeto.age"; then falha "o objeto contém a marca em texto claro"; fi
head -c 22 "$RUNNER_TEMP/baixado/objeto.age" | grep -aq 'age-encryption.org' || falha "o objeto não tem o cabeçalho do age"
ok "objeto cifrado (sem PGDMP, sem a marca)"

# --- 3. chave errada não restaura e não cria banco
if AGE_IDENTITY=/chaves/b.txt no_backup bash scripts/restaurar.sh "$OBJETO" polis_errado; then
  falha "restaurou com a chave errada"
fi
test "$(psql_db "SELECT count(*) FROM pg_database WHERE datname='polis_errado'")" -eq 0 \
  || falha "a restauração com chave errada deixou um banco"
ok "chave errada recusada"

# --- 4. restaura de verdade num banco novo; origem intacta
AGE_IDENTITY=/chaves/a.txt no_backup bash scripts/restaurar.sh "$OBJETO" polis_restaurado
test "$(psql_db "SELECT valor FROM marca_ci" polis_restaurado)" = "$MARCA" || falha "marca ausente na restauração"
test "$(psql_db "SELECT count(*) FROM django_migrations" polis_restaurado)" -eq "$ORIGEM_MIGRACOES" \
  || falha "contagem de migrações diferente na restauração"
test "$(psql_db "SELECT count(*) FROM marca_ci")" -eq 1 || falha "o banco em uso foi alterado"
ok "restauração fiel; banco em uso intacto"

# --- 5. não sobrescreve banco existente sem --substituir
if AGE_IDENTITY=/chaves/a.txt no_backup bash scripts/restaurar.sh "$OBJETO" polis_restaurado; then
  falha "restaurou sobre um banco existente sem --substituir"
fi
if AGE_IDENTITY=/chaves/a.txt no_backup bash scripts/restaurar.sh "$OBJETO" "$POSTGRES_DB"; then
  falha "restaurou sobre o banco em uso sem --substituir"
fi
ok "banco existente protegido sem --substituir"

# --- 6. poda: só o prefixo polis/, só o mais velho que a retenção
rclone_s3 copyto "destino:$PREFIX/$OBJETO" "destino:$PREFIX/2020-01-01T000000Z.dump.age"
rclone_s3 copyto "destino:$PREFIX/$OBJETO" "destino:${BACKUP_S3_BUCKET}/outro/2020-01-01T000000Z.dump.age"
no_backup bash scripts/backup.sh
DEPOIS=$(rclone_s3 lsf "destino:$PREFIX/")
if grep -q '^2020-01-01' <<<"$DEPOIS"; then falha "a poda não removeu o backup antigo"; fi
grep -q "$OBJETO" <<<"$DEPOIS" || falha "a poda removeu o backup do dia"
rclone_s3 lsf "destino:${BACKUP_S3_BUCKET}/outro/" | grep -q '^2020-01-01' || falha "a poda apagou fora do prefixo polis/"
ok "poda respeita retenção e prefixo"

# --- 7. o laço sobrevive à falha do comando e deixa batimento
no_backup bash -c 'BACKUP_COMANDO=false BACKUP_VOLTAS=2 BACKUP_ESPERA=1 BACKUP_BATIMENTO=/tmp/b bash scripts/backup-laco.sh && test -f /tmp/b'
ok "laço do backup sobrevive a falha"
