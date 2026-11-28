# Senado: `/processo` e os ids das votações (medição, 2026-11-28)

Complementa [`senado.md`](senado.md), que já mediu o formato de `/processo` e `/votacao` (Rodadas 1 a 4) e que **não foi refeito aqui**. Esta medição existe para a fatia de proposições e tramitações do Senado (equivalente aos ADR 0033, 0034 e 0035 da Câmara): antes de modelar, medir volume, ids e a correspondência com as votações que o banco já guarda. **Este documento não decide modelo nem chave**: relata o medido e deixa as perguntas para o dono.

Rótulos: **medido** (com o comando) e **documentado** (com a fonte). Datas em UTC.

## Como foi medido

- **Data e hora:** 2026-11-28, de 13:58 a 14:02 UTC (18 requisições `GET`, em série, uma a cada 3 s ou mais, a primeira só abre a especificação).
- **Máquina:** uma só, sem paralelismo. Latências dependem da rede dela.
- **Identificação do coletor:** `User-Agent: polis-coletor (+https://github.com/masterlxz/polis)` (o `USER_AGENT` de `apps/sources/http_client.py:84`), como manda o ADR 0008, decisões 4 e 5. Todas as respostas foram `200`; nenhum `429`, `503` nem `403`.
- **Versão da API na época:** `4.1.3.120` (medido em `/v3/api-docs`; `senado.md` registrou `4.1.3.113` em 2026-11-05). 157 caminhos e 42 depreciados, os mesmos números de `senado.md`. Não comparei os campos entre as duas versões.
- **Respostas** gravadas fora do repositório (scratchpad da sessão); nada foi commitado além deste texto. Só estrutura e contagens: nenhum valor de `autoria` ou de nome foi impresso.

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
g miss_lookup "processo?$Q"       # $Q = idProcesso=<id>&idProcesso=<id>... (43 ids, ver seção 3)
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

| Requisição | Status | Bytes | Tempo (s) |
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

Os números abaixo saem do script a seguir, rodado sobre essas respostas (`python3 -I reproduz.py`, com `M` apontando para o diretório delas). Cada seção diz de qual bloco vem o número.

<details>
<summary>Script de contagem (reproduz.py)</summary>

```python
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
```

</details>

## 1. Volume de `/processo` em 2026

### Como filtrar e paginar

- **Documentado** (descrição de `/processo` em `/v3/api-docs`, versão 4.1.3.120): é obrigatório informar ao menos um de `numero`, `ano`, `idProcesso`, `codigoMateria`, `tramitando` (`S`; **é o padrão se nenhum outro for informado**), `tramitouLegislaturaAtual`, `codigoParlamentarAutor`, `codigoClasse`, `codigoAssuntoEspecifico`, `sigla` + `siglaEnteIdentificador`, `dataInicioApresentacao`, `dataFimApresentacao`, `dataInicioDeliberacao`, `dataFimDeliberacao`, `numeroNorma`, `anoNorma`, `numdias` (máximo 30). `sigla` e `idProcesso` são arrays (repetíveis na consulta). Com `dataInicioApresentacao` ou `dataFim...` sozinhos, a descrição diz que o retorno cobre no máximo 1 ano. Não há `pagina` nem `tamanho` na lista de parâmetros.
- **Medido:** nenhuma paginação. `?ano=2026` devolveu os 3.467 itens numa resposta só (3,1 MB, 0,69 s); `?idProcesso=` repetido 43 vezes devolveu os 43.
- **Medido:** `?ano=` filtra pelo **ano do número** (o que vem depois da barra em `identificacao`), **não** pela data de apresentação. Em `?ano=2026`, 3.467 de 3.467 têm `2026` em `identificacao`, mas 8 foram apresentados em 2024 e 2025 (`dataApresentacao`). Por outro lado, `dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28` devolveu **4.175** itens: 3.459 em comum com `?ano=2026`, **716 só por data** (numerados em 2025, 2024, 2023 e antes: 383 `PDL`, 326 `PL`, 3 `PEC`, 3 `PLP`, 1 `VET`; blocos 1 e 6) e 8 só por `ano`. Os dois filtros não são o mesmo conjunto.
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
| Siglas no cadastro `/processo/siglas` | 184 (82 sem `dataFim`) |

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

- `?ano=2025` e `?ano=2026` não têm nenhum id em comum (0 de 5.003).
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
| Consulta por `codigoMateria` | `?codigoMateria=172391` devolveu 1 item, `id` 8986903, `PEC 1/2026` (o mesmo de `senado.md`) |
| Consulta por `id` | `/processo/8986903` (detalhe, 55 KB) e `?idProcesso=` (lista, repetível) funcionam; o detalhe tem `id`, `codigoMateria`, `sigla`, `numero` (texto), `ano` (inteiro) e `identificacao` |

**Limite da afirmação "1:1":** vale para os 28.355 processos que as consultas desta rodada devolveram (2026, 2025, tramitando de todos os anos, "tramitou na legislatura atual", mais os 43 das votações). Não varri todos os anos nem os processos antigos que nunca tramitaram na legislatura atual.

### `identificacao`

- **Medido:** `identificacao` é única nos 28.355 ids da união (0 repetidas; também 0 repetidas em cada conjunto separado e 0 pelo par `identificacao` + `casaIdentificadora`).
- **Mas o texto muda de forma** (`?ano=2026`, 3.467 itens): 2.047 são `SIGLA N/AAAA`; **1.413 são `REQ N/AAAA - <ente>`** (por exemplo `REQ 1/2026 - CDIR`, `REQ 1/2026 - MPV 1323/2025`) e 7 são `PL N/AAAA (Substitutivo-CD)` (do tipo `Emenda`, não `Projeto de Lei Ordinária`). O número base `SIGLA N/AAAA` se repete 142 vezes em 2026, **sempre em `REQ`** (um `REQ 1/2026` por comissão ou ente: `REQ 1/2026` aparece 31 vezes, uma por colegiado; bloco 6). Fora de `REQ`, o número base não se repete.
- **Medido:** cada colegiado numera os seus requerimentos de 1 a N, e a distinção entre eles está no **sufixo do texto** e no `enteIdentificador`, não no número. O campo `sigla`+`numero`+`ano` do detalhe `/processo/{id}` foi lido em 3 processos (`PEC 1/2026`, `PL 159/2026 (Substitutivo-CD)`, `PL 199/2026`), nenhum `REQ`; **não medi** se o detalhe de um `REQ` traz o ente em outro campo.
- `casaIdentificadora` só tem `SF` e `CN` (`CN`: 347 de 3.467 em 2026: `REQ` 151, `MPV` 68, `VET` 56, `PLN` 35, `AVN` 22, `R.C` 6, `PCS` 3, `OFN` 2, `RRC` 2, `RQN` 1, `MCN` 1; bloco 6).

### Origem na Câmara (3 detalhes lidos)

O detalhe `/processo/{id}` traz `siglaCasaIniciadora`, `idProcessoCasaInicial` e `identificacaoProcessoInicial`. Medido em 3 processos:

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
| `dataUltimaAtualizacao`, `ultimaInformacaoAtualizada` | 8.790 | 3.197 | n/m | `dataUltimaAtualizacao` com horas e milissegundos (`2026-10-21T17:09:43.956`); ausentes em 19.565 da união |
| `objetivo` | 12.742 | 718 | 12 | |
| `dataDeliberacao`, `siglaTipoDeliberacao` | 14.332 | 1.274 | n/m | |
| `apelido` | 706 | 106 | 260 | |
| `normaGerada` | 3.311 | 155 | 50 | texto, não objeto |

- `ementa` tem **quebra de linha em 388 processos** (`\n`), **CR em 313** e **TAB em 5**, na união (mesma família de problema do ADR 0033, decisão 7); nunca vazia.
- `tramitando` e `casaIdentificadora` nunca nulos.

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
| aparece em `/processo?tramitouLegislaturaAtual=S` | **71 (100%)** | **90 (100%)** |

- Os 43 processos fora dos dois filtros foram buscados diretamente: `GET /processo?idProcesso=<id>&idProcesso=<id>...` com os 43 ids numa requisição só (47 KB, 0,36 s) devolveu **os 43**, todos com `tramitando = Não`, todos `SF`. **43 de 43** com o mesmo `codigoMateria` e a mesma `identificacao` da votação. Nos 28 achados pelos filtros: 28 de 28 iguais também.
- **Votações de processos de anos anteriores a 2026** (campo `ano` da votação, que é o ano do número da proposição): **57 de 90** (63%). Por ano: 2025 (35), 2024 (2), 2023 (5), 2022 (3), 2021 (5), 2020 (1), 2019 (6); 2026 (33). **22 votações** são de processos numerados antes de 2025. Siglas das 90: `MSF` 30, `PLP` 27, `PEC` 17, `OFS` 8, `PL` 4, `RQS` 2, `PDL` 2.
- **Conclusão medida (uma janela de 365 dias):** "só 2026" **não** cobre as votações do Senado: ligaria 33 de 90 (37%) pelo ano do número, ou 34 de 90 com os tramitando. Somar 2025 elevaria para 68 de 90 (35 + 33, não há id em comum entre `ano=2025` e `ano=2026`), e ainda sobrariam 22 votações de 2019 a 2024. Só `tramitouLegislaturaAtual=S` cobriu 100% (e `?idProcesso=`, por construção).
- `identificacao` da votação coincide **exatamente** com a do processo nos 71 casos; a da votação não traz o sufixo ` - <ente>` porque as siglas votadas (`MSF`, `PLP`, `PEC`, `OFS`, `PL`, `RQS`, `PDL`) não são `REQ`.
- **Limite:** é uma janela só (90 votações). Votações de comissão (`votacaoComissao`) não entram em `/votacao` e não foram medidas.

## 4. Proposta (não decisão): chave de origem

**Proposta:** `id` do processo (`/processo`.`id`, o mesmo valor de `idProcesso` das votações) como id de origem; `codigoMateria` guardado como atributo, não como chave.

Por quê, com o que foi medido:

1. **É o que as votações já guardam como ligação** (`SenateVoting.process_id`, `models.py:133`) e vem em 90 de 90 votações; não há processo votado sem ele.
2. **1:1 com `codigoMateria`** nos 28.355 processos lidos (e 71 de 71 nas votações): trocar de um para outro não perde informação nem cria ambiguidade.
3. **`codigoMateria` é o id legado**: o `senado.md` registra que o endpoint `/materia/{id}` está depreciado com `Sunset` vencido, e que o sucessor é `processo/{idProcesso}`. O ADR 0008 (decisão 7) pede nada novo sobre endpoints depreciados.
4. **`identificacao` não serve de chave por si só**: é única nos dados lidos, mas o texto tem três formas, o número base se repete em `REQ` (31 vezes para `REQ 1/2026`) e o `ano` do número não é o ano da apresentação (8 em 3.467). Serve como texto legível e como chave natural **com** o sufixo, se o dono preferir algo legível.
5. **Consulta por id é barata**: `?idProcesso=` aceita vários ids numa requisição (43 numa só, 0,36 s) e `/processo/{id}` devolve o detalhe.

Contra-pontos que o dono deve pesar: `id` é um número opaco, sem significado; a estabilidade dos ids no tempo **não foi medida** (uma data só); e o `codigoMateria` é o id legado (o `senado.md` cita "código legado da matéria do MATE"), que a votação também traz; guardá-lo como atributo custa pouco e preserva a ligação com qualquer material antigo que o use (não medi se existe).

Para a fonte do escopo temporal, os dados medidos deixam três caminhos, **sem recomendar**: (a) por ano de número (`?ano=2025` + `?ano=2026`, 8.470 itens, 68 de 90 votações ligadas no que mediu); (b) `?tramitouLegislaturaAtual=S` (26.978 itens, 22,9 MB, 42 s numa amostra; 90 de 90 ligadas); (c) por demanda, só os processos que as votações citam, via `?idProcesso=` (71 ids na janela medida; 90 de 90 por construção), no mesmo espírito do ADR 0033 (a Câmara cobre as votações). `numdias` (até 30) atende o incremental em qualquer das três.

## Perguntas para o dono

1. **Escopo temporal.** Só 2026 liga 34 de 90 votações medidas (38%). Qual escopo vale para o Senado: (a) 2025 + 2026, (b) a legislatura atual (`tramitouLegislaturaAtual`, 26.978 itens; 42 s e 22,9 MB numa requisição), (c) só os processos citados por votações, ou (d) outro? O "só 2026" da Câmara (ADR 0033) funciona lá porque os arquivos de votações trazem a proposição junto; aqui não.
2. **Quais tipos entram.** Em 2026, `REQ` e `RQS` são 64% dos 3.467 (1.413 + 816). Entram todos os 27 tipos, ou só os legislativos (`PL`, `PLP`, `PEC`, `PDL`, `MPV`, `PRS`, `VET`, `PLN` e afins)? As votações medidas usam só `MSF`, `PLP`, `PEC`, `OFS`, `PL`, `RQS` e `PDL`.
3. **Chave de origem.** Concorda com o `id` do processo (e o `codigoMateria` como atributo)? Quer guardar também `identificacao`, com o sufixo de ente em `REQ`, como texto de exibição?
4. **Autoria.** `autoria` (texto de até 12.010 caracteres, em todos os itens) **não está** na allowlist do Senado do ADR 0005 (a lista diz: `id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL). Não inspecionei os valores; em 67 `PL` de 2026 o texto cita `Câmara`, e é provável que traga nomes de parlamentares. Fica fora, entra como ligação por código (como o ADR 0033 fez com `deputado_id`), ou entra? É decisão de allowlist e de dado pessoal (ADR 0005 e P-16), não minha.
5. **Campos da allowlist (ADR 0005).** Hoje a lista do Senado diz "(`id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL)". Os campos reais da listagem são `casaIdentificadora`, `enteIdentificador`, `tipoDocumento`, `tipoConteudo`, `tramitando`, `situacaoAtual`, `dataSituacaoAtual`, `dataUltimaAtualizacao`, `ultimaInformacaoAtualizada`, `objetivo`, `dataDeliberacao`, `siglaTipoDeliberacao`, `apelido`, `normaGerada` e `urlDocumento`. Quais entram? A interpretação de "tipo" (`tipoDocumento` ou `tipoConteudo` ou a sigla) é do dono.
6. **Texto da ementa.** `ementa` tem `\n` (388), `\r` (313) e TAB (5) na amostra: usar a mesma regra do ADR 0033 (decisão 7: quebra de linha e TAB viram um espaço; outros controles recusam)? Teto de caracteres: a maior medida foi 5.104.
7. **Processos de outra casa e do Congresso.** `CN` é 10% de 2026 (347 de 3.467). Entra? E a ligação com a proposição de origem da Câmara (`idProcessoCasaInicial`, só no detalhe, uma requisição por processo) está dentro desta fatia ou fica para depois?
8. **Fonte de leitura.** `/processo` tem tempo de resposta baixo (menos de 1,2 s) exceto `tramitouLegislaturaAtual` (42 s) e um detalhe (4,95 s). O prazo total do `PoliteClient` é de 30 minutos (ADR 0008, Consequências), mas **não li** o teto de bytes do leitor JSON; aceita-se uma requisição de 23 MB e 42 s como carga diária, ou prefere-se o desenho por `numdias`?

## Não verificado

- **Estabilidade dos ids no tempo.** Uma data só (2026-11-28). Não sei se `id` ou `codigoMateria` mudam (por exemplo na "remodelagem dos sistemas" que a descrição da API cita) nem se processos são reidentificados ou retirados. A unicidade 1:1 vale para o instante da medição.
- **Todos os anos.** Medi 2025 e 2026 por `ano`, os tramitando de todos os anos, "tramitou na legislatura atual" (2019 a 2026 e antes) e os 43 ids das votações; não varri `?ano=` de 1988 a 2024. Processos antigos que não tramitam nem tramitaram na legislatura atual não estão na união.
- **Amostra de votações:** uma janela de 365 dias (90 votações, 71 processos). A fração ligada a 2026 (38%) é desta janela; votações de outros períodos não foram medidas. Votações secretas e votações de comissão não são o foco.
- **Significado de `tramitouLegislaturaAtual`** e por que 364 processos de 2026 ficam fora; só medi a diferença.
- **Conteúdo de `autoria`** (nomes, tipos de autor) e se contém dado pessoal; não imprimi nem inspecionei valores.
- **Detalhe `/processo/{id}`:** n=3, nenhum `REQ`; não medi tramitações (`autuacoes`), despachos, relatoria nem o volume de uma coleta por detalhe.
- **429 e 503:** nenhum ocorreu (18 requisições, uma a cada 3 s ou mais); não testei o limite de propósito. Sem `Retry-After` visto.
- **Latência:** uma amostra por requisição, de uma só máquina; a de `tramitouLegislaturaAtual` (42 s) e a do detalhe `8983497` (4,95 s) podem ser acaso ou cache de borda (o cabeçalho `Age` apareceu na resposta de `?ano=2026`).
- **O código do polis só foi lido nos arquivos citados.** Não li o front, as migrações nem outros consumidores de `process_id`.
- **O script `reproduz.py` foi rodado uma vez** (Python 3.14, `python3 -I`), sobre as respostas gravadas, e os números deste texto foram conferidos contra a saída dele. Algumas contagens apareceram primeiro em consultas avulsas e foram depois incorporadas ao script (blocos 5 e 6); o que não está no script: a conferência de `?ano=2026&tramitando=S`, `?ano=2026&sigla=PL` e `?sigla=PEC&ano=2026` contra o filtro local (blocos 1 e 6 mostram só `tramitando=S` e a contagem total), e a leitura dos 3 detalhes `/processo/{id}`.
- **Os arquivos de resposta não estão no repositório**; quem repetir a medição obterá números maiores (o Senado atualiza `/processo` todo dia).
