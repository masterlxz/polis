#!/usr/bin/env bash
# Latência sob carga das variantes da busca (spike): só buscas, 10 buscas/s, 60 s medidos, 2 vCPU emulados.
# Pré-requisito: pilha base + meili no ar com CPUSET=0,1 (ver compose.yaml).
set -u
cd "$(dirname "$0")"
reps=${1:-3}
URL=http://127.0.0.1:8001
# rótulo|extra_query|distribuição
CASOS=(
  "V2|&v=V2|uniform"
  "V1|&v=V1|uniform"
  "V4|&v=V4|uniform"
  "V2cache-uniform|&v=V2&c=1|uniform"
  "V2cache-zipf|&v=V2&c=1|zipf"
  "V1cache-zipf|&v=V1&c=1|zipf"
)
for caso in "${CASOS[@]}"; do
  IFS='|' read -r rot extra dist <<<"$caso"
  # reinicia o Django para esvaziar o cache entre casos; a mesma configuração de CPU
  CPUSET=0,1 MEM_LIMIT=4g WORKERS=2 docker compose --profile base --profile meili up -d --force-recreate django-base >/dev/null 2>&1
  for _ in $(seq 1 60); do [ "$(curl -s -o /dev/null -w '%{http_code}' $URL/saude/)" = 200 ] && break; sleep 2; done
  taskset -c 4-7 python3 -I carga.py "$URL" 5 8 0 99 1.0 "$extra" "$dist" >/dev/null   # aquecimento
  for n in $(seq 1 "$reps"); do
    taskset -c 4-7 python3 -I carga.py "$URL" 10 60 10 "$n" 1.0 "$extra" "$dist" > "resultados/busca/carga-${rot}-r${n}.json"
    echo "feito ${rot}-r${n} loadavg_do_host=$(cut -d' ' -f1-3 /proc/loadavg)"
  done
done
echo FIM
