#!/usr/bin/env bash
# Roda a matriz do spike: perfil (A: 2 vCPU/4 GB, B: 1 vCPU/2 GB) x pilha (base, alvo) x repetições.
# Uso: ./matriz.sh CENARIO FRACAO_BUSCA RPS [REPETICOES=2]    (CENARIO vira prefixo do arquivo em resultados/)
set -euo pipefail
cd "$(dirname "$0")"
cen=$1; frac=$2; rps=$3; reps=${4:-2}; perfis=${5:-A B}

esperar() { # URL
  for _ in $(seq 1 90); do
    [ "$(curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null)" = 200 ] && return 0
    sleep 2
  done
  echo "timeout esperando $1" >&2; return 1
}

for perfil in $perfis; do
  if [ "$perfil" = A ]; then export CPUSET=0,1 MEM_LIMIT=4g WORKERS=2; else export CPUSET=0 MEM_LIMIT=2g WORKERS=1; fi
  for pilha in base alvo; do
    docker compose --profile base --profile alvo down >/dev/null 2>&1
    docker compose --profile "$pilha" up -d >/dev/null 2>&1
    if [ "$pilha" = base ]; then url=http://127.0.0.1:8001; else url=http://127.0.0.1:3001; fi
    esperar "$url/perfil/1/"
    # aquecimento fora da medição (JIT/caches)
    taskset -c 4-7 python3 -I carga.py "$url" 20 5 0 99 "$frac" >/dev/null
    for n in $(seq 1 "$reps"); do
      taskset -c 4-7 python3 -I carga.py "$url" "$rps" 60 10 "$n" "$frac" > "resultados/${cen}-${pilha}-${perfil}-r${n}.json"
      echo "feito ${cen}-${pilha}-${perfil}-r${n} loadavg_do_host=$(cut -d' ' -f1-3 /proc/loadavg)"
    done
  done
done
docker compose --profile base --profile alvo down >/dev/null 2>&1
echo FIM
