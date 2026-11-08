#!/usr/bin/env bash
# Mede o recall de cada variante, uma de cada vez, sem carga concorrente (spike da busca).
# n=100 alvos x 4 tipos = 400 consultas por variante (as de trigramas custam ~0,6 a 1,5 s cada).
set -u
cd "$(dirname "$0")"
for v in V2 V4 V1 V1w V0; do
  taskset -c 4-7 python3 -I recall.py http://127.0.0.1:8001 "$v" "" 100 7 > "resultados/busca/recall-$v.json" 2>"resultados/busca/recall-$v.err"
  echo "feito recall-$v"
done
echo FIM
