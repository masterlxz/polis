"""Gerador de carga da busca (ADR 0010, 0016). Só biblioteca padrão, taxa fixa (carga aberta).

Uso: `python carga.py URL_BASE consultas.txt [rps=10] [duracao=60] [aquecimento=10] [semente=1]`.
Dispara `rps` buscas por segundo mesmo que as respostas demorem (como usuários reais; numa carga
fechada o sistema "se protege" e o p95 sai bonito demais). Cada consulta é de uma de 4 classes,
para separar o caminho dos tokens do da reserva por trigramas:
  exata (nome ou nome e sobrenome, caixa alta), minuscula (sem caixa alta), erro (uma letra a
  menos no meio: cai na reserva), prefixo (3 primeiras letras de cada palavra).
Imprime um JSON com p50/p95/p99 por classe e no total, erros e o atraso máximo do gerador.
"""

import http.client
import json
import random
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlparse

CLASSES = ("exata", "minuscula", "erro", "prefixo")
PESOS = (0.4, 0.2, 0.2, 0.2)

_local = threading.local()


def montar_consulta(rnd, nome, classe):
    palavras = nome.split()
    base = " ".join(palavras[: rnd.choice((2, 3))])
    if classe == "minuscula":
        return base.lower()
    if classe == "erro" and len(base) > 6:
        i = rnd.randrange(2, len(base) - 2)
        return base[:i] + base[i + 1 :]
    if classe == "prefixo":
        return " ".join(p[:3] for p in palavras[:2])
    return base


def buscar(base, caminho):
    destino = urlparse(base)
    conexao = getattr(_local, "c", None)
    if conexao is None:
        conexao = _local.c = http.client.HTTPConnection(destino.hostname, destino.port, timeout=30)
    inicio = time.perf_counter()
    try:
        conexao.request("GET", caminho)
        resposta = conexao.getresponse()
        resposta.read()
        ok = resposta.status == 200
    except Exception:  # noqa: BLE001 - qualquer falha de rede conta como erro da medição
        conexao.close()
        _local.c = None
        ok = False
    return time.perf_counter() - inicio, ok


def percentil(valores, p):
    if not valores:
        return None
    ordenado = sorted(valores)
    return round(ordenado[min(len(ordenado) - 1, int(len(ordenado) * p))] * 1000, 1)


def resumo(valores, erros):
    return {
        "n": len(valores),
        "erros": erros,
        "p50_ms": percentil(valores, 0.5),
        "p95_ms": percentil(valores, 0.95),
        "p99_ms": percentil(valores, 0.99),
        "media_ms": round(statistics.mean(valores) * 1000, 1) if valores else None,
    }


def main():
    base = sys.argv[1]
    with open(sys.argv[2], encoding="utf-8") as arquivo:
        nomes = [linha.strip() for linha in arquivo if linha.strip()]
    rps = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    duracao = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    aquecimento = float(sys.argv[5]) if len(sys.argv) > 5 else 10
    rnd = random.Random(int(sys.argv[6]) if len(sys.argv) > 6 else 1)  # noqa: S311

    tempos = {c: [] for c in CLASSES}
    erros = dict.fromkeys(CLASSES, 0)
    atrasos = []
    trava = threading.Lock()
    medindo = threading.Event()

    def uma(classe, caminho):
        dt, ok = buscar(base, caminho)
        if medindo.is_set():
            with trava:
                tempos[classe].append(dt)
                if not ok:
                    erros[classe] += 1

    with ThreadPoolExecutor(max_workers=64) as pool:
        inicio = time.perf_counter()
        total = int((aquecimento + duracao) * rps)
        for n in range(total):
            alvo = inicio + n / rps
            agora = time.perf_counter()
            if agora < alvo:
                time.sleep(alvo - agora)
            elif medindo.is_set():
                atrasos.append(agora - alvo)
            if not medindo.is_set() and time.perf_counter() - inicio >= aquecimento:
                medindo.set()
            classe = rnd.choices(CLASSES, PESOS)[0]
            consulta = montar_consulta(rnd, rnd.choice(nomes), classe)
            pool.submit(uma, classe, f"/internal/v1/busca/?q={quote(consulta)}")

    todos = [t for c in CLASSES for t in tempos[c]]
    saida = {
        "url": base,
        "rps_alvo": rps,
        "duracao_s": duracao,
        "atraso_max_do_gerador_ms": round(max(atrasos) * 1000, 1) if atrasos else 0,
        "total": resumo(todos, sum(erros.values())),
        "por_classe": {c: resumo(tempos[c], erros[c]) for c in CLASSES},
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
