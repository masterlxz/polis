"""Relevância das variantes da busca (spike, ADR 0012/0016). Só biblioteca padrão.

Uso: python3 recall.py URL_BASE VARIANTE [extra_query=""] [n=1000] [semente=7]
Para cada uma de n pessoas (nomes de consultas.txt) gera 4 consultas e confere se ALGUM dos 10 primeiros
resultados tem EXATAMENTE o mesmo nome do alvo (há homônimos: a conferência é por nome, não por id).
Tipos: exato | sem_acento (minúsculas, sem acento) | um_erro (1 letra a menos num sobrenome) | prefixo
(1º nome inteiro + 3 primeiras letras dos demais).
"""

import json
import random
import sys
import time
import unicodedata
import urllib.request
from urllib.parse import quote

base, variante = sys.argv[1], sys.argv[2]
extra = sys.argv[3] if len(sys.argv) > 3 else ""
n = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
rnd = random.Random(int(sys.argv[5]) if len(sys.argv) > 5 else 7)
NOMES = [x.strip() for x in open("consultas.txt", encoding="utf-8") if x.strip()]


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def um_erro(nome):
    partes = nome.split()
    idx = [i for i, p in enumerate(partes) if len(p) > 3]
    i = rnd.choice(idx)
    j = rnd.randrange(1, len(partes[i]) - 1)
    partes[i] = partes[i][:j] + partes[i][j + 1 :]
    return " ".join(partes)


def prefixo(nome):
    p = nome.split()
    return " ".join([p[0]] + [x[:3] for x in p[1:]])


GERA = {
    "exato": lambda s: s,
    "sem_acento": lambda s: sem_acento(s).lower(),
    "um_erro": um_erro,
    "prefixo": prefixo,
}

acertos = {k: 0 for k in GERA}
lat = {k: [] for k in GERA}
alvos = [rnd.choice(NOMES) for _ in range(n)]
for alvo in alvos:
    for tipo, f in GERA.items():
        q = f(alvo)
        t0 = time.perf_counter()
        with urllib.request.urlopen(f"{base}/api/busca/?q={quote(q)}&v={variante}{extra}", timeout=60) as r:
            itens = json.load(r)["itens"]
        lat[tipo].append(time.perf_counter() - t0)
        if any(i["nome_publico"] == alvo for i in itens[:10]):
            acertos[tipo] += 1

out = {"variante": variante, "extra": extra, "n": n}
for tipo in GERA:
    xs = sorted(lat[tipo])
    out[tipo] = {
        "recall_top10_pct": round(100 * acertos[tipo] / n, 1),
        "lat_mediana_ms_sem_carga": round(xs[len(xs) // 2] * 1000, 1),
        "lat_p95_ms_sem_carga": round(xs[int(len(xs) * 0.95)] * 1000, 1),
    }
print(json.dumps(out, ensure_ascii=False, indent=2))
