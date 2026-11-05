"""Medição do spike de ingestão (descartável, roda só no CI).

`python medir.py executar` gera o ZIP sintético e mede, cada etapa num subprocesso
(para o pico de memória não vazar de uma etapa para outra):
  a: só descomprimir          b: ler + filtrar colunas (allowlist)
  c: SHA-256 do ZIP           d: COPY de uma amostra para o PostgreSQL (extrapolado)
Critérios (do plano; ajustáveis, pois o P-14 está em aberto): b + c em menos de 20 min
e pico de memória das etapas a, b e c abaixo de 500 MB.
"""
import json
import os
import resource
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gerar_zip_sintetico import gerar  # noqa: E402
from leitor import LeitorZip, sha256_arquivo  # noqa: E402

ALLOW = [
    "SQ_CANDIDATO", "NR_CANDIDATO", "NM_URNA_CANDIDATO", "NM_SOCIAL_CANDIDATO",
    "SG_PARTIDO", "SG_UF", "DS_CARGO", "DS_SIT_TOT_TURNO",
]
ZIP = Path(os.environ.get("SPIKE_ZIP", "/tmp/sintetico.zip"))
ALVO_GB = float(os.environ.get("SPIKE_ALVO_GB", "12"))
AMOSTRA_COPY = int(os.environ.get("SPIKE_AMOSTRA_COPY", "2000000"))
LIMITE_S = 20 * 60
LIMITE_MB = 500


def _resultado(nome, inicio, **extra):
    pico_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KiB no Linux
    print("RESULT " + json.dumps({"etapa": nome, "segundos": round(time.perf_counter() - inicio, 1),
                                  "pico_mb": round(pico_mb), **extra}))


def etapa_a():
    inicio, total = time.perf_counter(), 0
    with zipfile.ZipFile(ZIP) as zf:
        for info in zf.infolist():
            if info.filename.lower().endswith(".csv"):
                with zf.open(info) as f:
                    while pedaco := f.read(1024 * 1024):
                        total += len(pedaco)
    _resultado("a", inicio, bytes_descomprimidos=total)


def etapa_b():
    inicio, linhas = time.perf_counter(), 0
    leitor = LeitorZip(ZIP, ALLOW)
    for _ in leitor.linhas():
        linhas += 1
    _resultado("b", inicio, linhas=linhas, rejeitadas=leitor.rejeitadas,
               colunas_ignoradas=len(leitor.colunas_ignoradas))


def etapa_c():
    inicio = time.perf_counter()
    sha = sha256_arquivo(ZIP)
    _resultado("c", inicio, sha256=sha[:12], bytes_zip=ZIP.stat().st_size)


def etapa_d():
    import psycopg  # só aqui; instalado no CI

    inicio, gravadas = time.perf_counter(), 0
    colunas = ", ".join(f"{c.lower()} text" for c in ALLOW)
    nomes = ", ".join(c.lower() for c in ALLOW)
    with psycopg.connect(os.environ["PGURL"]) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS candidatos_spike")
            cur.execute(f"CREATE TABLE candidatos_spike ({colunas})")
            gerador = LeitorZip(ZIP, ALLOW).linhas()
            with cur.copy(f"COPY candidatos_spike ({nomes}) FROM STDIN") as copia:
                for _item, linha in gerador:
                    copia.write_row([linha[c] for c in ALLOW])
                    gravadas += 1
                    if gravadas >= AMOSTRA_COPY:
                        break
            gerador.close()
        conn.commit()  # uma transação: se algo falhasse antes, nada ficaria gravado
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM candidatos_spike")
            contadas = cur.fetchone()[0]
    _resultado("d", inicio, gravadas=gravadas, contadas=contadas)


def _rodar_etapa(nome):
    saida = subprocess.run([sys.executable, __file__, "etapa", nome], capture_output=True, text=True)
    print(saida.stdout[-2000:], end="")
    print(saida.stderr[-2000:], end="", file=sys.stderr)
    if saida.returncode != 0:
        raise SystemExit(f"etapa {nome} falhou (código {saida.returncode})")
    linha = [l for l in saida.stdout.splitlines() if l.startswith("RESULT ")][-1]
    return json.loads(linha[len("RESULT "):])


def executar():
    print(f"Gerando ZIP sintético (alvo {ALVO_GB} GB descomprimidos) em {ZIP} ...", flush=True)
    estat = gerar(ZIP, int(ALVO_GB * 1e9))
    with zipfile.ZipFile(ZIP) as zf:
        descomprimido = sum(i.file_size for i in zf.infolist())
    comprimido = ZIP.stat().st_size
    print(f"ZIP: {comprimido / 1e9:.2f} GB comprimido, {descomprimido / 1e9:.2f} GB descomprimido, "
          f"razão {descomprimido / comprimido:.1f}x, {estat['linhas']:,} linhas, gerado em {estat['segundos']} s", flush=True)

    r = {n: _rodar_etapa(n) for n in "abcd"}
    linhas = r["b"]["linhas"]
    mb_s = descomprimido / 1e6 / r["b"]["segundos"]
    extrapolado_d = r["d"]["segundos"] / max(r["d"]["gravadas"], 1) * linhas
    ok_tempo = r["b"]["segundos"] + r["c"]["segundos"] < LIMITE_S
    ok_mem = all(r[n]["pico_mb"] < LIMITE_MB for n in "abc")

    tabela = [
        "| Etapa | Tempo (s) | Pico de memória (MB) | Observação |",
        "|---|---|---|---|",
        f"| a: descomprimir | {r['a']['segundos']} | {r['a']['pico_mb']} | {r['a']['bytes_descomprimidos'] / 1e9:.2f} GB |",
        f"| b: ler + allowlist | {r['b']['segundos']} | {r['b']['pico_mb']} | {linhas:,} linhas, {mb_s:.0f} MB/s descomprimidos, rejeitadas {r['b']['rejeitadas']} |",
        f"| c: SHA-256 do ZIP | {r['c']['segundos']} | {r['c']['pico_mb']} | {r['c']['bytes_zip'] / 1e9:.2f} GB |",
        f"| d: COPY da amostra | {r['d']['segundos']} | {r['d']['pico_mb']} | {r['d']['gravadas']:,} linhas gravadas (extrapolado para tudo: ~{extrapolado_d / 60:.0f} min) |",
        "",
        f"ZIP: {comprimido / 1e9:.2f} GB comprimido, {descomprimido / 1e9:.2f} GB descomprimido, razão {descomprimido / comprimido:.1f}x.",
        f"**Critério (b + c < 20 min e pico < 500 MB nas etapas a, b e c): {'ATENDIDO' if ok_tempo and ok_mem else 'NÃO ATENDIDO'}** "
        f"(b + c = {r['b']['segundos'] + r['c']['segundos']:.0f} s; maior pico = {max(r[n]['pico_mb'] for n in 'abc')} MB).",
    ]
    texto = "\n".join(tabela)
    print("\n" + texto)
    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as f:
            f.write("### Spike de ingestão (Python)\n\n" + texto + "\n")
    raise SystemExit(0 if ok_tempo and ok_mem else 1)


if __name__ == "__main__":
    if sys.argv[1:2] == ["executar"]:
        executar()
    elif sys.argv[1:2] == ["etapa"]:
        {"a": etapa_a, "b": etapa_b, "c": etapa_c, "d": etapa_d}[sys.argv[2]]()
    else:
        raise SystemExit("uso: medir.py executar")
