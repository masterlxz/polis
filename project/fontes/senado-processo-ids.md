# Senado: `/processo` e os ids das votações (medição, 2026-11-28)

Complementa [`senado.md`](senado.md), que já mediu o formato de `/processo` e `/votacao` (Rodadas 1 a 4) e que **não foi refeito aqui**. Esta medição existe para a fatia de proposições e tramitações do Senado (equivalente aos ADR 0033, 0034 e 0035 da Câmara): antes de modelar, medir volume, ids e a correspondência com as votações que o banco já guarda. **Este documento propõe (seção 4), mas não decide, modelo nem chave**: relata o medido e deixa as perguntas para o dono.

Rótulos: **medido** (com o comando) e **documentado** (com a fonte). Datas em UTC.

## Como foi medido

- **Data e hora:** 2026-11-28, de 13:58 a 14:02 UTC (18 requisições `GET`, em série, uma a cada 3 s ou mais, a primeira só abre a especificação).
- **Máquina e concorrência:** uma máquina, e as minhas requisições foram em série (nenhuma sobreposta a outra). **Mas outra sessão da equipe (o levantamento do #372) mediu o Senado ao mesmo tempo, de 13:58 a 14:07 UTC, com o mesmo `User-Agent`** (informação da coordenação; não li o arquivo dele). O ADR 0008 (decisão 5) pede série, e o conjunto das duas sessões não foi em série. **Os tempos de resposta deste documento (inclusive 42,07 s e 4,95 s) não são confiáveis**: podem estar contaminados pela outra sessão e pela rede; usar só como ordem de grandeza.
- **Identificação do coletor:** `User-Agent: polis-coletor (+https://github.com/masterlxz/polis)` (o `USER_AGENT` de `apps/sources/http_client.py:84`), como manda o ADR 0008, decisões 4 e 5. Todas as respostas foram `200`; nenhum `429`, `503` nem `403`.
- **Versão da API na época:** `4.1.3.120` (medido em `/v3/api-docs`; `senado.md` registrou `4.1.3.113` em 2026-11-05). 157 caminhos e 42 depreciados, os mesmos números de `senado.md` (bloco 7). Não comparei os campos entre as duas versões.
- **Respostas** gravadas fora do repositório (scratchpad da sessão); nada foi commitado além deste texto. Só estrutura e contagens: nenhum valor de `autoria` ou de nome foi impresso.
- **Cabeçalhos:** o `curl` não gravou cabeçalhos (sem `-D`) nas requisições, **exceto em 4** (`?ano=2026`, `/processo/8986903`, `?codigoMateria=172391` e `?sigla=PEC&ano=2026`). Nessas 4: `200`, `cache-control: max-age=1800, s-maxage=1800`, **`Age` de 2.404, 178, 938 e 1.327 s** (cache de borda: a resposta pode ter até ~40 minutos) e nenhum `Retry-After`. Nas outras 14 não olhei cabeçalhos; "nenhum 429, 503 ou 403" vem do código de status impresso por `-w`.

```bash
B=https://legis.senado.leg.br/dadosabertos
UA='polis-coletor (+https://github.com/masterlxz/polis)'
g(){ sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o "$1.json" -w "$2 -> %{http_code} %{size_download} B %{time_total}s\n" "$B/$2"; }

g apidocs   'v3/api-docs'
g p2026     'processo?ano=2026'
g siglas    'processo/siglas'
g p2026_tram 'processo?ano=2026&tramitando=S'
g p2026_pl  'processo?ano=2026&sigla=PL'
g p_tram    'processo?tramitando=S'
g v365      'votacao?dataInicio=2025-11-29&dataFim=2026-11-28'
# Q: idProcesso das votações (v365) que não estão em p2026 nem em p_tram (43 ids), calculado das respostas já gravadas:
Q=$(python3 -I -c '
import json
a = {x["id"] for f in ("p2026", "p_tram") for x in json.load(open(f + ".json"))}
ids = sorted({v["idProcesso"] for v in json.load(open("v365.json"))} - a)
print("&".join("idProcesso=%d" % i for i in ids))')
g miss_lookup "processo?$Q"
g det_8986903 'processo/8986903'
g bycm_172391 'processo?codigoMateria=172391'
g pec2026   'processo?sigla=PEC&ano=2026'
g det_8983497 'processo/8983497'
g det_8983465 'processo/8983465'
g papres2026 'processo?dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28'
g pleg      'processo?tramitouLegislaturaAtual=S'
g p2025     'processo?ano=2025'
g nd7       'processo?numdias=7'
g nd30      'processo?numdias=30'
```

| Requisição | Status | Bytes | Tempo (s) (**não confiável**, ver acima) |
|---|---|---|---|
| `/v3/api-docs` | 200 | 215.797 | 0,44 |
| `/processo?ano=2026` | 200 | 3.130.919 | 0,69 |
| `/processo/siglas` | 200 | 22.711 | 0,33 |
| `/processo?ano=2026&tramitando=S` | 200 | 1.500.962 | 1,14 |
| `/processo?ano=2026&sigla=PL` | 200 | 494.760 | 0,63 |
| `/processo?tramitando=S` | 200 | 9.221.974 | 0,83 |
| `/votacao?dataInicio=2025-11-29&dataFim=2026-11-28` | 200 | 1.719.282 | 0,66 |
| `/processo?idProcesso=...` (43 ids) | 200 | 47.370 | 0,36 |
| `/processo/8986903` | 200 | 55.715 | 0,30 |
| `/processo?codigoMateria=172391` | 200 | 2.771 | 0,25 |
| `/processo?sigla=PEC&ano=2026` | 200 | 27.984 | 0,31 |
| `/processo/8983497` | 200 | 19.649 | 4,95 (uma amostra; as demais ficaram abaixo de 1,2 s) |
| `/processo/8983465` | 200 | 4.194 | 0,34 |
| `/processo?dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28` | 200 | 3.744.740 | 0,57 |
| `/processo?tramitouLegislaturaAtual=S` | 200 | 22.908.869 | **42,07** |
| `/processo?ano=2025` | 200 | 4.186.792 | 0,69 |
| `/processo?numdias=7` | 200 | 1.003.765 | 0,46 |
| `/processo?numdias=30` | 200 | 2.227.698 | 0,52 |

Os números abaixo saem do script a seguir, rodado sobre essas respostas (`python3 -I reproduz.py`, com `M` apontando para o diretório delas). Cada seção diz de qual bloco vem o número. O que **não** sai do script está listado, uma a uma, em "Não verificado" (tempos, cabeçalhos, os 3 detalhes `/processo/{id}`).

<details>
<summary>Script de contagem (reproduz.py)</summary>

```text
# Python 3. Marcado como `text` de propósito: o `ruff format --check .` do CI reformata blocos `python` de Markdown.
import collections
import json
import re

M = "<diretório das respostas>/"


def load(name):
    with open(M + name + ".json") as f:
        return json.load(f)


ano = load("p2026")
tram = load("p_tram")
leg = load("pleg")
apres = load("papres2026")
a2025 = load("p2025")
perdidos = load("miss_lookup")
votos = load("v365")
nd7, nd30 = load("nd7"), load("nd30")
ANO = re.compile(r"^\S+ \d+/(\d{4})")


def ano_de(x):
    m = ANO.match(x["identificacao"])
    return int(m.group(1)) if m else None


def sigla(x):
    return x["identificacao"].split(" ")[0]


print("== 1. volume")
print("ano=2026:", len(ano), "tramitando Sim:", sum(x["tramitando"] == "Sim" for x in ano))
print("por sigla:", collections.Counter(map(sigla, ano)).most_common())
print("casa:", collections.Counter(x["casaIdentificadora"] for x in ano))
print("ano=2026&tramitando=S:", len(load("p2026_tram")))
print("tramitando=S:", len(tram), "anos:", sorted(collections.Counter(ano_de(x) for x in tram if ano_de(x)).items()))
print("tramitando=S numerados antes de 2026:", sum(1 for x in tram if ano_de(x) and ano_de(x) < 2026))
print("tramitando=S sem ano parseavel:", sum(1 for x in tram if ano_de(x) is None))
print("ano=2025:", len(a2025), collections.Counter(x["tramitando"] for x in a2025))
print("dataApresentacao 2026:", len(apres), "so por data:", len({x["id"] for x in apres} - {x["id"] for x in ano}),
      "so por ano:", len({x["id"] for x in ano} - {x["id"] for x in apres}))
print("tramitouLegislaturaAtual=S:", len(leg), "ano=2026 fora dela:", len({x["id"] for x in ano} - {x["id"] for x in leg}),
      "tramitando fora dela:", len({x["id"] for x in tram} - {x["id"] for x in leg}))
print("numdias=7:", len(nd7), "numdias=30:", len(nd30))

print("== 2. ids")
todos = ano + tram + leg + apres + a2025 + perdidos + nd7 + nd30
por_id, por_cm = collections.defaultdict(set), collections.defaultdict(set)
for x in todos:
    por_id[x["id"]].add(x["codigoMateria"])
    por_cm[x["codigoMateria"]].add(x["id"])
print("itens lidos:", len(todos), "ids distintos:", len(por_id), "cm distintos:", len(por_cm))
print("id com >1 cm:", sum(len(s) > 1 for s in por_id.values()), "cm com >1 id:", sum(len(s) > 1 for s in por_cm.values()))
print("sem id:", sum(x.get("id") is None for x in todos), "sem cm:", sum(x.get("codigoMateria") is None for x in todos))
print("tipos:", {type(x["id"]).__name__ for x in todos}, {type(x["codigoMateria"]).__name__ for x in todos})
print("faixa id:", min(por_id), max(por_id), "faixa cm:", min(por_cm), max(por_cm))
for nome, lista in [("ano=2026", ano), ("tramouLegislaturaAtual", leg), ("tramitando=S", tram)]:
    rep = collections.Counter(x["identificacao"] for x in lista)
    print(nome, "identificacao repetida:", sum(v > 1 for v in rep.values()))
print("identificacao fora de 'SIGLA N/AAAA':", sum(not re.fullmatch(r"\S+ \d+/\d{4}", x["identificacao"]) for x in ano))
print("sufixo ' - X':", sum(bool(re.fullmatch(r"\S+ \d+/\d{4} - .+", x["identificacao"])) for x in ano),
      "sufixo '(...)':", sum(bool(re.fullmatch(r"\S+ \d+/\d{4} \(.+\)", x["identificacao"])) for x in ano))
base = collections.Counter(ANO.match(x["identificacao"]).group(0) for x in ano if ANO.match(x["identificacao"]))
print("base 'SIGLA N/AAAA' repetida:", sum(v > 1 for v in base.values()),
      "so em REQ:", all(k.startswith("REQ ") for k, v in base.items() if v > 1))
print("ano da identificacao:", collections.Counter(ano_de(x) for x in ano))
print("ano de dataApresentacao:", collections.Counter(x["dataApresentacao"][:4] for x in ano))

print("== 3. votacoes")
print("votacoes:", len(votos), "janela:", min(v["dataSessao"] for v in votos), max(v["dataSessao"] for v in votos))
print("idProcesso nulo:", sum(v["idProcesso"] is None for v in votos), "cm nulo:", sum(v["codigoMateria"] is None for v in votos))
ids = {v["idProcesso"] for v in votos}
print("processos distintos:", len(ids), "pares (id,cm) distintos:", len({(v["idProcesso"], v["codigoMateria"]) for v in votos}))
A, T = {x["id"] for x in ano}, {x["id"] for x in tram}
print("em ano=2026:", len(ids & A), "votacoes:", sum(v["idProcesso"] in A for v in votos))
print("em tramitando=S:", len(ids & T), "votacoes:", sum(v["idProcesso"] in T for v in votos))
print("em um dos dois:", len(ids & (A | T)), "votacoes:", sum(v["idProcesso"] in A | T for v in votos))
print("em nenhum:", len(ids - (A | T)), "votacoes:", sum(v["idProcesso"] not in A | T for v in votos))
print("em tramouLegislaturaAtual:", len(ids & {x["id"] for x in leg}))
print("em ano=2025:", len(ids & {x["id"] for x in a2025}), "votacoes:", sum(v["idProcesso"] in {x["id"] for x in a2025} for v in votos))
print("campo ano das votacoes:", sorted(collections.Counter(v["ano"] for v in votos).items()))
print("votacoes ano<2026:", sum(v["ano"] < 2026 for v in votos), "ano<2025:", sum(v["ano"] < 2025 for v in votos))
print("sigla das votacoes:", collections.Counter(v["sigla"] for v in votos).most_common())
P = {x["id"]: x for x in perdidos}
vc = {v["idProcesso"]: v for v in votos}
fora = sorted(ids - (A | T))
print("ids fora pedidos:", len(fora), "devolvidos:", len(perdidos), "achados:", len(set(fora) & set(P)))
print("cm igual:", sum(P[i]["codigoMateria"] == vc[i]["codigoMateria"] for i in fora if i in P),
      "identificacao igual:", sum(P[i]["identificacao"] == vc[i]["identificacao"] for i in fora if i in P),
      "tramitando:", collections.Counter(P[i]["tramitando"] for i in fora if i in P))
todosP = {x["id"]: x for x in ano + tram}
achados = [i for i in ids if i in todosP]
print("nos achados por filtro: cm igual:", sum(todosP[i]["codigoMateria"] == vc[i]["codigoMateria"] for i in achados),
      "identificacao igual:", sum(todosP[i]["identificacao"] == vc[i]["identificacao"] for i in achados), "de", len(achados))

print("== 4. campos (uniao de todos os ids lidos)")
U = {}
for x in todos:
    U.setdefault(x["id"], x)
X = list(U.values())
print("ids na uniao:", len(X))
for k in ["identificacao", "ementa", "situacaoAtual", "tipoDocumento", "tipoConteudo", "enteIdentificador", "urlDocumento",
          "autoria", "objetivo", "apelido", "normaGerada"]:
    v = [x[k] for x in X if isinstance(x.get(k), str)]
    print(k, "presente:", len(v), "max:", max(map(len, v)))
print("ementa com \\n / \\r / \\t:", sum("\n" in x["ementa"] for x in X), sum("\r" in x["ementa"] for x in X), sum("\t" in x["ementa"] for x in X))
print("chaves nem sempre presentes:", {k: sum(k in x for x in X) for k in
      ["dataSituacaoAtual", "situacaoAtual", "dataUltimaAtualizacao", "ultimaInformacaoAtualizada", "urlDocumento",
       "objetivo", "dataDeliberacao", "siglaTipoDeliberacao", "apelido", "normaGerada"]})
print("ano=2026 chaves:", {k: sum(k in x for x in ano) for k in
      ["dataSituacaoAtual", "situacaoAtual", "dataUltimaAtualizacao", "ultimaInformacaoAtualizada", "urlDocumento",
       "objetivo", "dataDeliberacao", "apelido", "normaGerada"]})

print("== 5. identificacao na uniao")
rep = collections.Counter(x["identificacao"] for x in X)
dup = [k for k, v in rep.items() if v > 1]
print("identificacao repetida na uniao:", len(dup), "itens:", sum(rep[k] for k in dup))
print("(identificacao, casa) repetida:", sum(v > 1 for v in collections.Counter((x["identificacao"], x["casaIdentificadora"]) for x in X).values()))
print("autoria menciona 'Câmara' em PL (ano=2026):", sum(1 for x in ano if sigla(x) == "PL" and "Câmara" in x["autoria"]))

print("== 6. detalhes")
descr = {s["sigla"]: s["descricao"] for s in load("siglas")}
tot, tr = collections.Counter(map(sigla, ano)), collections.Counter(sigla(x) for x in ano if x["tramitando"] == "Sim")
for s, n in tot.most_common():
    print(f"| `{s}` | {descr.get(s, '?').strip()} | {n} | {tr[s]} |")
print("REQ 1/2026 (todas as variantes):", sum(x["identificacao"].startswith("REQ 1/2026 - ") for x in ano))
print("so por data de apresentacao:", collections.Counter(map(sigla, [x for x in apres if x["id"] not in A])).most_common())
print("ano=2026 fora de tramouLegislaturaAtual:", collections.Counter(sigla(x) for x in ano if x["id"] not in {y["id"] for y in leg}).most_common())
print("  tramitando Sim entre eles:", sum(1 for x in ano if x["id"] not in {y["id"] for y in leg} and x["tramitando"] == "Sim"))
print("numdias=30 por ano do numero:", sorted(collections.Counter(ano_de(x) for x in nd30 if ano_de(x)).items(), reverse=True)[:6],
      "sem ano parseavel:", sum(ano_de(x) is None for x in nd30))
print("numdias=7 dataUltimaAtualizacao:", min(x["dataUltimaAtualizacao"][:10] for x in nd7), max(x["dataUltimaAtualizacao"][:10] for x in nd7),
      "contido em numdias=30:", {x["id"] for x in nd7} <= {x["id"] for x in nd30})
print("sem situacaoAtual, por tramitando:", collections.Counter(x["tramitando"] for x in X if "situacaoAtual" not in x))
print("sem urlDocumento, por casa:", collections.Counter(x["casaIdentificadora"] for x in X if "urlDocumento" not in x))
print("CN em 2026 por sigla:", collections.Counter(sigla(x) for x in ano if x["casaIdentificadora"] == "CN").most_common())
print("tramitando=S: ids tambem em ano=2026 (1674 esperados):", len(T & A))

print("== 7. ajustes da revisao")
d = load("apidocs")
print("api-docs: versao", d["info"].get("version"), "caminhos", len(d["paths"]), "depreciados", sum(v.get("get", {}).get("deprecated", False) for v in d["paths"].values()))
sg = load("siglas")
print("siglas:", len(sg), "sem dataFim (ausente ou nulo):", sum(s.get("dataFim") is None for s in sg))
print("ano=2025 ∩ ano=2026:", len({x["id"] for x in a2025} & A), "de", len(a2025))
print("PL de ano=2026 por tipoDocumento:", collections.Counter(x["tipoDocumento"] for x in ano if sigla(x) == "PL"))
print("casaIdentificadora na uniao:", collections.Counter(x["casaIdentificadora"] for x in X), "enteIdentificador max:", max(len(x["enteIdentificador"]) for x in X))
print("numeros-base distintos de REQ repetidos:", sum(v > 1 for v in base.values()), "itens REQ nesses:", sum(v for v in base.values() if v > 1))
print("enteIdentificador dos REQ 1/2026:", sorted({x["enteIdentificador"] for x in ano if x["identificacao"].startswith("REQ 1/2026 - ")}))
so_data = [x for x in apres if x["id"] not in A]
print("716 so por data: ano do numero:", sorted(collections.Counter(ano_de(x) for x in so_data).items(), key=lambda kv: (kv[0] is None, kv[0] or 0)))
print("votacoes por mes de dataSessao (2025-12 e 2026):", sorted(collections.Counter(v["dataSessao"][:7] for v in votos).items()))
v26 = [v for v in votos if v["dataSessao"] >= "2026-01-01"]
ids26 = {v["idProcesso"] for v in v26}
print("votacoes com dataSessao>=2026-01-01:", len(v26), "processos distintos:", len(ids26))
print("  em ano=2026:", sum(v["idProcesso"] in A for v in v26), "processos:", len(ids26 & A))
print("  em ano=2026 ou tramitando=S:", sum(v["idProcesso"] in A | T for v in v26), "processos:", len(ids26 & (A | T)))
print("  campo ano<2026:", sum(v["ano"] < 2026 for v in v26), " ano<2025:", sum(v["ano"] < 2025 for v in v26))
print("  em ano=2025 ou 2026:", sum(v["idProcesso"] in A | {x["id"] for x in a2025} for v in v26))
v25 = [v for v in votos if v["dataSessao"] < "2026-01-01"]
print("votacoes de dez/2025:", len(v25), " com campo ano==2026:", sum(v["ano"] == 2026 for v in v25))
tipos = {"PL", "PLP", "PEC", "PDL", "MPV", "PRS", "VET", "PLN"}
print("votacoes cujo sigla fica fora de", sorted(tipos), ":", sum(v["sigla"] not in tipos for v in votos), collections.Counter(v["sigla"] for v in votos if v["sigla"] not in tipos))
print("processos votados em ano=2026 (27 de 71):", len(ids & A), " em ano=2026 ou tramitando:", len(ids & (A | T)))
print("ano=2026&tramitando=S == tramitando Sim de ano=2026:", {x["id"] for x in load("p2026_tram")} == {x["id"] for x in ano if x["tramitando"] == "Sim"})
print("ano=2026&sigla=PL == PL de ano=2026:", {x["id"] for x in load("p2026_pl")} == {x["id"] for x in ano if sigla(x) == "PL"}, len(load("p2026_pl")))
print("sigla=PEC&ano=2026 == PEC de ano=2026:", {x["id"] for x in load("pec2026")} == {x["id"] for x in ano if sigla(x) == "PEC"}, len(load("pec2026")))
print("codigoMateria=172391:", [(x["id"], x["identificacao"]) for x in load("bycm_172391")])
ent = collections.Counter(x["enteIdentificador"] for x in X)
fora_padrao = [k for k in ent if not re.fullmatch(r"[A-Z]{2,12}|CMMPV \d+/\d{4}|Mesa|CEsp", k)]
print("enteIdentificador distintos:", len(ent), "fora do padrao sigla/'CMMPV n/aaaa'/Mesa/CEsp:", fora_padrao)
print("dataApresentacao fora de aaaa-mm-dd:", sum(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", x["dataApresentacao"]) for x in X))
print("formatos de dataUltimaAtualizacao:", collections.Counter(re.sub(r"\d", "d", x["dataUltimaAtualizacao"]) for x in X if "dataUltimaAtualizacao" in x))
print("ementa vazia:", sum(x["ementa"] == "" for x in X), "tramitando nulo/vazio:", sum(not x["tramitando"] for x in X), "casaIdentificadora nulo/vazio:", sum(not x["casaIdentificadora"] for x in X))
print("tramitando valores:", collections.Counter(x["tramitando"] for x in X))
```

</details>

## 1. Volume de `/processo` em 2026

### Como filtrar e paginar

- **Documentado** (descrição de `/processo` em `/v3/api-docs`, versão 4.1.3.120): é obrigatório informar ao menos um de `numero`, `ano`, `idProcesso`, `codigoMateria`, `tramitando` (`S`; **é o padrão se nenhum outro for informado**), `tramitouLegislaturaAtual`, `codigoParlamentarAutor`, `codigoClasse`, `codigoAssuntoEspecifico`, `sigla` + `siglaEnteIdentificador`, `dataInicioApresentacao`, `dataFimApresentacao`, `dataInicioDeliberacao`, `dataFimDeliberacao`, `numeroNorma`, `anoNorma`, `numdias` (máximo 30). `sigla` e `idProcesso` são arrays (repetíveis na consulta). Com `dataInicioApresentacao` ou `dataFim...` sozinhos, a descrição diz que o retorno cobre no máximo 1 ano. Não há `pagina` nem `tamanho` na lista de parâmetros.
- **Medido:** nenhuma paginação. `?ano=2026` devolveu os 3.467 itens numa resposta só (3,1 MB, 0,69 s); `?idProcesso=` repetido 43 vezes devolveu os 43.
- **Medido:** `?ano=` filtra pelo **ano do número** (o que vem depois da barra em `identificacao`), **não** pela data de apresentação. Em `?ano=2026`, 3.467 de 3.467 têm `2026` em `identificacao`, mas 8 foram apresentados em 2024 e 2025 (`dataApresentacao`). Por outro lado, `dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28` devolveu **4.175** itens: 3.459 em comum com `?ano=2026`, **716 só por data** (por sigla: 383 `PDL`, 326 `PL`, 3 `PEC`, 3 `PLP`, 1 `VET`; pelo ano do número: 2025 447, 2024 110, 2023 76, 2022 19, 2021 17, 2020 9, 2019 38; blocos 6 e 7) e 8 só por `ano`. Os dois filtros não são o mesmo conjunto.
- **Medido:** `?ano=2026&tramitando=S` devolveu 1.674 itens, **exatamente** os mesmos ids dos itens com `tramitando` igual a `Sim` em `?ano=2026`. `?ano=2026&sigla=PL` devolveu 572, o mesmo conjunto dos que começam com `PL ` em `?ano=2026`. `?sigla=PEC&ano=2026` devolveu 16, igual ao filtro local.
- `tramitando` vem como texto `Sim` ou `Não` (não é booleano, e o filtro de entrada usa `S` ou `N`).

### Totais de 2026 (`?ano=2026`)

Data da medição: 2026-11-28 13:58 UTC. Bloco 1 do script.

```bash
curl -sS -A "$UA" -H 'Accept: application/json' "$B/processo?ano=2026" -o p2026.json
python3 -I -c 'import json;d=json.load(open("p2026.json"));print(len(d),sum(x["tramitando"]=="Sim" for x in d))'   # 3467 1674
```

| Item | Valor |
|---|---|
| Processos com número de 2026 | **3.467** |
| `tramitando` = `Sim` | **1.674** (48%) |
| `tramitando` = `Não` | 1.793 |
| `casaIdentificadora` `SF` / `CN` | 3.120 / 347 |
| Siglas distintas (primeiro token de `identificacao`) | 27 |
| Siglas no cadastro `/processo/siglas` | 184 (82 sem `dataFim`, isto é, chave ausente ou nula; bloco 7) |

Por sigla (a descrição vem de `/processo/siglas`; todas as 27 constam da lista):

| Sigla | Descrição | Em 2026 | Tramitando |
|---|---|---|---|
| `REQ` | Requerimento | 1.413 | 406 |
| `RQS` | Requerimento | 816 | 314 |
| `PL` | Projeto de Lei | 572 | 529 |
| `MPV` | Medida Provisória | 68 | 21 |
| `PLP` | Projeto de Lei Complementar | 66 | 56 |
| `PDL` | Projeto de Decreto Legislativo | 64 | 52 |
| `MSF` | Mensagem (SF) | 61 | 13 |
| `PET` | Petição (SF) | 61 | 61 |
| `PRS` | Projeto de Resolução do Senado | 60 | 21 |
| `VET` | Veto | 56 | 55 |
| `INS` | Indicação | 54 | 19 |
| `SUG` | Sugestão | 43 | 37 |
| `PLN` | Projeto de Lei do Congresso Nacional | 35 | 8 |
| `PCE` | Petição do Conselho de Ética e Decoro Parlamentar (SF) | 23 | 23 |
| `AVN` | Aviso (CN) | 22 | 22 |
| `PEC` | Proposta de Emenda à Constituição | 16 | 16 |
| `R.S` | Recurso (SF) | 9 | 5 |
| `R.C` | Recurso (Congresso Nacional) | 6 | 6 |
| `OFS` | Ofício "S" | 5 | 1 |
| `PFS` | Proposta de Fiscalização e Controle | 4 | 4 |
| `PRM` | Premiação | 3 | 0 |
| `PCS` | Parecer do Conselho de Comunicação Social | 3 | 0 |
| `OFN` | Ofício (CN) | 2 | 2 |
| `RRC` | Recomendação do Conselho de Comunicação Social | 2 | 0 |
| `RQN` | Requerimento (CN) | 1 | 1 |
| `MCN` | Mensagem (CN) | 1 | 1 |
| `AVS` | Aviso | 1 | 1 |

`REQ` e `RQS` somam 2.229 dos 3.467 (64%). A tabela é a saída do bloco 6 do script (as linhas já saem no formato Markdown).

### Outros recortes (contexto para decidir o escopo temporal)

| Filtro | Itens | Tamanho | Tempo | Bloco |
|---|---|---|---|---|
| `?ano=2026` | 3.467 | 3,1 MB | 0,69 s | 1 |
| `?ano=2025` | 5.003 (1.998 tramitando) | 4,2 MB | 0,69 s | 1 |
| `?dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28` | 4.175 | 3,7 MB | 0,57 s | 1 |
| `?tramitando=S` (sem ano) | 10.951 | 9,2 MB | 0,83 s | 1 |
| `?tramitouLegislaturaAtual=S` | 26.978 | **22,9 MB** | **42,07 s** (uma amostra) | 1 |
| `?numdias=7` | 1.110 | 1,0 MB | 0,46 s | 1 |
| `?numdias=30` | 2.433 | 2,2 MB | 0,52 s | 1 |

- `?ano=2025` e `?ano=2026` não têm nenhum id em comum (0 de 5.003; bloco 7).
- `?tramitando=S` traz processos de **muitos anos**: 1.674 numerados em 2026, 9.237 numerados antes (1984 a 2025; 1.998 de 2025, 1.524 de 2024, 1.600 de 2023, 1.263 de 2019) e **40 cujo `identificacao` não tem o formato `SIGLA N/AAAA`** (por exemplo `MPV 2167-53/2001`, com traço no número). O ano do número não é o ano da última atividade.
- `?tramitouLegislaturaAtual=S` **não é superconjunto** de `?ano=2026` nem de `?tramitando=S`: 364 dos 3.467 processos de 2026 (291 `REQ`, 61 `PET`, 8 `R.S`, 2 `PFS`, 1 `RQN`, 1 `SUG`; 112 deles `tramitando=Sim`; bloco 6) e 1.045 dos 10.951 tramitando ficam de fora. O significado exato de "tramitou na legislatura atual" **não foi verificado** (só o texto do parâmetro: "Processo tramitou na legislatura atual?").
- `?numdias=N` ("atualizadas nos últimos N dias", máximo 30, documentado): em 2026-11-28, `numdias=7` trouxe itens com `dataUltimaAtualizacao` de 2026-11-21 a 2026-11-27 (1.110), e `numdias=30` de 2026-10-29 a 2026-11-27 (2.433). Os 1.110 estão contidos nos 2.433. Mais da metade dos itens atualizados nos últimos 30 dias é numerada em anos anteriores a 2026 (pelo ano de `identificacao`: 1.202 de 2026, 430 de 2025, 269 de 2024, 151 de 2023, 87 de 2022, 120 de 2021, e outros; 2 sem ano no formato; bloco 6). Ou seja, o incremental por `numdias` pega processos de qualquer ano.

## 2. Ids: `id` × `codigoMateria` × `identificacao`

Bloco 2 do script. **Medido em 2026-11-28 sobre a união de todas as respostas de `/processo`** (54.160 itens lidos, 28.355 ids distintos, de todos os anos que as consultas alcançaram).

| Pergunta | Resultado |
|---|---|
| `id` e `codigoMateria` sempre presentes? | **Sim**: 0 ausentes e 0 nulos em 54.160 itens; os dois são inteiros JSON |
| `id` único? | **Sim**: 28.355 ids distintos e cada um tem exatamente 1 `codigoMateria` |
| `codigoMateria` único? | **Sim**: 28.355 códigos distintos e cada um aponta para exatamente 1 `id` |
| 1:1? | **Sim**, nos 28.355 (0 ids com mais de 1 código, 0 códigos com mais de 1 id) |
| Faixa dos valores | `id` de 500.046 a 9.141.063; `codigoMateria` de 43 a 176.628 (os dois cabem no `int32`, o limite de `_int`, ver seção 3) |
| Consulta por `codigoMateria` | `?codigoMateria=172391` devolveu 1 item, `id` 8986903, `PEC 1/2026` (o mesmo de `senado.md`; bloco 7) |
| Consulta por `id` | `/processo/8986903` (detalhe, 55 KB) e `?idProcesso=` (lista, repetível; bloco 3) funcionam; o detalhe tem `id`, `codigoMateria`, `sigla`, `numero` (texto), `ano` (inteiro) e `identificacao` (**avulso, n=1, não reproduzível pelo script**) |

**Limite da afirmação "1:1":** vale para os 28.355 processos que as consultas desta rodada devolveram (2026, 2025, tramitando de todos os anos, "tramitou na legislatura atual", mais os 43 das votações). Não varri todos os anos nem os processos antigos que nunca tramitaram na legislatura atual.

### `identificacao`

- **Medido:** `identificacao` é única nos 28.355 ids da união (0 repetidas; também 0 repetidas em cada conjunto separado e 0 pelo par `identificacao` + `casaIdentificadora`).
- **Mas o texto muda de forma** (`?ano=2026`, 3.467 itens): 2.047 são `SIGLA N/AAAA`; **1.413 são `REQ N/AAAA - <ente>`** (por exemplo `REQ 1/2026 - CDIR`, `REQ 1/2026 - MPV 1323/2025`) e 7 são `PL N/AAAA (Substitutivo-CD)`, todos com `tipoDocumento` `Emenda` (os outros 565 `PL` são `Projeto de Lei Ordinária`; bloco 7). **142 números-base distintos `SIGLA N/AAAA` se repetem em 2026** (juntos, 1.129 processos), **todos em `REQ`**: `REQ 1/2026`, por exemplo, aparece 31 vezes, cada uma com um `enteIdentificador` diferente (blocos 6 e 7). Os 31 valores são siglas como `CAE`, `CCJ`, `CMMPV 1323/2025` e `Mesa` (o que cada sigla é, não consultei em dicionário): **ente, não necessariamente colegiado**. Na união, `enteIdentificador` tem 81 valores distintos, todos com cara de sigla de órgão (só `CMACOP30` fugiu do padrão que testei; nenhum parece nome de pessoa; bloco 7). Fora de `REQ`, o número base não se repete.
- **Medido:** cada ente numera os seus requerimentos de 1 a N, e a distinção entre eles está no **sufixo do texto** e no `enteIdentificador`, não no número. O campo `sigla`+`numero`+`ano` do detalhe `/processo/{id}` foi lido em 3 processos (`PEC 1/2026`, `PL 159/2026 (Substitutivo-CD)`, `PL 199/2026`), nenhum `REQ`; **não medi** se o detalhe de um `REQ` traz o ente em outro campo.
- `casaIdentificadora` só tem `SF` e `CN` (união de 28.355: `SF` 26.339, `CN` 2.016; bloco 7). Em `?ano=2026`, `CN`: 347 de 3.467 em 2026: `REQ` 151, `MPV` 68, `VET` 56, `PLN` 35, `AVN` 22, `R.C` 6, `PCS` 3, `OFN` 2, `RRC` 2, `RQN` 1, `MCN` 1; bloco 6.

### Origem na Câmara (3 detalhes lidos)

O detalhe `/processo/{id}` traz `siglaCasaIniciadora`, `idProcessoCasaInicial` e `identificacaoProcessoInicial`. Medido em 3 processos (**avulso, não reproduzível pelo script**; as respostas estão no scratchpad):

| `id` | `identificacao` | `siglaCasaIniciadora` | `idProcessoCasaInicial` | `identificacaoProcessoInicial` |
|---|---|---|---|---|
| 8986903 | `PEC 1/2026` | `SF` | 8986903 (ele mesmo) | `PEC 1/2026` |
| 8983465 | `PL 199/2026` | **`CD`** | 8983464 | `PL 10674/2018` (da Câmara) |
| 8983497 | `PL 159/2026 (Substitutivo-CD)` | `SF` | 2947817 | `PLS 491/2011` |

`identificacaoExterna` veio como objeto vazio (`{}`) nos 3. Só indica que o dado de ligação com a Câmara **existe** no detalhe; não mediu se `PL 10674/2018` corresponde ao `id` da Câmara nem com que frequência isso ocorre (n=3). Não está na listagem `/processo`.

### Campos da listagem `/processo` (tamanhos e presença)

Bloco 4. União de 28.355 processos; para 2026 (`?ano=2026`, 3.467) ao lado.

| Campo | Presente (união) | Presente (2026) | Tamanho máximo (união) | Observação |
|---|---|---|---|---|
| `id`, `codigoMateria`, `identificacao`, `ementa`, `tipoDocumento`, `tipoConteudo`, `enteIdentificador`, `casaIdentificadora`, `dataApresentacao`, `autoria`, `tramitando` | todos | todos | `identificacao` 30; `ementa` **5.104**; `tipoDocumento` 41; `tipoConteudo` 152; `enteIdentificador` 15; `autoria` **12.010** | `dataApresentacao` sempre `aaaa-mm-dd` |
| `urlDocumento` | 27.872 | 3.467 | 100 | ausente em 483 da união (290 `CN`, 193 `SF`; bloco 6) |
| `situacaoAtual`, `dataSituacaoAtual` | 25.445 | 3.300 | 60 | ausentes em 2.910 da união (2.758 deles `tramitando=Não`, 152 `Sim`; bloco 6) |
| `dataUltimaAtualizacao`, `ultimaInformacaoAtualizada` | 8.790 | 3.197 | n/m | `dataUltimaAtualizacao` é data e hora ISO sem fuso, com fração de segundo de **0 a 6 dígitos** (7.859 de 8.790 com 3 dígitos, ex. `2026-10-21T17:09:43.956`; 788 com 2; 79 com 1; 50 com 6; 7 sem fração; 6 com 5; 1 com 4; bloco 7); ausentes em 19.565 da união |
| `objetivo` | 12.742 | 718 | 12 | |
| `dataDeliberacao`, `siglaTipoDeliberacao` | 14.332 | 1.274 | n/m | |
| `apelido` | 706 | 106 | 260 | |
| `normaGerada` | 3.311 | 155 | 50 | texto, não objeto |

- `ementa` tem **quebra de linha em 388 processos** (`\n`), **CR em 313** e **TAB em 5**, na união (mesma família de problema do ADR 0033, decisão 7); nunca vazia (bloco 7).
- `tramitando` e `casaIdentificadora` nunca nulos nem vazios na união; `tramitando` vale `Sim` (10.951) ou `Não` (17.404) (bloco 7).

### Nota: reconciliação com o #370 (`senado-processo-regras.md`)

O #370 (commit `932e963` da branch `sen-regras`) **já incorpora estes números**: `codigoMateria` 1:1 com `id`, `casaIdentificadora` só `SF` e `CN` e `enteIdentificador` com até 15 caracteres. **Medido aqui** (2026-11-28, blocos 2, 4 e 7), para conferência: `codigoMateria` é 1:1 com `id` em 28.355 processos; `casaIdentificadora` só tem `SF` e `CN`; `enteIdentificador` tem no máximo 15 caracteres e 81 valores distintos, e o padrão testado (sigla maiúscula, `CMMPV n/aaaa`, `Mesa`, `CEsp`) não achou valor com forma de nome de pessoa (por regex, **não** por leitura dos 81 valores; a regex foi montada depois de ver parte deles); `dataApresentacao` é sempre `aaaa-mm-dd` (0 fora do formato em 28.355) e `dataUltimaAtualizacao` traz hora com fração de segundo de comprimento variável (0 a 6 dígitos). Não consultei o dicionário do Senado.

**Referências a este arquivo devem ser por seção, não por número de linha** (as linhas mudam a cada revisão). Na versão anterior do #370, a fração das votações ligadas a "só 2026" aparecia como "34 de 90 (38%)"; o certo para `ano=2026` é **33 de 90 (37%)** (34 de 90 só com `tramitando=S`; 33 de 74, 45%, só com votações de 2026).

## 3. Correspondência com as votações do Senado

### O que o banco guarda hoje (leitura do código)

Li `apps/legislature/senate_voting_parsing.py`, `senate_voting_normalization.py` e `models.py`:

- **`SenateVoting.process_id`** (`models.py:133`): `PositiveIntegerField("código do processo")`, **sem `null`, sem `db_index` e sem chave estrangeira**. Vem de `idProcesso` (`senate_voting_parsing.py:78`: `_int(values, "idProcesso")`).
- **`SenateVoting.matter_id`** (`models.py:134`): `PositiveIntegerField("código da matéria")`, mesmas propriedades. Vem de `codigoMateria` (`senate_voting_parsing.py:79`).
- A chave da votação é `session_voting_code` (`codigoSessaoVotacao`, `models.py:118`), única por `UniqueConstraint` (`models.py:146-148`). Os dois ids são atualizados no upsert (`senate_voting_normalization.py:46-47`, lista `VOTING_UPDATABLE`). **`process_id` e `matter_id` não são únicos**: várias votações podem apontar para o mesmo processo.
- `_int` (`apps/legislature/parsing.py:31-41`) aceita só inteiro positivo até `INT32` (2.147.483.647); os maiores ids medidos (9.141.063 e 176.628) cabem. **Linha com `idProcesso` ou `codigoMateria` ausente, zero ou não inteiro recusa a normalização inteira** (`senate_voting_parsing.py` levanta `RowError` com o nome da coluna; falha fechada, `senate_voting_normalization.py:143-144`).
- O conjunto `senado/votacoes` tem `idProcesso` e `codigoMateria` na lista de colunas permitidas do cadastro (`apps/sources/catalog.py:189-190`).
- A API interna expõe os dois como `id_processo` e `codigo_materia` (`apps/legislature/views.py:203-204`).
- **Não lido por aqui:** o front (`web/`) e qualquer tela que use `id_processo`; as migrações.

### Medição pela API

Bloco 3 do script. `GET /votacao?dataInicio=2025-11-29&dataFim=2026-11-28` (365 dias, 2026-11-28 13:59 UTC): **90 votações**, `dataSessao` de 2025-12-03 a 2026-11-18, 1,7 MB, 0,66 s. Em 90 de 90, `idProcesso` e `codigoMateria` estão presentes e são inteiros; **71 processos distintos**, e os pares (`idProcesso`, `codigoMateria`) são 71, ou seja, 1:1 também aqui.

**Votações por processo.** Em 365 dias, 90 votações para 71 processos (várias votações do mesmo processo).

| Cruzamento (as 90 votações, 71 processos) | Processos | Votações |
|---|---|---|
| `idProcesso` aparece em `/processo?ano=2026` | 27 | 33 (37%) |
| aparece em `/processo?tramitando=S` | 1 | 1 |
| aparece em um dos dois | 28 | **34 (38%)** |
| **não aparece em nenhum dos dois** | **43** | **56 (62%)** |
| aparece em `/processo?ano=2025` | 30 | 35 |
| aparece em `/processo?tramitouLegislaturaAtual=S` | 71 (100%) | 90 (100%) (**por construção nesta janela**: como o filtro devolve 26.978 processos de 1984 a 2026 e cobre todos os 71 aqui, não prova que cobriria uma janela maior) |

- Os 43 processos fora dos dois filtros foram buscados diretamente: `GET /processo?idProcesso=<id>&idProcesso=<id>...` com os 43 ids numa requisição só (47 KB, 0,36 s) devolveu **os 43**, todos com `tramitando = Não`, todos `SF`. **43 de 43** com o mesmo `codigoMateria` e a mesma `identificacao` da votação. Nos 28 achados pelos filtros: 28 de 28 iguais também.
- **Votações de processos de anos anteriores a 2026** (campo `ano` da votação, que é o ano do número da proposição): **57 de 90** (63%). Por ano: 2025 (35), 2024 (2), 2023 (5), 2022 (3), 2021 (5), 2020 (1), 2019 (6); 2026 (33). **22 votações** são de processos numerados antes de 2025. Siglas das 90: `MSF` 30, `PLP` 27, `PEC` 17, `OFS` 8, `PL` 4, `RQS` 2, `PDL` 2.
- **Medido nesta janela, amostra única, confiança média:** o filtro `ano=2026` liga **33 de 90 votações (37%; 27 de 71 processos)**. Os 34 de 90 (38%; 28 de 71) da tabela incluem 1 votação achada **só** por `?tramitando=S`, que não é de 2026. Somar `ano=2025` ligaria 68 de 90 (35 + 33; `ano=2025` e `ano=2026` não têm id em comum, bloco 7), e sobrariam 22 votações de processos numerados de 2019 a 2024. Se isso "não funciona" para o Senado é **julgamento do dono, não medida**: o que se mediu é só a fração.
- **A janela puxa a fração de 2026 para baixo.** A janela de 365 dias (2025-11-29 a 2026-11-28) inclui **16 votações de dezembro de 2025**, que não podem ser de processo numerado em 2026 (0 de 16 têm `ano` 2026; não confundir com as 35 votações de processos **numerados** em 2025). Só com `dataSessao` de 2026 (bloco 7):

  | Votações com `dataSessao` >= 2026-01-01 | Processos | Votações |
  |---|---|---|
  | total | 60 | 74 |
  | `idProcesso` em `?ano=2026` (e em `ano=2026` ou `tramitando=S`: o mesmo, 33 e 27) | 27 | **33 (45%)** |
  | `idProcesso` em `?ano=2025` ou `?ano=2026` | n/m | 63 (85%) |
  | campo `ano` anterior a 2026 | n/m | 41 (55%); anterior a 2025: 11 (15%) |

  Ou seja, mesmo só com votações de 2026, **41 de 74 (55%)** são de processos numerados antes de 2026. As 33 votações de processo de 2026 são **todas** de 2026 (nenhuma em dez/2025).
- **A fração tende a decair, se o escopo for um ano fixo** (com janela móvel não decai). `SenateVoting` só acumula (docstring de `SenateVoting`, `models.py:113-114`: "A tabela só acumula: votação que sai da janela de coleta continua aqui"; ADR 0029, não relido por aqui): a cada ano que passa, mais votações do banco apontam para processos de anos anteriores ao "ano corrente" do escopo. A medição é de uma data só; a tendência é inferência.
- `identificacao` da votação coincide **exatamente** com a do processo nos 71 casos; nenhuma das siglas votadas (`MSF`, `PLP`, `PEC`, `OFS`, `PL`, `RQS`, `PDL`) é `REQ`, que é a única sigla com sufixo ` - <ente>` na lista de 2026.
- **Limite:** é uma janela só (90 votações, 74 de 2026). Votações de comissão (`votacaoComissao`) não entram em `/votacao` e não foram medidas.

## 4. Proposta (não decisão): chave de origem

**Proposta:** `id` do processo (`/processo`.`id`, o mesmo valor de `idProcesso` das votações) como id de origem; `codigoMateria` guardado como atributo, não como chave.

Por quê, com o que foi medido:

1. **É o que as votações já guardam como ligação** (`SenateVoting.process_id`, `models.py:133`) e vem em 90 de 90 votações; não há processo votado sem ele.
2. **1:1 com `codigoMateria`** nos 28.355 processos lidos (e 71 de 71 nas votações): trocar de um para outro não perde informação nem cria ambiguidade.
3. **`codigoMateria` é o id legado**: o `senado.md` registra que o endpoint `/materia/{id}` está depreciado com `Sunset` vencido, e que o sucessor é `processo/{idProcesso}`. O ADR 0008 (decisão 7) pede que não se construa nada novo sobre endpoints depreciados.
4. **`identificacao` não serve de chave por si só**: é única nos dados lidos, mas o texto tem três formas, o número base se repete em `REQ` (31 vezes para `REQ 1/2026`) e o `ano` do número não é o ano da apresentação (os filtros `ano=2026` e `dataApresentacao` em 2026 divergem em **724** processos: 716 só por data e 8 só por `ano`). Serve como texto legível e como chave natural **com** o sufixo, se o dono preferir algo legível.
5. **Consulta por id é barata**: `?idProcesso=` aceita vários ids numa requisição (43 numa só, 0,36 s) e `/processo/{id}` devolve o detalhe.

Contra-pontos que o dono deve pesar: `id` é um número opaco, sem significado; a estabilidade dos ids no tempo **não foi medida** (uma data só); e o `codigoMateria` é o id legado (o `senado.md` cita "código legado da matéria do MATE"), que a votação também traz; guardá-lo como atributo custa pouco e preserva a ligação com qualquer material antigo que o use (não medi se existe).

Para a fonte do escopo temporal, os dados medidos deixam três caminhos, **sem recomendar**: (a) por ano de número (`?ano=2025` + `?ano=2026`, 8.470 itens, 68 de 90 votações ligadas na janela medida); (b) `?tramitouLegislaturaAtual=S` (26.978 itens, 22,9 MB, 42 s numa amostra não confiável; 90 de 90 ligadas nesta janela, **por construção nesta janela**); (c) por demanda, só os processos que as votações citam, via `?idProcesso=` (71 ids na janela medida; 90 de 90 por construção), no mesmo espírito do ADR 0033 (a Câmara cobre as votações). `numdias` (até 30) atende o incremental em qualquer das três.

## Perguntas para o dono

1. **Escopo temporal.** O filtro `ano=2026` liga 33 de 90 votações medidas (37%; 33 de 74, 45%, se só se contam as votações de 2026; com `tramitando=S` seriam 34 de 90, 38%), numa janela única; a fração tende a cair com o tempo se o escopo for um ano fixo, porque a tabela de votações acumula. Na Câmara a cobertura vem dos arquivos de votações (ADR 0033, decisão 1); aqui `ano=2026` liga 33 de 90 (45% das 74 votações de 2026). Se isso basta é decisão sua. Qual escopo vale para o Senado: (a) 2025 + 2026, (b) a legislatura atual (`tramitouLegislaturaAtual`, 26.978 itens; 22,9 MB numa requisição, 42 s numa medição não confiável), (c) só os processos citados por votações, ou (d) outro?
2. **Quais tipos entram.** Em 2026, `REQ` e `RQS` são 64% dos 3.467 (1.413 + 816). Entram todos os 27 tipos, ou só os legislativos (`PL`, `PLP`, `PEC`, `PDL`, `MPV`, `PRS`, `VET`, `PLN` e afins)? As votações medidas usam só `MSF`, `PLP`, `PEC`, `OFS`, `PL`, `RQS` e `PDL`. **Atenção:** restringir a `PL`, `PLP`, `PEC`, `PDL`, `MPV`, `PRS`, `VET` e `PLN` deixa **40 de 90 votações (44%) sem processo** na base (`MSF` 30, `OFS` 8, `RQS` 2; bloco 7), e a votação guarda `process_id` obrigatório (`models.py:133`).
3. **Chave de origem.** Concorda com o `id` do processo (e o `codigoMateria` como atributo)? Quer guardar também `identificacao`, com o sufixo de ente em `REQ`, como texto de exibição?
4. **Autoria.** `autoria` (texto de até 12.010 caracteres, em todos os itens) **não está** na allowlist do Senado do ADR 0005 (a lista diz: `id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL). Não imprimi nenhum valor (só contei, bloco 5); em 67 `PL` de 2026 o texto cita `Câmara`, e é provável que traga nomes de parlamentares. Fica fora, entra como ligação por código (como o ADR 0033 fez com `deputado_id`), ou entra? É decisão de allowlist e de dado pessoal (ADR 0005 e P-16), não minha.
5. **Campos da allowlist (ADR 0005).** Hoje a lista do Senado diz "(`id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL)". Os campos reais da listagem são `casaIdentificadora`, `enteIdentificador`, `tipoDocumento`, `tipoConteudo`, `tramitando`, `situacaoAtual`, `dataSituacaoAtual`, `dataUltimaAtualizacao`, `ultimaInformacaoAtualizada`, `objetivo`, `dataDeliberacao`, `siglaTipoDeliberacao`, `apelido`, `normaGerada` e `urlDocumento`. Quais entram? A interpretação de "tipo" (`tipoDocumento` ou `tipoConteudo` ou a sigla) é do dono.
6. **Texto da ementa.** `ementa` tem `\n` (388), `\r` (313) e TAB (5) na amostra: usar a mesma regra do ADR 0033 (decisão 7: quebra de linha e TAB viram um espaço; outros controles recusam)? Teto de caracteres: a maior medida foi 5.104.
7. **Processos de outra casa e do Congresso.** `CN` é 10% de 2026 (347 de 3.467). Entra? E a ligação com a proposição de origem da Câmara (`idProcessoCasaInicial`, só no detalhe, uma requisição por processo) está dentro desta fatia ou fica para depois?
8. **Fonte de leitura.** `/processo` respondeu em menos de 1,2 s exceto `tramitouLegislaturaAtual` (42 s) e um detalhe (4,95 s), **mas as latências não são confiáveis** (outra sessão mediu ao mesmo tempo). O prazo total do `PoliteClient` é de 30 minutos (ADR 0008, Consequências), mas **não li** o teto de bytes do leitor JSON; aceita-se uma requisição de 23 MB e 42 s como carga diária, ou prefere-se o desenho por `numdias`?

## Não verificado

- **Estabilidade dos ids no tempo.** Uma data só (2026-11-28). Não sei se `id` ou `codigoMateria` mudam (por exemplo na "remodelagem dos sistemas" que a descrição da API cita) nem se processos são reidentificados ou retirados. A unicidade 1:1 vale para o instante da medição.
- **Todos os anos.** Medi 2025 e 2026 por `ano`, os tramitando de todos os anos, "tramitou na legislatura atual" (o filtro devolveu números de 1984 a 2026; o que ele considera "legislatura atual" **não foi verificado**) e os 43 ids das votações; não varri `?ano=` de 1988 a 2024. Processos antigos que não tramitam nem tramitaram na legislatura atual não estão na união.
- **Amostra de votações:** uma janela de 365 dias (90 votações, 71 processos). A fração ligada a `ano=2026` (37% das 90; 45% das 74 de 2026) é desta janela; votações de outros períodos não foram medidas, e a fração muda com o tempo. Votações secretas e votações de comissão não são o foco.
- **Significado de `tramitouLegislaturaAtual`** e por que 364 processos de 2026 ficam fora; só medi a diferença.
- **Conteúdo de `autoria`** (nomes, tipos de autor) e se contém dado pessoal; não imprimi valores (só contei, bloco 5).
- **Detalhe `/processo/{id}`:** n=3, nenhum `REQ`; não medi tramitações (`autuacoes`), despachos, relatoria nem o volume de uma coleta por detalhe.
- **429 e 503:** nenhum status 429, 503 ou 403 apareceu nas 18 requisições (status impresso por `-w`); não testei o limite de propósito. **Cabeçalhos só foram gravados em 4 respostas** (ver "Como foi medido"): `Retry-After` ausente nelas, e **não sei** nas outras 14.
- **Concorrência e latência:** outra sessão da equipe (#372) mediu o Senado ao mesmo tempo (13:58 a 14:07 UTC, mesmo `User-Agent`), contra o pedido de série do ADR 0008 (decisão 5). **A latência deste documento não é confiável**: 42,07 s (`tramitouLegislaturaAtual`) e 4,95 s (detalhe `8983497`) são uma amostra cada, podem ser contaminadas pela outra sessão, pela rede ou por cache de borda (`Age` de 178 a 2.404 s nas 4 respostas com cabeçalho).
- **O código do polis só foi lido nos arquivos citados.** Não li o front, as migrações nem outros consumidores de `process_id`.
- **O script foi rodado sobre as respostas gravadas** (Python 3.14, `python3 -I`) e quase todos os números deste texto saem dos blocos 1 a 7 (as contagens dos blocos 5 a 7 apareceram primeiro em consultas avulsas e foram incorporadas ao script depois). **Exceções, sem comando no script ("avulso, não reproduzível por ele"):**
  - os tempos, tamanhos e códigos de status da tabela de requisições (saída do `curl -w` na hora);
  - os cabeçalhos das 4 respostas gravadas com `-D` (`Age`, `cache-control`);
  - a leitura dos 3 detalhes `/processo/{id}` (campos, `siglaCasaIniciadora`, `idProcessoCasaInicial`, `identificacaoExterna` vazio, `numero` texto e `ano` inteiro): n=3, respostas no scratchpad;
  - a lista dos 43 ids fora dos filtros foi gravada num arquivo à parte na hora (o bloco bash a recalcula pelo mesmo critério, mas esse recálculo não foi executado);
  - a descrição e os parâmetros de `/processo` na especificação (`documentado`, lidos num trecho avulso do `api-docs`; o script só imprime versão, caminhos e depreciados);
  - os exemplos de `identificacao` fora do formato `SIGLA N/AAAA`: o script só conta (40 em `?tramitando=S` sem ano no formato, 1.420 em 2026); os exemplos vistos foram `MPV 2167-53/2001` (traço no número) e o par `REQ 1/2026 - CDIR` e `REQ 1/2026 - MPV 1323/2025`, lidos numa consulta avulsa;
  - os 4 `-D` e os valores de `Age` (acima).
- **Os arquivos de resposta não estão no repositório**; quem repetir a medição obterá números maiores (o Senado atualiza `/processo` todo dia).

**Para quem cita este arquivo:** referir por **seção** (por exemplo "seção 3, cruzamento só com 2026"), nunca por número de linha. Os únicos cabeçalhos HTTP gravados (`-D`) foram em 4 respostas: `?ano=2026`, `/processo/8986903`, `?codigoMateria=172391` e `?sigla=PEC&ano=2026`. **Não** houve cabeçalho gravado para `?tramitando=S` nem para as outras 14.
