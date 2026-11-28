# Senado: tramitações do processo legislativo (medição de 2026-11-28)

Complementa [senado.md](senado.md) (que já mede `/processo` e `/votacao`; nada daquilo foi refeito) e serve de base para a fatia de tramitações do Senado, no papel que a "Rodada 5" de [camara.md](camara.md) teve para o ADR 0034. **Nada foi integrado e nada aqui decide o modelo**: relata o medido e levanta perguntas para o dono (última seção).

Rótulos: **medido** (com o comando, na seção "Comandos", e a saída) ou **documentado** (com a fonte). Datas e horas desta medição em UTC. Medições feitas de uma só máquina, em série, de **2026-11-28T13:58Z a 14:07Z**, com `User-Agent: polis-coletor (+https://github.com/masterlxz/polis)` (a constante `USER_AGENT` em `apps/sources/http_client.py:84`, lida), pausa de 3 s entre requisições, **55 requisições** no total, nenhuma 429, 503 ou 403 e nenhum cabeçalho `Retry-After` ou `RateLimit` nas respostas guardadas (medido: `grep -ic 'retry-after\|ratelimit'` nos cabeçalhos de 5 respostas deu 0 em todos; as demais respostas só tiveram o código e o tamanho conferidos). Versão da API na especificação de hoje: `4.1.3.120` (a de `senado.md` era `4.1.3.113`; 157 caminhos e 42 depreciados, como antes).

## Resumo

1. **As tramitações estão só no detalhe `GET /processo/{id}`**, dentro de `autuacoes[]` (sempre 1 autuação nos 46 processos medidos). Não existe arquivo nem endpoint em massa de movimentações por período (pelos resumos da especificação e pelo catálogo; ver "Onde estão"). Uma carga é **uma requisição por processo**.
2. **O que o Senado chama de tramitação tem três formas** no mesmo detalhe: `informesLegislativos` (texto livre com data e hora, a mais parecida com a tramitação da Câmara), `movimentacoes` (envio e recebimento entre órgãos, sem texto) e `situacoes` (estado com início e fim, só data). Ver "Formato".
3. **`informesLegislativos` vem com cópias exatas**: 1.316 itens brutos viram 670 distintos por `id` (49% são cópia idêntica, campo a campo). O `id` do informe é inteiro e, na amostra, único por processo e nunca repetido entre processos. **Não há campo de sequência**; os itens vêm em ordem crescente de `data`.
4. **Volume:** mediana de 6 informes distintos por processo (amostra aleatória, n = 24), detalhe de 2,6 KB a 94 KB (mediana 9 KB), mas o pior caso medido foi 978 KB (208 informes). Estimativa **muito incerta** de informes com data em 2026: cerca de **16 mil** (bootstrap 5,4 mil a 28,4 mil), contra 118.684 da Câmara. Uma carga completa por detalhe leva **3,5 h** (os 4.175 processos apresentados em 2026) a **10,7 h** (os 12.871 que tramitam ou foram apresentados em 2026) só de pausas de 3 s. A atualização diária pode usar o filtro `numdias` de `/processo`.
5. **Hora 00:00:** em 2026 só **1 de 220** informes distintos (0,45%) tem hora exatamente `00:00:00`, contra 28,2% das tramitações da Câmara (ADR 0035, emenda 1) e ~0,07% por acaso. O padrão "meia-noite" do Senado aparece sobretudo em processos **antigos** (31 dos 34 `00:00:xx` são de 2019 ou antes, 2 de 2023 e 1 de 2026), na forma `00:00:01`, `00:00:02`... Amostra pequena: ver "Hora".
6. **O texto livre é um só campo (`descricao`)**, sem equivalente separado de `despacho`; cita senadores (324 de 670) e convidados de audiência com nome e cargo (alguns cargos sugerem particulares). Sem CPF, e-mail ou telefone nos 670 textos (regex). O ADR 0005 não foi avaliado para este campo.

## Onde estão as tramitações (medido e documentado)

- **Documentado (especificação, `GET /v3/api-docs`):** o `GET /dadosabertos/processo/{id}` é "Detalhes de um Processo Legislativo" ("identificação, ementa, [...] autoria, [...] decisão, destino, norma gerada, entre outros"); a descrição não cita tramitação nem informes. O esquema da resposta é uma referência externa (`schemas/processo.yml#/components/schemas/Processo`) que **não vem dentro do arquivo**, então os campos abaixo foram descritos **a partir do dado**, não da documentação.
- **Documentado (catálogo `geracsv`, 2026-11-28):** há dois conjuntos chamados "Tramitações da Matéria Legislativa" e "Atualizações da Matéria Legislativa", ambos com `txt_url` apontando para o Swagger de `Processo/detalhesProcesso`, frequência "Diário". Ou seja, o próprio catálogo manda ler a tramitação do detalhe.
- **Sem listagem em massa (medido na especificação, só pelos resumos):** dos 157 caminhos, os que citam andamento, tramitação, movimentação ou despacho no caminho, no resumo ou na descrição são `/processo/prazo`, `/processo/entes`, `/processo` (a lista), `/materia/vetos/{encerrados,aposrcn,antesrcn}`, `/materia/lista/tramitacao` (total por tipo ou colegiado) e cinco de `/materia/*` **depreciados** (`tramitando`, `situacaoatual/tramitacao/{data}`, `movimentacoes/{codigo}`, `lista/prazo/{codPrazo}`, `legislaturaatual`). Pelos resumos, nenhum devolve os informes de todos os processos por período; **não abri cada um** e não chamei nenhum. Nada novo sobre os depreciados, pelo ADR 0008, decisão 7.
- **As listas `/processo` não trazem tramitação** (medido: as chaves de cada item são só dados básicos; `dataUltimaAtualizacao` e `ultimaInformacaoAtualizada` faltam nas listas de 2026 e de `tramitando=S` e aparecem com o filtro `numdias`).
- **Filtro de atualização (documentado e medido):** `numdias` ("Atualizadas nos últimos N dias. O máximo é 30"). `GET /processo?numdias=1` devolveu 328 processos (289.573 B) e `numdias=7` devolveu 1.110 (1.003.765 B), cada item com `dataUltimaAtualizacao` (`aaaa-mm-ddThh:mm:ss.mmm`, sem fuso). **Medido: o "1 dia" abrangeu atualizações de 2026-11-25T17:37 a 2026-11-27T18:54**, mais de 24 h antes de 2026-11-28T14:04Z; a semântica exata da janela **não foi verificada**.
- **Inexistente (medido):** `GET /processo/1` devolveu **404** com corpo `{"instance":"/dadosabertos/processo/1","status":404,"title":"Not Found"}` (72 B). É diferente do `/senador/99999999` de `senado.md`, que dava 200 sem dados; um id só, não generalizo.
- **Cache (medido):** os detalhes saem com `cache-control: max-age=1800, s-maxage=1800` e `Age` (99 s no PEC 1/2026); a lista `/processo?tramitando=S`, com 1800 s. Latência do detalhe: 0,23 a 0,46 s (46 respostas). Lista `dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28`: 3.744.740 B em 5,4 s; `?tramitando=S`: 9.221.974 B em 0,8 s.

## Formato (medido, 46 processos)

Chaves de topo presentes em todos os 46 detalhes: `ano, autuacoes, casaIdentificadora, codigoMateria, comissaoMpv, conteudo, dataInicioEfetivo, deliberacao, descricaoSigla, documento, id, identificacao, identificacaoExterna, normaGerada, numero, sigla, siglaEnteIdentificador, tramitando` (42 chaves no total; as outras variam por tipo). `dthUltimaAtualizacao` (`aaaa-mm-ddThh:mm:ss.uuuuuu`, sem fuso) está em 32 dos 46.

**`autuacoes[]`** (1 por processo nos 46): `numero`, `descricao` ("Autuação Principal"), `codigoColegiadoControleAtual`, `siglaColegiadoControleAtual` e outros campos do colegiado e do ente de controle, `situacoes[]`, `informesLegislativos[]`, `movimentacoes[]` (lido no PEC 1/2026; nos 46, só conferi as três listas). Em REQ de comissão e PET `informesLegislativos` pode faltar ou ser vazio (3 de 24 na amostra aleatória não têm nenhum).

| Lista | Itens (46 processos) | Chaves (tipo) | Data e hora |
|---|---|---|---|
| `informesLegislativos` | 1.316 brutos, 670 distintos | `id` (int), `data` (str), `colegiado` (objeto: `codigo`, `casa`, `sigla`, `nome`; **vazio `{}` em 70 de 670**), `enteAdministrativo` (objeto: `id`, `casa`, `sigla`, `nome`), `descricao` (str), `idSituacaoIniciada` e `siglaSituacaoIniciada` (só em 248 dos 670 distintos), `documentosAssociados` (lista, em 364 dos 670) | `aaaa-mm-dd hh:mm:ss` em 1.316 de 1.316, **sem fuso** |
| `movimentacoes` | 188 | `id` (int, 188 distintos), `dataEnvio`, `enteOrigem`, `dataRecebimento` (**nulo em 7**), `enteDestino`, `colegiadoDestino` (`{}` em 91) | `aaaa-mm-dd hh:mm:ss`, sem fuso |
| `situacoes` | 269 | `idTipo`, `sigla`, `descricao`, `inicio`, `fim` (ausente em 43), `colegiado`, `enteAdministrativo` | só data `aaaa-mm-dd` |
| `despachos` (topo, fora de `autuacoes`) | 35 | `id`, `data` (só data), `siglaTipoMotivacao`, `tipoMotivacao`, `cancelado`, `encontroLegislativo`, `providencias[]` (rótulos de tipo, sem texto livre) | só data |

Os `id` de informe (93.334 a 2.333.088) e de movimentação nunca coincidem (0 em comum). Um informe de exemplo, **truncado e sem nomes**: `{"id": 2134832, "data": "2023-05-03 19:16:49", "colegiado": {"codigo": 1998, "casa": "SF", "sigla": "PLEN", ...}, "enteAdministrativo": {"id": 55312, "sigla": "SLSF", ...}, "idSituacaoIniciada": 175, "siglaSituacaoIniciada": "AGDESP", "documentosAssociados": [...]}`.

**Dados controlados (medido, 670 informes distintos):** `siglaSituacaoIniciada` tem 34 valores, `colegiado.sigla` 17 e `enteAdministrativo.sigla` 22. O que o Senado oferece como "descrição curta controlada" é, portanto, o estado iniciado (só em 37% dos informes), e não um tipo de tramitação em todos.

**`documentosAssociados`** (2.750 itens nos 670 informes): `id`, `tipo`, `siglaTipo`, `identificacao`, `descricao`, `data` (`aaaa-mm-ddThh:mm:ss`, outro formato, conferido só no exemplo acima), `autoria` (texto com o nome e o partido de quem assina, preenchido em 2.750 de 2.750) e `url`.

## Amostra (medido)

Duas amostras, **separadas porque servem a coisas diferentes**: a **dirigida** (22 processos, escolhidos para cobrir tipos e casos extremos; não serve para estimar volume) e a **aleatória** (24 processos sorteados com semente fixa entre os 12.871 que tramitam ou foram apresentados em 2026; serve para estimar). Colunas: bytes do detalhe, informes brutos / distintos, movimentações, situações.

**Dirigida:**

| Processo | `id` | Bytes | Informes (brutos / distintos) | Mov. | Sit. |
|---|---|---|---|---|---|
| PEC 1/2026 | 8986903 | 55.715 | 6 / 6 | 2 | 6 |
| PEC 12/2026 | 9055580 | 40.896 | 5 / 5 | 2 | 3 |
| PL 2/2026 | 8986931 | 47.921 | 21 / 21 | 4 | 9 |
| PL 168/2026 | 8988413 | 9.983 | 6 / 6 | 2 | 4 |
| PL 856/2025 | 9063446 | 12.433 | 13 / 4 | 2 | 3 |
| PL 2234/2024 | 8989972 | 33.908 | 26 / 24 | 12 | 18 |
| **PL 2338/2023** | 8441243 | 449.253 | **375 / 126** | 21 | 38 |
| PLP 6/2026 | 8987995 | 14.828 | 9 / 9 | 3 | 8 |
| PLP 184/2026 | 9070516 | 8.309 | 3 / 3 | 2 | 3 |
| **PLP 68/2024** | 8701679 | **978.415** | **208 / 207** | **30** | 15 |
| MPV 1333/2026 | 8984726 | 18.927 | 12 / 12 | 5 | 4 |
| MPV 1368/2026 | 9069218 | 23.104 | 13 / 13 | 9 | 7 |
| REQ 1/2026 - CDIR | 8984112 | 5.798 | 2 / 2 | 3 | 3 |
| REQ 210/2026 - CDIR | 9053761 | 3.228 | 0 / 0 | 0 | 2 |
| PDL 2/2026 | 8985534 | 7.816 | 3 / 3 | 2 | 3 |
| PDL 261/2025 | 8985559 | 83.113 | 107 / 13 | 9 | 9 |
| RQS 3/2026 | 8984232 | 6.791 | 4 / 4 | 3 | 3 |
| INS 1/2026 | 8986924 | 6.918 | 4 / 4 | 3 | 3 |
| MSF 1/2026 | 8984950 | 17.039 | 12 / 12 | 5 | 9 |
| PRS 1/2026 | 8998698 | 17.415 | 14 / 14 | 6 | 9 |
| PLN 1/2026 | 9024204 | 27.236 | 25 / 17 | 7 | 10 |
| VET 51/2025 | 8984209 | 79.708 | 145 / 17 | 6 | 6 |

Resumo da dirigida: informes brutos mín 0, mediana 12, máx 375; distintos mín 0, mediana 10,5, máx 207; movimentações mín 0, mediana 3,5, máx 30; bytes de 3.228 a 978.415 (mediana 18.171).

**Aleatória (24):** 11 PL, 6 REQ, 1 de cada VET, OFS, PDL, REP, RQS, MSF e PET (o sorteio não pegou PEC, PLP nem MPV, que somam 155 dos 4.175 de 2026, por isso a dirigida). Informes brutos: mín 0, mediana 6, média 12,6, máx 160 (PDL 470/2023: 160 brutos e 9 distintos); **distintos: mín 0, mediana 6, média 6,2, máx 25**; movimentações: mediana 2, máx 10; situações: mediana 3, máx 12; bytes do detalhe: 2.632 a 94.208, mediana 9.068, média 12.419. Sem informes: 3 de 24 (REQ 193/2026, REQ 277/2026 e PET 21/2026). A tabela completa sai do script A.

## Volume

| Fato | Valor | Rótulo |
|---|---|---|
| Processos apresentados de 2026-01-01 a 2026-11-28 | 4.175 (1.413 REQ, 896 PL, 814 RQS, 447 PDL, 68 MPV, 68 PLP, 19 PEC...), 3.744.740 B | medido (`lista2026.json`; a contagem por tipo não está nos scripts abaixo: `collections.Counter(x["identificacao"].split()[0] for x in lista)`) |
| Processos que tramitam hoje (`tramitando=S`) | 10.951; dos quais 2.255 apresentados em 2026 | medido |
| União dos dois (base do sorteio) | **12.871** | medido (script E) |
| Informes distintos por processo (aleatória) | mediana 6, média 6,2, máx 25 | medido (n = 24) |
| Informes distintos **com `data` em 2026** por processo (aleatória) | 17 processos com 0; soma 30; média 1,25; máx 7 | medido (n = 24) |
| Estimativa de informes com `data` em 2026 nos 12.871 | **≈ 16.089** (bootstrap de 5.000, semente 7: 5.363 a 28.423) | **estimativa**; 24 processos, cauda pesada |
| Estimativa só dos 4.175 apresentados em 2026 | ≈ 9.916 (média 2,38 em **8** processos) | **estimativa**; n = 8 |
| Estimativa dos 8.696 mais antigos que tramitam | ≈ 5.978 (média 0,69 em 16 processos) | **estimativa**; n = 16 |
| Referência: Câmara, 2026 | 118.684 tramitações | ADR 0034 (documentado no repo, não refeito) |
| Bytes de uma carga completa de detalhes | ≈ 160 MB (12.871 × média de 12.419 B) ou ≈ 52 MB (4.175) | estimativa |
| Requisições em série, 3 s de pausa, só a pausa | **12.871 → 10,7 h; 4.175 → 3,5 h** | cálculo (aritmética sobre os números acima) |
| Atualização diária pelo `numdias` | 328 processos em `numdias=1` (16 min de pausas para os detalhes); 1.110 em `numdias=7` (56 min) | medido; semântica da janela não verificada |

**O que a estimativa não cobre:** informes com data em 2026 de processos que **não tramitam hoje e não foram apresentados em 2026** (por exemplo, arquivados em 2026 com início antes); o sorteio não os alcança. A faixa de 5 mil a 28 mil é do bootstrap de uma amostra de 24; a estimativa por estrato (9.916 + 5.978 = 15.894) usa n = 8 e n = 16 e **não é independente** da primeira.

Duplicatas (medido, 46 processos): 646 cópias extras de um `id` no mesmo processo, **todas idênticas ao primeiro** (o dicionário inteiro); 10 dos 42 processos com informes têm alguma. O volume bruto (1.316) é 1,96 vez o distinto (670). **O motivo da duplicação não foi investigado.**

## Hora 00:00 (medido, 670 informes distintos de 46 processos)

| Recorte | Informes | `00:00:00` exato | `00:00:xx` (qualquer segundo) | `00:10:00` |
|---|---|---|---|---|
| Todos os anos | 670 | 1 | 34 (5,1%) | 6 |
| Só 2026 | **220** | **1 (0,45%)** | 1 | 0 |
| 2009 a 2014 | 22 | 0 | 22 | 0 |
| 2019 | 20 | 0 | 9 | 0 |
| 2020 a 2022 | 21 | 0 | 0 | 6 (todos de `2022-12-21 00:10:00`) |
| 2023 a 2025 | 387 | 0 | 2 | 0 |

(o recorte "todos os anos" tem 670 informes; a tabela por ano completa está na saída do script C.)

- **Esperado por acaso:** 1 minuto em 1.440 = 0,069% (a mesma conta do ADR 0035). **Câmara, 2026:** 28,2% (ADR 0035, emenda 1; documentado no repo).
- **O padrão "meia-noite" existe, mas é de processos antigos e tem outra forma:** dos 34 `00:00:xx`, 31 são de 2019 ou antes, com segundos `01` (19), `02` (8), `03` (2), `04` (1) e `05` (1); os outros 3 são 2 de 2023 e o `00:00:00` de 2026. **23 dos 40 informes da hora 00 são de um só processo (VET 36/2009)**, 6 de PL 5956/2019 e 5 de PL 5987/2019. Leitura minha, **inferência**: eventos só com data recebem segundos sequenciais para manter a ordem. O `00:00:00` exato apareceu uma vez em 2026 (`VET 51/2025`, 2026-03-04, "A matéria passa a sobrestar, a partir desta data, a pauta das sessões [...]", um evento automático).
- **Sobre a pergunta "a data vem com ou sem hora":** em **todos** os informes e movimentações o campo é sempre `aaaa-mm-dd hh:mm:ss` (1.316 de 1.316 e 188 de 188; nenhum só com data). O que é só data é `situacoes.inicio|fim` e `despachos.data` (e `dataSituacaoAtual`, `dataApresentacao` etc. da lista).
- **Movimentações:** `dataEnvio` e `dataRecebimento` com `00:00:00`: 0 de 188 e 0 de 181.
- **Amostra:** 220 informes de 2026, vindos de 27 processos (20 da dirigida e 7 da aleatória; linha final do script C), são **poucos** para concluir; 1 evento em 220 não dá uma estimativa precisa da taxa verdadeira (não calculei intervalo). O que a amostra sustenta é só que **nesses 46 processos** não aparece em 2026 o fenômeno de 28% da Câmara; ela não prova que ele não exista em outros tipos de processo ou em outros meses.
- **Fuso (não declarado):** nenhum campo traz deslocamento. Evidência indireta (**inferência, não verificado**): os informes de 2026 vão de 07:xx a 21:xx e se concentram entre 08:00 e 19:59 (script C, histograma), o que é horário de expediente de Brasília e não de UTC (que cairia entre 04:xx e 18:xx de Brasília). Conferi também 3 processos com atualização na véspera (2026-11-27): último informe às 09:02, 11:31 e 12:14, com `dthUltimaAtualizacao` às 11:51, 11:59 e 17:28, o que não contradiz, mas **também não prova**, hora local.

## Ordem e chave natural (medido)

- **Não há campo de sequência** (`sequencia`): as chaves de um informe são só as da tabela de formato.
- **Ordem:** em **42 de 42** processos com informes a lista vem em ordem **crescente** de `data` (empates entre cópias contam como ordem); entre os informes **distintos**, **0 de 42** processos têm dois com a mesma data e hora. Na amostra, portanto, `data` ordenaria sem desempate, mas isso **não é garantia** (46 processos).
- **`id` do informe:** 670 pares (processo, `id`) distintos de 1.316 brutos; **nenhum `id` aparece em mais de um processo**; as 646 repetições são cópias exatas (chave natural candidata: (processo, `id`) com as cópias contando uma vez, como o ADR 0034 faz com as 38 duplicatas da Câmara). Estabilidade do `id` entre cargas: **não medida** (uma carga só).
- **`id` da movimentação:** 188 distintos em 188.
- **Processo:** a chave é o `id` do processo (inteiro, ex. `8986903`); `codigoMateria` é o id legado (senado.md); o detalhe traz os dois.
- **Autuações:** sempre 1 nos 46 (outros tipos podem ter mais; não medido).

## Texto livre e dados pessoais (medido; ADR 0005 não avaliado)

- **Equivalente de `despacho`/texto livre:** `informesLegislativos[].descricao`. Não há campo curto controlado separado como a `descricaoTramitacao` da Câmara (112 valores, até 57 caracteres); o análogo controlado é `siglaSituacaoIniciada`, em 37% dos informes.
- **Tamanho (670 distintos):** mín 12, mediana 137, p99 2.125, **máx 4.176** caracteres; 0 vazios; 19 com espaço no começo ou no fim.
- **Controle:** nenhum caractere de controle além de `\t`, `\n` e `\r` (0 de 670); mas **169 têm `\r\n`, 43 têm `\n` sem `\r` e 1 tem `\t`** (quebra de linha dentro do texto: 212 de 670, 32%). O ADR 0034 (decisão 5) manda recusar "caractere de controle" e a Câmara não tinha nenhum em `descricaoTramitacao` (camara.md, Rodada 5); aqui a quebra de linha é comum. Se o código do polis conta `\n` e `\r` como controle, **não lido por aqui**.
- **Pessoas no texto (regex; não é leitura):** cita "Senador/Senadora" em 324 de 670, "Relator/Relatora" em 87, "Deputado/Deputada" em 12, "Ministro/Ministra" em 11, nome com "(PARTIDO/UF)" em 7, "Sr./Sra./Dr./Dra." em 36 informes (inclui "Dr." de nome de senador) e **145 trechos "Sr./Sra. Nome, cargo"** (o padrão mais estreito; não contei em quantos informes). Pelo que li, são convidados de audiência pública; vi cargos como "Secretário-Executivo do Ministério da Fazenda" e "Advogado, representante de [...]", e alguns parecem não ser parlamentares nem agentes públicos. **CPF, CNPJ, e-mail e telefone: 0 de 670.** O texto dos informes não foi lido por inteiro.
- **`documentosAssociados[].autoria`** repete o nome e o partido do autor dos 2.750 documentos; `autoria[]` do processo (não lida a fundo) traz `codigoParlamentar` e `autor` (61 autores na PEC 1/2026). São os mesmos dados públicos que `senado.md` já mapeia para o ADR 0005; **não avaliei** se entram na allowlist.

## Comparação com a Câmara (só o que foi medido)

| | Câmara (ADR 0034, 0035) | Senado (esta medição) |
|---|---|---|
| Canal | arquivo CSV anual (38,5 MB), 1 requisição | detalhe por processo, **1 requisição por processo** (3,5 h a 10,7 h em série) |
| Volume em 2026 | 118.684 tramitações, 46.295 proposições | estimativa ≈ 16 mil informes (5,4 a 28,4 mil), 12.871 processos |
| Itens por proposição/processo | mediana 2, máx 98 | mediana 6 distintos (aleatória), máx 207 (dirigida) |
| Chave | (proposição, `sequencia`, `dataHora`, `siglaOrgao`, `descricaoTramitacao`) | `id` do informe (inteiro), sem `sequencia` |
| Duplicatas | 40 linhas (0,03%) | 646 de 1.316 (49%), todas idênticas |
| Data e hora | `dataHora`, fuso não declarado | `aaaa-mm-dd hh:mm:ss`, fuso não declarado |
| Hora `00:00` | 28,2% | 0,45% em 2026 (1 de 220); legado `00:00:0N` em processos antigos |
| Texto | `descricaoTramitacao` curta + `despacho` longo (3.426) | um só `descricao` (até 4.176) |
| Órgão | `siglaOrgao` (74 valores) | `colegiado.sigla` (17 na amostra; vazio em 70 de 670) e `enteAdministrativo.sigla` (22) |

## Perguntas para o dono

Nenhuma é decisão tomada; cada uma muda o modelo.

1. **O que é "tramitação" no Senado?** Só `informesLegislativos` (o texto com data e hora, a que mais se parece com a da Câmara), ou também as `movimentacoes` (envio e recebimento entre órgãos, sem texto) e as `situacoes` (estado com início e fim, só data)? São três listas no mesmo detalhe, com chaves e horas diferentes.
2. **Coleta por detalhe, sem arquivo em massa.** O padrão dos ADR 0031, 0033 e 0034 é um arquivo CSV por conjunto. Aqui é uma requisição por processo (3,5 h para os 4.175 de 2026, 10,7 h para os 12.871), com 3 s de pausa. Aceita essa forma de coleta (e, no dia a dia, buscar só o `numdias`)? O que entra primeiro: **só os apresentados em 2026**, ou todos os que tramitam (inclui informes com data em 2026 de processos mais antigos)?
3. **Recorte "2026".** Pela data do informe (como a Câmara, que é pela `dataHora`) ou pelo processo apresentado em 2026? Os dois divergem: processos de 2025 e 2024 têm informes de 2026 (PL 2234/2024: 24 de 24).
4. **O texto `descricao` entra?** Sem ele o informe fica só com data, `colegiado`, `enteAdministrativo` e `siglaSituacaoIniciada` (37%). Com ele, entram nomes de senadores (324 de 670) e de convidados de audiência (nome e cargo; alguns cargos sugerem particulares). A decisão do dono para o `despacho` da Câmara foi não ingerir (ADR 0034, decisão 2); vale a mesma regra aqui, ou só o texto de certos tipos?
5. **Hora.** Pelo ADR 0035, emenda 1, a página da Câmara mostra só a data quando a hora é 00:00. No Senado em 2026 o caso é raro (1 de 220); a regra vale também para o Senado (e vale para `00:00:01`, `00:00:02`, que aparecem em informes antigos, ou só para `00:00:00`)? Ou o Senado mostra sempre a hora?
6. **Duplicatas exatas (49%).** A chave "(processo, `id` do informe), cópia exata vale uma linha" serve, como as 38 duplicatas da Câmara? Ou o dono quer ver o motivo antes?
7. **Anos anteriores.** Processos com informes só em anos anteriores ficam de fora do "2026" (PL 2338/2023, por exemplo, tem 126 informes distintos e nenhum de 2026)? A página do Senado diria "tramitação em 2026" como a da Câmara?

## Não verificado

- **Fuso** de todos os campos de data e hora (nenhum traz deslocamento; só indício de horário local).
- **Significado de `00:00:01`..`00:00:05` e de `00:10:00`** (os 6 `2022-12-21 00:10:00`, que parecem carga em lote): é inferência.
- **Por que 49% dos informes vêm duplicados** e se isso depende do tipo, do tamanho do processo ou do dia.
- **Estabilidade ao longo do tempo:** se o `id` do informe, a ordem e o conteúdo mudam entre duas coletas (uma carga só); se a fonte reclassifica (como `senado.md` viu nos votos).
- **Estimativa de volume** com 24 processos aleatórios (n = 8 para os apresentados em 2026), cauda pesada (um processo tem 207 informes); informes com data em 2026 de processos fora da união não foram contados.
- **Semântica do `numdias`** (a janela de 1 dia incluiu 3 dias) e se `dataUltimaAtualizacao` muda quando só um informe novo é acrescentado.
- **Processo com mais de 1 autuação:** nos 46 (inclui 2 MPV, 1 PLN e 1 PRS) todos têm 1; outros tipos e casos não foram vistos.
- **Texto dos informes** lido só por contagens por padrão (regex) e por amostra de formas; não li os 670, e a presença de dados pessoais além de nomes não está descartada.
- **XML e NDJSON** do detalhe; o parâmetro `v` (versão do serviço); o comportamento de 429 e 503 (nunca ocorreram).
- **404 para um processo retirado** (medi só um id que nunca existiu).
- **ADR 0005** (allowlist para este campo), **P-16** (licença e uso comercial do Senado, ainda "não dito").
- **Código do polis:** só li `apps/sources/http_client.py:84` (o `USER_AGENT`). O que a normalização, o leitor CSV ou o `PlainCsvReader` fariam com este formato **não foi lido por aqui**; o que digo do ADR 0034 e 0035 vem do texto dos ADRs, não do código.

## Comandos

Tudo roda fora do repo, com os dados em um diretório `$D` (aqui, o scratchpad da sessão). Antes de cada requisição, `sleep 3`; `UA='polis-coletor (+https://github.com/masterlxz/polis)'`; `B=https://legis.senado.leg.br/dadosabertos`.

**Downloads (2026-11-28, 13:58Z a 14:07Z, 55 requisições):**

```bash
D=/caminho/sen; mkdir -p $D/dirigida $D/aleatoria; cd $D
UA='polis-coletor (+https://github.com/masterlxz/polis)'; B=https://legis.senado.leg.br/dadosabertos
curl -sS -A "$UA" -o apidocs.json -w '%{http_code} %{size_download}\n' $B/v3/api-docs                       # 200, 215.797 B, 157 caminhos, 42 deprecated, versão 4.1.3.120
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o lista2026.json "$B/processo?dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28"   # 4.175 itens
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o tramitando.json "$B/processo?tramitando=S"      # 10.951 itens
sleep 3; curl -sS -A "$UA" -o geracsv.csv https://www12.senado.leg.br/dados-abertos/geracsv                 # catálogo
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o numdias1.json "$B/processo?numdias=1"           # 328
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o numdias7.json "$B/processo?numdias=7"           # 1.110
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -w '%{http_code} %{size_download}\n' "$B/processo/1"  # 404, 72 B
# duas buscas para achar os ids de PL 2338/2023 e PLP 68/2024
for q in "sigla=PL&numero=2338&ano=2023" "sigla=PLP&numero=68&ano=2024"; do sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' "$B/processo?$q"; done
# amostra dirigida (22 detalhes); os 22 ids estao na tabela "Dirigida"
for id in 8986903 9055580 8986931 9063446 8987995 9070516 8984726 9069218 8984112 9053761 8985534 8984232 9024204 8984950 8984209 8998698 8986924 8441243 8701679 8985559 8988413 8989972; do
  sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o dirigida/p$id.json -w "$id %{http_code} %{size_download} %{time_total}\n" "$B/processo/$id"; done
# amostra aleatória (24 detalhes; os ids saem do script G)
for id in $(cat aleatoria/ids.txt); do
  sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o aleatoria/p$id.json -w "$id %{http_code} %{size_download} %{time_total}\n" "$B/processo/$id"; done
```

(Os 3 últimos da dirigida, PDL 261/2025, PL 168/2026 e PL 2234/2024, vieram de processos com atualização na véspera, escolhidos da lista de 2026 por `dataSituacaoAtual >= 2026-11-27`.) Contagem das 55 requisições: especificação 1, lista de 2026 1, `tramitando=S` 1, catálogo 1, `numdias` 2, id inexistente 1, duas buscas 2, dirigida 22, aleatória 24.

**Como ler a especificação e o catálogo** (a segunda e a terceira linhas da seção "Onde estão"):

```bash
python3 -I - <<'EOF'
import json,re
d=json.load(open("apidocs.json")); print(d["info"].get("version"),len(d["paths"]),sum(v["get"].get("deprecated",False) for v in d["paths"].values()))
pat=re.compile(r"informe|andamento|tramita|movimenta|despacho",re.I)
for p,v in d["paths"].items():
    g=v["get"]
    if pat.search(g.get("summary","")+" "+g.get("description","")+" "+p): print(p,"DEPRECIADO" if g.get("deprecated") else "",g.get("summary"))
EOF
python3 -I - <<'EOF'
import csv,io
rows=list(csv.DictReader(io.StringIO(open("geracsv.csv",encoding="utf-8-sig").read()),delimiter=";"))
for r in rows:
    if r["nom_conjunto_dados"] in ("Tramitações da Matéria Legislativa","Atualizações da Matéria Legislativa"): print(r["nom_conjunto_dados"],"|",r["txt_url"],"|",r["des_frequencia_atualizacao"])
EOF
```

Os scripts abaixo vêm todos depois deste mesmo prelúdio: `cat prelude.py <script>.py | python3 -I -` com `D` exportado (o `-I` impede que o diretório de dados carregue código; o `D` é lido pelo prelúdio).

**`prelude.py`:**

```python
import collections, glob, json, os, random, re, statistics

D = os.environ["D"]


def carrega(sub):
    return [json.load(open(f)) for f in sorted(glob.glob(f"{D}/{sub}/p*.json"))]


def informes(d):
    """Informes brutos (como vieram) de todas as autuações de um processo."""
    return [x for a in d["autuacoes"] for x in a.get("informesLegislativos", [])]


def distintos(d):
    """Informes sem as cópias exatas: um por `id` dentro do processo."""
    return list({x["id"]: x for x in informes(d)}.values())


dirigida = carrega("dirigida")
aleatoria = carrega("aleatoria")
todos = dirigida + aleatoria
```

**Script A, contagens por processo (tabelas "Amostra"):**

```python
def linha(d, arq):
    a = d["autuacoes"]
    return dict(
        ident=d["identificacao"], id=d["id"], bytes=os.path.getsize(arq),
        autuacoes=len(a), informes=len(informes(d)), distintos=len(distintos(d)),
        mov=sum(len(u.get("movimentacoes", [])) for u in a),
        sit=sum(len(u.get("situacoes", [])) for u in a),
        desp=len(d.get("despachos", [])),
    )


for nome in ("dirigida", "aleatoria"):
    arqs = sorted(glob.glob(f"{D}/{nome}/p*.json"))
    rows = [linha(json.load(open(f)), f) for f in arqs]
    print("##", nome, len(rows), "processos")
    for r in rows:
        print(r["ident"], r["id"], r["bytes"], r["autuacoes"], r["informes"], r["distintos"], r["mov"], r["sit"], r["desp"], sep=" | ")
    for k in ("bytes", "informes", "distintos", "mov", "sit"):
        v = sorted(r[k] for r in rows)
        print(f"{k}: min {v[0]} mediana {statistics.median(v)} media {statistics.mean(v):.1f} max {v[-1]}")
```

Saída (resumo; as linhas por processo estão nas tabelas acima): dirigida `bytes: min 3228 mediana 18171.0 media 88579.7 max 978415`, `informes: min 0 mediana 12.0 media 46.0 max 375`, `distintos: min 0 mediana 10.5 media 23.7 max 207`, `mov: min 0 mediana 3.5 media 6.3 max 30`; aleatória `bytes: min 2632 mediana 9068.0 media 12418.6 max 94208`, `informes: min 0 mediana 6.0 media 12.6 max 160`, `distintos: min 0 mediana 6.0 media 6.2 max 25`, `mov: min 0 mediana 2.0 media 2.1 max 10`, `sit: min 1 mediana 3.0 media 3.9 max 12`.

**Script B, formato, cópias, chave e ordem:**

```python
def forma(s):
    return re.sub(r"\d", "9", s) if isinstance(s, str) else repr(s)


bru = [(d["id"], x) for d in todos for x in informes(d)]
dis = {(p, x["id"]): x for p, x in bru}
print("processos", len(todos), "| informes brutos", len(bru), "| distintos por (processo, id)", len(dis))

# tipos das chaves de um informe e de uma movimentacao
for rot, itens in (
    ("informe", [x for _, x in bru]),
    ("movimentacao", [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]),
    ("situacao", [s for d in todos for a in d["autuacoes"] for s in a.get("situacoes", [])]),
):
    c, t = collections.Counter(), collections.defaultdict(collections.Counter)
    for it in itens:
        for k, v in it.items():
            c[k] += 1
            t[k][type(v).__name__] += 1
    print("##", rot, "n =", len(itens))
    for k in c:
        print(f"  {k}: {c[k]} {dict(t[k])}")

# formato dos campos de data/hora
inf = [x for _, x in bru]
mov = [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print("informe.data:", collections.Counter(forma(x["data"]) for x in inf))
print("mov.dataEnvio:", collections.Counter(forma(m["dataEnvio"]) for m in mov), "| dataRecebimento:", collections.Counter(forma(m["dataRecebimento"]) for m in mov))
print("dthUltimaAtualizacao:", collections.Counter(forma(d.get("dthUltimaAtualizacao")) for d in todos))

# copias exatas
por_proc = collections.defaultdict(list)
for p, x in bru:
    por_proc[(p, x["id"])].append(x)
extra = sum(len(v) - 1 for v in por_proc.values())
identicas = sum(1 for v in por_proc.values() for y in v[1:] if y == v[0])
print("copias extras do mesmo id no mesmo processo:", extra, "| identicas ao primeiro (dict inteiro):", identicas)
print("processos com alguma copia extra:", len({p for (p, i), v in por_proc.items() if len(v) > 1}), "de", len({p for p, _ in bru}), "com informes")

# mesmo id de informe em processos diferentes?
procs_por_id = collections.defaultdict(set)
for p, i in dis:
    procs_por_id[i].add(p)
print("ids de informe que aparecem em mais de um processo:", sum(1 for s in procs_por_id.values() if len(s) > 1))
mids = [m["id"] for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print("movimentacoes: ids", len(mids), "distintos", len(set(mids)), "| ids em comum com informes:", len(set(mids) & {i for _, i in dis}))

# ordem em que a fonte entrega
cresc = sum(1 for d in todos if informes(d) and [x["data"] for x in informes(d)] == sorted(x["data"] for x in informes(d)))
print("processos com informes: ", sum(1 for d in todos if informes(d)), "| em ordem crescente de `data`:", cresc)
emp = sum(1 for d in todos if len({x["data"] for x in distintos(d)}) < len(distintos(d)))
print("processos com 2+ informes distintos na MESMA data-hora:", emp)
print("autuacoes por processo:", collections.Counter(len(d["autuacoes"]) for d in todos))
print("colegiado vazio {}:", sum(1 for x in dis.values() if not x["colegiado"]), "de", len(dis))
```

Saída (as linhas que sustentam o texto): `processos 46 | informes brutos 1316 | distintos por (processo, id) 670`; `informe.data: {'9999-99-99 99:99:99': 1316}`; `mov.dataEnvio: {'9999-99-99 99:99:99': 188} | dataRecebimento: {'9999-99-99 99:99:99': 181, 'None': 7}`; `dthUltimaAtualizacao: {'9999-99-99T99:99:99.999999': 32, 'None': 14}`; `copias extras ...: 646 | identicas ao primeiro (dict inteiro): 646`; `processos com alguma copia extra: 10 de 42 com informes`; `ids de informe que aparecem em mais de um processo: 0`; `movimentacoes: ids 188 distintos 188 | ids em comum com informes: 0`; `processos com informes: 42 | em ordem crescente de data: 42`; `processos com 2+ informes distintos na MESMA data-hora: 0`; `autuacoes por processo: {1: 46}`; `colegiado vazio {}: 70 de 670`.

**Script C, hora 00:00:**

```python
dis = {(d["id"], x["id"]): x for d in todos for x in informes(d)}
U = list(dis.values())
print("informes distintos:", len(U))
print("hora exatamente 00:00:00:", sum(1 for x in U if x["data"][11:] == "00:00:00"))
print("hora 00:00:xx (qualquer segundo):", sum(1 for x in U if x["data"][11:16] == "00:00"))
print("hora 00:10:00:", sum(1 for x in U if x["data"][11:] == "00:10:00"))
print(f"esperado por acaso, 1 minuto em 1440: {100/1440:.3f}%")

# por ano da `data`: [total, 00:00:xx, 00:10:00]
por_ano = collections.defaultdict(lambda: [0, 0, 0])
for x in U:
    a = por_ano[x["data"][:4]]
    a[0] += 1
    a[1] += x["data"][11:16] == "00:00"
    a[2] += x["data"][11:] == "00:10:00"
for ano, v in sorted(por_ano.items()):
    print(ano, v)

# so 2026
r26 = [x for x in U if x["data"].startswith("2026")]
print("2026: n", len(r26), "| 00:00:00:", sum(1 for x in r26 if x["data"][11:] == "00:00:00"),
      "| 00:00:xx:", sum(1 for x in r26 if x["data"][11:16] == "00:00"))
print("anos < 2020, segundos dos 00:00:xx:", sorted(collections.Counter(x["data"][17:] for x in U if x["data"][:4] < "2020" and x["data"][11:16] == "00:00").items()))
print("2026, hora do dia:", sorted(collections.Counter(int(x["data"][11:13]) for x in r26).items()))

# movimentacoes
mov = [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print("movimentacoes:", len(mov), "| dataEnvio 00:00:00:", sum(1 for m in mov if m["dataEnvio"][11:] == "00:00:00"),
      "| dataRecebimento 00:00:00:", sum(1 for m in mov if (m["dataRecebimento"] or "")[11:] == "00:00:00"))

# o unico 00:00:00 de 2026
for d in todos:
    for x in distintos(d):
        if x["data"].startswith("2026") and x["data"][11:] == "00:00:00":
            print("o caso de 2026:", d["identificacao"], x["data"], repr(x["descricao"][:70]))

com26 = lambda ds: sum(any(x["data"].startswith("2026") for x in distintos(d)) for d in ds)
print("processos com algum informe distinto de 2026:", com26(todos), "de", len(todos), "| dirigida:", com26(dirigida), "| aleatoria:", com26(aleatoria))

h0 = collections.Counter(d["identificacao"] for d in todos for x in distintos(d) if x["data"][11:13] == "00")
print("informes na hora 00, por processo:", h0.most_common(3), "| total:", sum(h0.values()))
```

Saída: `informes distintos: 670`; `hora exatamente 00:00:00: 1`; `hora 00:00:xx: 34`; `hora 00:10:00: 6`; por ano `[total, 00:00:xx, 00:10:00]`: 2009 `[16, 16, 0]`, 2011 `[1, 1, 0]`, 2012 `[2, 2, 0]`, 2013 `[1, 1, 0]`, 2014 `[2, 2, 0]`, 2019 `[20, 9, 0]`, 2020 `[4, 0, 0]`, 2021 `[8, 0, 0]`, 2022 `[9, 0, 6]`, 2023 `[35, 2, 0]`, 2024 `[328, 0, 0]`, 2025 `[24, 0, 0]`, 2026 `[220, 1, 0]`; `2026: n 220 | 00:00:00: 1 | 00:00:xx: 1`; `anos < 2020, segundos dos 00:00:xx: [('01', 19), ('02', 8), ('03', 2), ('04', 1), ('05', 1)]`; hora do dia em 2026: `[(0, 1), (7, 4), (8, 22), (9, 15), (10, 18), (11, 24), (12, 16), (13, 13), (14, 19), (15, 22), (16, 16), (17, 15), (18, 19), (19, 9), (20, 6), (21, 1)]`; `movimentacoes: 188 | dataEnvio 00:00:00: 0 | dataRecebimento 00:00:00: 0`; `o caso de 2026: VET 51/2025 2026-03-04 00:00:00`; `processos com algum informe distinto de 2026: 27 de 46 | dirigida: 20 | aleatoria: 7`; `informes na hora 00, por processo: [('VET 36/2009', 23), ('PL 5956/2019', 6), ('PL 5987/2019', 5)] | total: 40`.

**Script D, texto livre e dados pessoais:**

```python
U = [x for d in todos for x in distintos(d)]
L = [x["descricao"] for x in U]
print("descricoes distintas:", len(L), "| vazias:", sum(1 for s in L if not s.strip()))
ln = sorted(len(s) for s in L)
print("tamanho min/mediana/p99/max:", ln[0], statistics.median(ln), ln[int(0.99 * len(ln)) - 1], ln[-1])
print("com \\r\\n:", sum("\r\n" in s for s in L), "| com \\n sem \\r:", sum("\n" in s and "\r" not in s for s in L),
      "| com \\r sem \\n:", sum("\r" in s and "\n" not in s for s in L), "| com \\t:", sum("\t" in s for s in L))
print("controle alem de \\t \\n \\r:", sum(bool(re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", s)) for s in L))
print("espaco no comeco ou no fim:", sum(s != s.strip() for s in L))

# dado pessoal no texto (regex = estimativa por baixo/por cima, nao leitura)
pad = {
    "Senador/Senadora": r"\b[Ss]enador(a)?\b", "Deputado/Deputada": r"\b[Dd]eputad[oa]\b", "Relator/Relatora": r"\b[Rr]elator(a)?\b",
    "Ministro/Ministra": r"\bMinistr[oa]\b", "Sr./Sra./Dr./Dra.": r"\b(Sr|Sra|Dr|Dra)\.", "nome (PARTIDO/UF)": r"\([A-Za-z\-]{2,12}/[A-Z]{2}\)",
    "CPF": r"\d{3}\.\d{3}\.\d{3}-\d{2}", "CNPJ": r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", "e-mail": r"[\w.\-]+@[\w\-]+\.[\w.\-]+", "telefone": r"\(?\d{2}\)?\s?9?\d{4}-\d{4}",
}
for k, p in pad.items():
    print(f"{k}: {sum(bool(re.search(p, s)) for s in L)} de {len(L)}")

# convidados de audiencia: trechos "Sr. <nome>, <cargo>" (so a forma do trecho, sem nomes)
tr = [m.group(0) for s in L for m in re.finditer(r"\b(Sr|Sra)\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^,;.]{2,60},\s*[^,;.]{3,60}", s)]
print("trechos 'Sr./Sra. Nome, cargo':", len(tr), "| forma de um deles, nome omitido:", re.sub(r"^(Sr|Sra)\.\s+[^,]+", r"\1. <nome>", tr[0]))

da = [y for x in U for y in x.get("documentosAssociados", [])]
print("documentosAssociados:", len(da), "| chaves:", sorted({k for y in da for k in y}), "| com `autoria`:", sum(1 for y in da if y.get("autoria")))
```

Saída: `descricoes distintas: 670 | vazias: 0`; `tamanho min/mediana/p99/max: 12 137.0 2125 4176`; `com \r\n: 169 | com \n sem \r: 43 | com \r sem \n: 0 | com \t: 1`; `controle alem de \t \n \r: 0`; `espaco no comeco ou no fim: 19`; Senador/Senadora 324, Deputado/Deputada 12, Relator/Relatora 87, Ministro/Ministra 11, Sr./Sra./Dr./Dra. 36, nome (PARTIDO/UF) 7, CPF 0, CNPJ 0, e-mail 0, telefone 0 (todos "de 670"); `trechos 'Sr./Sra. Nome, cargo': 145`; `documentosAssociados: 2750 | chaves: ['autoria', 'data', 'descricao', 'id', 'identificacao', 'siglaTipo', 'tipo', 'url'] | com autoria: 2750`. O "36" de "Sr./Sra./Dr./Dra." inclui o "Dr." usado antes do nome de senadores; os 145 trechos "Sr./Sra. Nome, cargo" vêm do padrão mais estreito.

**Script E, universo, estimativa e incremental:**

```python
apres26 = {x["id"] for x in json.load(open(f"{D}/lista2026.json"))}
tramit = {x["id"] for x in json.load(open(f"{D}/tramitando.json"))}
uniao = apres26 | tramit
print("apresentados em 2026:", len(apres26), "| tramitando:", len(tramit), "| interseccao:", len(apres26 & tramit), "| uniao:", len(uniao))

d26 = [sum(x["data"].startswith("2026") for x in distintos(d)) for d in aleatoria]
em26 = [d["id"] in apres26 for d in aleatoria]
print("amostra aleatoria: n", len(d26), "| apresentados em 2026:", sum(em26), "| informes distintos com data em 2026 (soma):", sum(d26))
print("por processo (d26):", sorted(d26))
m = statistics.mean(d26)
print(f"media {m:.2f} mediana {statistics.median(d26)} max {max(d26)} -> x uniao = {m * len(uniao):.0f}")
random.seed(7)
bs = sorted(statistics.mean(random.choices(d26, k=len(d26))) * len(uniao) for _ in range(5000))
print(f"bootstrap (5000, semente 7) 2,5% = {bs[125]:.0f}  97,5% = {bs[4874]:.0f}")
e = [v for v, f in zip(d26, em26) if f]
o = [v for v, f in zip(d26, em26) if not f]
print(f"estrato apresentados em 2026: n {len(e)} media {statistics.mean(e):.2f} x {len(apres26)} = {statistics.mean(e) * len(apres26):.0f}")
print(f"estrato anteriores a 2026 (tramitando): n {len(o)} media {statistics.mean(o):.2f} x {len(uniao) - len(apres26)} = {statistics.mean(o) * (len(uniao) - len(apres26)):.0f}")

tam = [os.path.getsize(f) for f in glob.glob(f"{D}/aleatoria/p*.json")]
print(f"bytes por detalhe (aleatoria): mediana {statistics.median(tam):.0f} media {statistics.mean(tam):.0f} -> x uniao = {statistics.mean(tam) * len(uniao) / 1e6:.0f} MB; x apres26 = {statistics.mean(tam) * len(apres26) / 1e6:.0f} MB")
for n, rotulo in ((len(uniao), "uniao"), (len(apres26), "apresentados em 2026")):
    print(f"carga em serie, 1 detalhe a cada 3 s, {rotulo}: {n} req = {n * 3 / 3600:.1f} h (so a pausa)")

# incremental pelo filtro numdias
for n in (1, 7):
    v = json.load(open(f"{D}/numdias{n}.json"))
    ts = sorted(x["dataUltimaAtualizacao"] for x in v)
    print(f"numdias={n}: {len(v)} processos; dataUltimaAtualizacao de {ts[0]} a {ts[-1]}; {len(v) * 3 / 60:.0f} min de pausas para buscar todos os detalhes")
```

Saída: `apresentados em 2026: 4175 | tramitando: 10951 | interseccao: 2255 | uniao: 12871`; `amostra aleatoria: n 24 | apresentados em 2026: 8 | informes distintos com data em 2026 (soma): 30`; `por processo (d26): [0 x17, 2, 2, 3, 4, 6, 6, 7]`; `media 1.25 mediana 0.0 max 7 -> x uniao = 16089`; `bootstrap (5000, semente 7) 2,5% = 5363  97,5% = 28423`; `estrato apresentados em 2026: n 8 media 2.38 x 4175 = 9916`; `estrato anteriores a 2026 (tramitando): n 16 media 0.69 x 8696 = 5978`; `bytes por detalhe (aleatoria): mediana 9068 media 12419 -> x uniao = 160 MB; x apres26 = 52 MB`; `uniao: 12871 req = 10.7 h`; `apresentados em 2026: 4175 req = 3.5 h`; `numdias=1: 328 processos; dataUltimaAtualizacao de 2026-11-25T17:37:06.897 a 2026-11-27T18:54:29.011; 16 min`; `numdias=7: 1110 processos; ... de 2026-11-21T11:16:57.091 a 2026-11-27T18:54:29.011; 56 min`.

**Script F, campos controlados e chaves de topo:**

```python
U = [x for d in todos for x in distintos(d)]
print("informes distintos:", len(U))
print("com siglaSituacaoIniciada:", sum("siglaSituacaoIniciada" in x for x in U), "| valores distintos:", len({x["siglaSituacaoIniciada"] for x in U if "siglaSituacaoIniciada" in x}))
print("colegiado.sigla distintas:", len({x["colegiado"].get("sigla") for x in U}), "| colegiado vazio:", sum(not x["colegiado"] for x in U))
print("enteAdministrativo.sigla distintas:", len({x["enteAdministrativo"]["sigla"] for x in U}))
print("com documentosAssociados:", sum(bool(x.get("documentosAssociados")) for x in U))
print("chaves de um informe, na ordem em que vieram:", list(U[0].keys()))
print("tamanho de `descricao` (caracteres), maximo:", max(len(x["descricao"]) for x in U))
print("ids de informe: min", min(x["id"] for x in U), "max", max(x["id"] for x in U))
print("processos:", len(todos), "| chaves de topo (uniao):", len({k for d in todos for k in d}), "| chaves de topo (todos tem):", sorted(set.intersection(*[set(d) for d in todos])))
```

Saída: `com siglaSituacaoIniciada: 248 | valores distintos: 34`; `colegiado.sigla distintas: 17 | colegiado vazio: 70` (o 17 conta o valor ausente como um valor); `enteAdministrativo.sigla distintas: 22`; `com documentosAssociados: 364`; `ids de informe: min 93334 max 2333088`; `chaves de topo (uniao): 42`.

**Script G, sorteio da amostra aleatória:**

```python
apres26 = {x["id"] for x in json.load(open(f"{D}/lista2026.json"))}
tramit = {x["id"] for x in json.load(open(f"{D}/tramitando.json"))}
random.seed(20261128)
ids = random.sample(sorted(apres26 | tramit), 24)
print(*ids)
```

Saída (grave em `aleatoria/ids.txt`, um id por linha, antes do download): `8861962 7897075 9106496 9135954 7834921 3335633 9048998 8756412 8747042 8696463 8992806 9082795 7748539 8380185 9112008 8694974 7835670 9052244 8932012 8239329 8908708 8494730 8696986 9095406`.
