"""Gera um ZIP sintético no formato do `consulta_cand` do TSE (spike descartável).

CSV em ISO-8859-1, separador ';', campos entre aspas, CRLF, 50 colunas, um item por
"UF" mais um `leiame.pdf` falso. NÃO há dado real: o CPF é o canário
`CANARIO-NAO-VAZAR` e o título de eleitor é zerado. Escreve em fluxo, item a item.
"""
import random
import time
import zipfile

UFS = (
    "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO ZZ"
).split()
PARTIDOS = [("PT", 13), ("PL", 22), ("MDB", 15), ("PSD", 55), ("PP", 11), ("PSB", 40), ("UNIÃO", 44)]
CARGOS = [(6, "DEPUTADO FEDERAL"), (7, "DEPUTADO ESTADUAL"), (5, "SENADOR"), (3, "GOVERNADOR")]
NOMES = ["JOÃO", "MARIA", "JOSÉ", "ANA", "CARLOS", "FRANCISCA", "ANTÔNIO", "ÂNGELA", "LUÍS", "CONCEIÇÃO"]
SITUACOES = ["ELEITO", "NÃO ELEITO", "SUPLENTE", "#NULO#"]

CAMPOS = [
    ("DT_GERACAO", "05/11/2026"), ("HH_GERACAO", "19:35:35"), ("ANO_ELEICAO", "2026"),
    ("CD_TIPO_ELEICAO", "2"), ("NM_TIPO_ELEICAO", "Eleição Ordinária"), ("NR_TURNO", "1"),
    ("CD_ELEICAO", "9999"), ("DS_ELEICAO", "Eleições Gerais SINTÉTICAS 2026"),
    ("DT_ELEICAO", "04/10/2026"), ("TP_ABRANGENCIA", "E"), ("SG_UF", "{uf}"), ("SG_UE", "{uf}"),
    ("NM_UE", "{uf} SINTÉTICO"), ("CD_CARGO", "{cargo_cd}"), ("DS_CARGO", "{cargo}"),
    ("SQ_CANDIDATO", "{n}"), ("NR_CANDIDATO", "{nr}"),
    ("NM_CANDIDATO", "CANDIDATO SINTÉTICO {n} {ruido}"), ("NM_URNA_CANDIDATO", "{urna}"),
    ("NM_SOCIAL_CANDIDATO", "#NULO#"), ("NR_CPF_CANDIDATO", "CANARIO-NAO-VAZAR"),
    ("DS_EMAIL", "#NULO#"), ("CD_SITUACAO_CANDIDATURA", "-1"),
    ("DS_SITUACAO_CANDIDATURA", "Deferido"), ("TP_AGREMIACAO", "PARTIDO ISOLADO"),
    ("NR_PARTIDO", "{npart}"), ("SG_PARTIDO", "{part}"), ("NM_PARTIDO", "PARTIDO SINTÉTICO {part}"),
    ("NR_FEDERACAO", "-1"), ("NM_FEDERACAO", "#NULO#"), ("SG_FEDERACAO", "#NULO#"),
    ("DS_COMPOSICAO_FEDERACAO", "#NULO#"), ("SQ_COLIGACAO", "{n}"),
    ("NM_COLIGACAO", "COLIGAÇÃO {ruido}"), ("DS_COMPOSICAO_COLIGACAO", "PARTIDO A / PARTIDO B / {part}"),
    ("SG_UF_NASCIMENTO", "{uf}"), ("DT_NASCIMENTO", "01/01/1970"),
    ("NR_TITULO_ELEITORAL_CANDIDATO", "000000000000"), ("CD_GENERO", "2"), ("DS_GENERO", "MASCULINO"),
    ("CD_GRAU_INSTRUCAO", "8"), ("DS_GRAU_INSTRUCAO", "SUPERIOR COMPLETO"), ("CD_ESTADO_CIVIL", "3"),
    ("DS_ESTADO_CIVIL", "CASADO(A)"), ("CD_COR_RACA", "1"), ("DS_COR_RACA", "BRANCA"),
    ("CD_OCUPACAO", "999"), ("DS_OCUPACAO", "OCUPAÇÃO SINTÉTICA"), ("CD_SIT_TOT_TURNO", "-1"),
    ("DS_SIT_TOT_TURNO", "{sit}"),
]
assert len(CAMPOS) == 50
CABECALHO = ";".join(f'"{nome}"' for nome, _ in CAMPOS)
MODELO = ";".join(f'"{valor}"' for _, valor in CAMPOS)


def _lote(rng, uf, inicio, quantidade):
    linhas = []
    for n in range(inicio, inicio + quantidade):
        part, npart = PARTIDOS[n % len(PARTIDOS)]
        cargo_cd, cargo = CARGOS[n % len(CARGOS)]
        linhas.append(
            MODELO.format(
                uf=uf, n=n, nr=10000 + n % 90000, npart=npart, part=part, cargo_cd=cargo_cd,
                cargo=cargo, sit=SITUACOES[n % len(SITUACOES)],
                urna=f"{NOMES[n % len(NOMES)]} {NOMES[(n // 7) % len(NOMES)]} {n}",
                ruido=f"{rng.getrandbits(32):08x}",
            )
        )
    return ("\r\n".join(linhas) + "\r\n").encode("iso-8859-1")


def gerar(saida, alvo_descomprimido_bytes, *, compresslevel=1, lote=10_000):
    """Escreve o ZIP em `saida` até somar `alvo_descomprimido_bytes` de CSV. Devolve estatísticas."""
    rng = random.Random(42)
    por_item = alvo_descomprimido_bytes // len(UFS)
    inicio_tempo = time.perf_counter()
    linhas_total = 0
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED, compresslevel=compresslevel) as zf:
        zf.writestr("leiame.pdf", b"%PDF-1.4\r\nsintetico\r\nnao e dado real\r\n")
        proximo = 1
        for uf in UFS:
            cabecalho = (CABECALHO + "\r\n").encode("iso-8859-1")
            escrito = len(cabecalho)
            with zf.open(f"consulta_cand_SINT_{uf}.csv", "w", force_zip64=True) as f:
                f.write(cabecalho)
                while escrito < por_item:
                    pedaco = _lote(rng, uf, proximo, lote)
                    f.write(pedaco)
                    escrito += len(pedaco)
                    proximo += lote
                    linhas_total += lote
    return {
        "linhas": linhas_total,
        "segundos": round(time.perf_counter() - inicio_tempo, 1),
    }
