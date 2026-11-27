"""Gerador de carga das páginas e das APIs das tramitações da Câmara (ADR 0010, 0035). Só biblioteca
padrão, taxa fixa (carga aberta), como `scripts/carga_busca/carga.py` (de onde vem `resumo`, que
calcula p50/p95/p99).

Uso: `python medir.py ALVO URL_BASE [rps=10] [duracao=60] [aquecimento=10] [semente=1]`, com `ALVO`
`front` (as páginas do Next.js) ou `api` (a API interna do Django). Cada alvo tem 6 classes, os
piores casos semeados por `.github/ci/semear_camara.py`: proposição pequena, proposição com 98
tramitações, ementa longa, votação pequena, votação com 213 proposições e proposição desconhecida
(404 esperado, e não conta como erro).

ANTES da carga, cada caminho tem de devolver o status esperado E um trecho esperado do corpo; se
não, sai com erro. Sem isso, uma medição que bate só em 404 ou em páginas de erro daria um p95
lindo e falso. Imprime um JSON com p50/p95/p99 por classe e no total, erros e o atraso máximo do
gerador (se ele atrasou, o número é do gerador, não do servidor).
"""

import http.client
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "carga_busca"))
from carga import resumo  # noqa: E402

# (classe, caminho, status esperado, trecho esperado no corpo ou None)
CLASSES_DO_FRONT = (
    ("proposicao_pequena", "/camara/proposicoes/14666/", 200, "PL 11/2003"),
    ("proposicao_98", "/camara/proposicoes/14670/", 200, "Tramitação 98 do pior caso"),
    ("ementa_longa", "/camara/proposicoes/14668/", 200, "Ler a ementa inteira"),
    ("votacao_pequena", "/camara/votacoes/9000001-1/", 200, "Ver tramitação (4)"),
    ("votacao_213", "/camara/votacoes/9000002-1/", 200, "Ver tramitação (98)"),
    ("desconhecida", "/camara/proposicoes/99999/", 404, None),
)
CLASSES_DA_API = (
    ("proposicao_pequena", "/internal/v1/camara/proposicoes/14666/", 200, '"PL 11/2003"'),
    (
        "proposicao_98",
        "/internal/v1/camara/proposicoes/14669/",
        200,
        "Tramitação 98 do pior caso",
    ),
    ("ementa_longa", "/internal/v1/camara/proposicoes/14668/", 200, "Dispõe sobre a organização"),
    ("votacao_pequena", "/internal/v1/camara/votacoes/9000001-1/", 200, '"total_tramitacoes": 4'),
    ("votacao_213", "/internal/v1/camara/votacoes/9000002-1/", 200, '"total_tramitacoes": 98'),
    ("desconhecida", "/internal/v1/camara/proposicoes/99999/", 404, None),
)
ALVOS = {"front": CLASSES_DO_FRONT, "api": CLASSES_DA_API}

_local = threading.local()


def _conexao(base):
    conexao = getattr(_local, "c", None)
    if conexao is None:
        destino = urlparse(base)
        conexao = _local.c = http.client.HTTPConnection(destino.hostname, destino.port, timeout=60)
    return conexao


def pedir(base, caminho):
    """(duração em segundos, status ou None se a rede falhou, corpo em texto)."""
    inicio = time.perf_counter()
    try:
        conexao = _conexao(base)
        conexao.request("GET", caminho)
        resposta = conexao.getresponse()
        corpo = resposta.read().decode("utf-8", "replace")
        return time.perf_counter() - inicio, resposta.status, corpo
    except Exception:  # noqa: BLE001 - qualquer falha de rede conta como erro da medição
        if getattr(_local, "c", None) is not None:
            _local.c.close()
        _local.c = None
        return time.perf_counter() - inicio, None, ""


def checar(base, classes):
    """Lista de falhas da checagem prévia (vazia se tudo certo)."""
    falhas = []
    for nome, caminho, esperado, trecho in classes:
        _, status, corpo = pedir(base, caminho)
        if status != esperado:
            falhas.append(f"{nome} {caminho}: esperava {esperado}, veio {status}")
        elif trecho is not None and trecho not in corpo:
            falhas.append(f"{nome} {caminho}: o corpo não tem {trecho!r}")
    return falhas


def main():
    alvo, base = sys.argv[1], sys.argv[2]
    rps = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    duracao = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    aquecimento = float(sys.argv[5]) if len(sys.argv) > 5 else 10
    rnd = random.Random(int(sys.argv[6]) if len(sys.argv) > 6 else 1)  # noqa: S311
    classes = ALVOS[alvo]

    falhas = checar(base, classes)
    if falhas:
        print("A checagem prévia falhou; nada foi medido:", file=sys.stderr)
        print("\n".join(falhas), file=sys.stderr)
        sys.exit(1)

    nomes = [c[0] for c in classes]
    tempos = {n: [] for n in nomes}
    erros = dict.fromkeys(nomes, 0)
    atrasos = []
    trava = threading.Lock()
    medindo = threading.Event()

    def uma(nome, caminho, esperado):
        dt, status, _ = pedir(base, caminho)
        if medindo.is_set():
            with trava:
                tempos[nome].append(dt)
                if status != esperado:
                    erros[nome] += 1

    with ThreadPoolExecutor(max_workers=64) as pool:
        inicio = time.perf_counter()
        total = int((aquecimento + duracao) * rps)
        for n in range(total):
            alvo_t = inicio + n / rps
            agora = time.perf_counter()
            if agora < alvo_t:
                time.sleep(alvo_t - agora)
            elif medindo.is_set():
                atrasos.append(agora - alvo_t)
            if not medindo.is_set() and time.perf_counter() - inicio >= aquecimento:
                medindo.set()
            nome, caminho, esperado, _ = rnd.choice(classes)
            pool.submit(uma, nome, caminho, esperado)

    todos = [t for n in nomes for t in tempos[n]]
    saida = {
        "alvo": alvo,
        "url": base,
        "rps_alvo": rps,
        "duracao_s": duracao,
        "atraso_max_do_gerador_ms": round(max(atrasos) * 1000, 1) if atrasos else 0,
        "total": resumo(todos, sum(erros.values())),
        "por_classe": {n: resumo(tempos[n], erros[n]) for n in nomes},
    }
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
