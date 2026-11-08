"""Gerador de carga do spike (ADR 0015). Só biblioteca padrão. Taxa fixa (aberta), mistura 80% perfil / 20% busca.

Uso: python3 carga.py URL_BASE [rps=50] [duracao=60] [aquecimento=10] [semente=1] [fracao_busca=0.2] [extra_query=""] [dist=uniform|zipf]
Imprime um JSON com p50/p95/p99 por tipo, erros e a RSS máxima por contêiner (docker stats).
"""

import http.client
import json
import random
import re
import statistics
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlparse

N_PESSOAS = 300_000
# Nomes reais do conjunto sintético, exportados do banco (consultas.txt, um por linha).
NOMES = [x.strip() for x in open("consultas.txt", encoding="utf-8") if x.strip()]

_local = threading.local()


_ZIPF = None


def _escolhe(rnd, dist):
    """uniform: todos os nomes igualmente prováveis. zipf: peso 1/posição (SUPOSIÇÃO: tráfego real repete consultas)."""
    global _ZIPF
    if dist != "zipf":
        return rnd.choice(NOMES)
    if _ZIPF is None:
        acc, _ZIPF = 0.0, []
        for i in range(len(NOMES)):
            acc += 1.0 / (i + 1)
            _ZIPF.append(acc)
    x = rnd.random() * _ZIPF[-1]
    lo, hi = 0, len(_ZIPF) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if _ZIPF[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return NOMES[lo]


def consulta(rnd, dist="uniform"):
    """Nome + sobrenome, às vezes sem acento ou com uma letra a menos (erro de digitação)."""
    partes = _escolhe(rnd, dist).split()
    q = " ".join(partes[: rnd.choice((2, 3))])  # nome e 1º sobrenome, ou nome completo
    r = rnd.random()
    if r < 0.3:
        q = q.lower()
    elif r < 0.5 and len(q) > 6:
        i = rnd.randrange(2, len(q) - 2)
        q = q[:i] + q[i + 1 :]
    return q


def get(base, path):
    u = urlparse(base)
    c = getattr(_local, "c", None)
    if c is None:
        c = _local.c = http.client.HTTPConnection(u.hostname, u.port, timeout=30)
    t0 = time.perf_counter()
    try:
        c.request("GET", path)
        resp = c.getresponse()
        resp.read()
        ok = resp.status == 200
    except Exception:
        c.close()
        _local.c = None
        ok = False
    return time.perf_counter() - t0, ok


def amostrar_memoria(parar, saida):
    while not parar.is_set():
        out = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}"],
            capture_output=True,
            text=True,
        ).stdout
        for linha in out.splitlines():
            m = re.match(r"(\S+) ([\d.]+)(MiB|GiB|KiB) /", linha)
            if m and m.group(1).startswith("nextjs-"):
                v = float(m.group(2)) * {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[m.group(3)]
                saida[m.group(1)] = max(saida.get(m.group(1), 0), v)
        parar.wait(1)


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p))] * 1000, 1) if xs else None


def main():
    base = sys.argv[1]
    rps = float(sys.argv[2]) if len(sys.argv) > 2 else 50
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    aq = float(sys.argv[4]) if len(sys.argv) > 4 else 10
    rnd = random.Random(int(sys.argv[5]) if len(sys.argv) > 5 else 1)
    frac_busca = float(sys.argv[6]) if len(sys.argv) > 6 else 0.2
    extra = sys.argv[7] if len(sys.argv) > 7 else ""  # ex.: "&v=V2&c=1" (variante da busca)
    dist = sys.argv[8] if len(sys.argv) > 8 else "uniform"

    res = {"perfil": [], "busca": []}
    erros = {"perfil": 0, "busca": 0}
    atraso = []
    lock = threading.Lock()
    medir = threading.Event()

    def um(tipo, path):
        dt, ok = get(base, path)
        if medir.is_set():
            with lock:
                res[tipo].append(dt)
                if not ok:
                    erros[tipo] += 1

    mem = {}
    parar = threading.Event()
    th = None
    with ThreadPoolExecutor(max_workers=64) as ex:
        inicio = time.perf_counter()
        n = 0
        total = int((aq + dur) * rps)
        while n < total:
            alvo = inicio + n / rps
            agora = time.perf_counter()
            if agora < alvo:
                time.sleep(alvo - agora)
            elif medir.is_set():
                atraso.append(agora - alvo)
            if not medir.is_set() and time.perf_counter() - inicio >= aq:
                medir.set()
                th = threading.Thread(target=amostrar_memoria, args=(parar, mem), daemon=True)
                th.start()
            if rnd.random() >= frac_busca:
                ex.submit(um, "perfil", f"/perfil/{rnd.randint(1, N_PESSOAS)}/")
            else:
                ex.submit(um, "busca", f"/busca/?q={quote(consulta(rnd, dist))}{extra}")
            n += 1
    parar.set()
    if th:
        th.join()

    out = {
        "url": base,
        "rps_alvo": rps,
        "duracao_s": dur,
        "atraso_max_do_gerador_ms": round(max(atraso) * 1000, 1) if atraso else 0,
    }
    for tipo in ("perfil", "busca"):
        xs = res[tipo]
        out[tipo] = {
            "n": len(xs),
            "erros": erros[tipo],
            "p50_ms": pct(xs, 0.5),
            "p95_ms": pct(xs, 0.95),
            "p99_ms": pct(xs, 0.99),
            "media_ms": round(statistics.mean(xs) * 1000, 1) if xs else None,
        }
    out["memoria_max_mib"] = {k: round(v, 1) for k, v in sorted(mem.items())}
    out["memoria_soma_mib"] = round(sum(mem.values()), 1)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
