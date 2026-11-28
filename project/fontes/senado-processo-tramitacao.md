# Senado: tramitações do processo legislativo (medição de 2026-11-28)

Complementa [senado.md](senado.md) (que já mede `/processo` e `/votacao`; nada daquilo foi refeito) e serve de base para a fatia de tramitações do Senado, no papel que a "Rodada 5" de [camara.md](camara.md) teve para o ADR 0034. **Nada foi integrado e nada aqui decide o modelo**: relata o medido e levanta perguntas para o dono (última seção). Outras duas medições do mesmo dia, em PRs abertos, cobrem a lista `/processo` e os ids (#371, `senado-processo-ids.md`) e as regras de rede e de carga do código (#370, `senado-processo-regras.md`); este arquivo as cita e não as refaz.

Rótulos: **medido** (com o comando, na seção "Comandos", e a saída) ou **documentado** (com a fonte). Datas e horas desta medição em UTC.

**Como foi medido, e uma ressalva de fidelidade.** De uma máquina, **55 requisições** de **2026-11-28T13:58Z a 14:07Z**, com `User-Agent: polis-coletor (+https://github.com/masterlxz/polis)` (a constante `USER_AGENT` em `apps/sources/http_client.py:84`, lida) e `sleep 3` entre as requisições **desta** medição. **A medição do #371 (13:58 a 14:02Z) correu ao mesmo tempo, com o mesmo `User-Agent`**; se as duas saíram do mesmo IP, a taxa combinada passou do "em série, 3 s" do ADR 0008, decisão 5 (não sei se foi o mesmo IP). Por isso não afirmo "uma só máquina, em série" para o conjunto.

**O que ficou registrado sobre erros e cabeçalhos.** O código HTTP e o tempo foram impressos na sessão (`-w`) para todas as requisições, mas só **gravados em arquivo** para os 42 detalhes da amostra (`fetch1.log` e `fetch2.log`); para a lista, as buscas, o catálogo, o `numdias` e o 404, o código ficou só na saída da sessão. Nessa saída não apareceu 429, 503 nem 403, mas **não há registro durável** além dos logs dos detalhes. Os cabeçalhos foram gravados (`-D`) em **5 respostas** (a lista de 2026, o PEC 1/2026 e os 3 detalhes de 2026-11-27): `Cache-Control`, `Age` e a ausência de `Retry-After` e `RateLimit` (`grep -ic 'retry-after\|ratelimit'` deu 0 nas 5) valem **só para elas**, e o laço de downloads da seção "Comandos" **não grava `-D`**: essas afirmações não são reproduzíveis pelos comandos como estão escritos (acrescente `-D arquivo.hdr`). Versão da API na especificação de hoje: `4.1.3.120` (a de `senado.md` era `4.1.3.113`; 157 caminhos e 42 depreciados, como antes).

## Resumo

1. **As tramitações estão só no detalhe `GET /processo/{id}`**, dentro de `autuacoes[]` (sempre 1 autuação nos 46 processos medidos). **Não encontrei** arquivo nem endpoint em massa de informes por período: varri localmente os 157 resumos da especificação e as 467 entradas do catálogo (script I) e nenhum candidato devolve os informes de todos os processos; não chamei nenhum dos endpoints depreciados. Uma carga é **uma requisição por processo**.
2. **O que o Senado chama de tramitação tem três formas** no mesmo detalhe: `informesLegislativos` (texto livre com data e hora, a mais parecida com a tramitação da Câmara), `movimentacoes` (envio e recebimento entre órgãos, sem texto) e `situacoes` (estado com início e fim, só data). Ver "Formato".
3. **`informesLegislativos` vem com cópias exatas**: nos 46 processos, 10 de 42 com informes têm cópia, e 1.316 itens brutos viram 670 distintos por `id`. **O "49%" é dominado por poucos processos e mistura as duas amostras:** na aleatória, 151 das 155 cópias extras são de 1 processo (PDL 470/2023); na dirigida, 4 processos somam 480 das 491. O `id` do informe é inteiro e, **nos 46**, único por processo e nunca repetido entre processos. **Nos 46 não há campo de sequência**, e os itens vêm em ordem crescente de `data`.
4. **Volume:** mediana de 6 informes distintos por processo (amostra aleatória, n = 24, histórico completo do processo), detalhe de 2,6 KB a 94 KB (mediana 9 KB), mas o pior caso medido foi 978 KB (208 informes). Estimativa de informes com data em 2026: cerca de **16 mil**, com **percentis 2,5-97,5 do bootstrap de 5,4 mil a 28,4 mil sobre n = 24 (17 zeros, 7 positivos, máx 7); tende a subestimar a cauda, e o sorteio não pegou PEC, PLP nem MPV**. Isso compara só `informesLegislativos` com a tramitação inteira da Câmara (118.684); as outras duas listas (188 movimentações e 269 situações nos 46 processos) ficam fora da conta. Uma carga completa por detalhe leva **3,5 h** (os 4.175 processos apresentados em 2026) a **10,7 h** (os 12.871 que tramitam ou foram apresentados em 2026) só de pausas de 3 s; a coleta só dos processos citados pelas votações seria de **cerca de 4 min** (71 ids, #371). O filtro `numdias` de `/processo` existe e devolve `dataUltimaAtualizacao`, mas **não se sabe se ela muda quando entra um informe novo**.
5. **Hora 00:00:** em 2026, **1 de 220** informes distintos tem hora exatamente `00:00:00` (IC 95% exato de 0,012% a 2,51%; 0 de 30 na amostra aleatória, limite superior unilateral de 9,5%), contra 28,2% das tramitações da Câmara (ADR 0035, emenda 1) e ~0,07% por acaso. **O que a amostra permite dizer é que o fenômeno de 28% não aparece nesta amostra**, não que o Senado não tenha o padrão: 190 dos 220 vêm da amostra dirigida, e os informes de um mesmo processo não são independentes. Os `00:00:01` a `00:00:05` existem, concentrados em 3 processos antigos (34 dos 40 informes da hora 00).
6. **O texto livre é um só campo (`descricao`)**, sem equivalente separado de `despacho`; 324 de 670 mencionam senadores, e há convidados de audiência com nome e cargo (alguns cargos sugerem particulares). Nenhum CPF, CNPJ, e-mail ou telefone **em padrão formatado** (e nenhuma sequência de 11 dígitos) nos 670 textos. A allowlist do Senado no ADR 0005 não lista `descricao`, `autoria` nem `documentosAssociados`; pela decisão 1, ficam fora por padrão.
7. **O `_text` do código da Câmara recusaria 208 das 670 descrições (31%)** por terem quebra de linha no meio (`apps/legislature/parsing.py:51`); e o `_DATE_TIME` da Câmara exige `T` entre data e hora, enquanto o Senado usa espaço. Ver "Texto livre".

## Onde estão as tramitações (medido e documentado)

- **Documentado (especificação, `GET /v3/api-docs`):** o `GET /dadosabertos/processo/{id}` é "Detalhes de um Processo Legislativo" ("identificação, ementa, [...] autoria, [...] decisão, destino, norma gerada, entre outros"); a descrição não cita tramitação nem informes. **Medido na especificação: `/processo/{id}` não está depreciado** (`deprecated` falso, script I). O esquema da resposta é uma referência externa (`schemas/processo.yml#/components/schemas/Processo`) que **não vem dentro do arquivo**, então os campos abaixo foram descritos **a partir do dado**, não da documentação.
- **Documentado (catálogo `geracsv`, 2026-11-28):** há dois conjuntos chamados "Tramitações da Matéria Legislativa" e "Atualizações da Matéria Legislativa", ambos com `txt_url` apontando para o Swagger de `Processo/detalhesProcesso`, frequência "Diário". O próprio catálogo manda ler a tramitação do detalhe.
- **Sem listagem em massa (medido localmente, nos resumos e descrições da especificação e no catálogo inteiro; script I):** com um padrão amplo (`informe`, `andamento`, `tramita`, `movimenta`, `despacho`, `atualiza`, `situa[cç]`, `hist[oó]ric`, `evento`, `decis`), **25 dos 157 caminhos casam**. Os que importam: ativos, `/processo` (a lista), `/processo/{id}`, `/processo/prazo`, `/processo/entes`, `/processo/tipos-situacao|tipos-decisao|tipos-atualizacao`, `/materia/vetos/{encerrados,aposrcn,antesrcn}` e `/materia/lista/tramitacao` (total por tipo ou colegiado); depreciados, `/materia/movimentacoes/{codigo}`, `/materia/atualizadas` ("incluídas ou sofreram atualização nos últimos dias"), `/materia/atualizacoes/{codigo}`, `/materia/situacaoatual/*`, `/materia/tramitando`, `/materia/legislaturaatual` e outros. Nenhum devolve os informes de todos os processos por período, **pelo texto do resumo e da descrição**: não abri o esquema de cada um nem chamei nenhum. No catálogo (2.268 linhas, 467 pares conjunto-URL), 48 nomes casam um padrão amplo em nome, descrição ou URL; os que tratam de processo legislativo são os mesmos já listados. Nada novo sobre os depreciados, pelo ADR 0008, decisão 7.
- **As listas `/processo` trazem `dataUltimaAtualizacao` e `ultimaInformacaoAtualizada` só em parte dos itens (medido, script H).** Corrijo uma versão anterior deste arquivo, que dizia que as listas não as traziam (eu havia olhado só o primeiro item): `lista2026.json` tem as duas em **3.906 de 4.175** (93,6%), `tramitando.json` em **5.047 de 10.951** (46,1%), e as listas de `numdias` em 100% (328 de 328 e 1.110 de 1.110). Isso **bate** com o #371, que mediu 3.197 de 3.467 em `?ano=2026` (92,2%) e 8.790 de 28.355 na união das listas dele: são recortes diferentes (por data de apresentação, por `ano` do número, só `tramitando`), mas a chave é **opcional** em todos eles. Consequência para o incremental: a lista completa **não dá** a data de atualização de todo processo (quem não tem a chave não pode ser comparado), e o `numdias` é o caminho que a traz sempre. **Não se sabe se `dataUltimaAtualizacao` muda quando entra um informe novo** (ver "Não verificado").
- **Filtro de atualização (documentado e medido):** `numdias` ("Atualizadas nos últimos N dias. O máximo é 30"). `GET /processo?numdias=1` devolveu 328 processos (289.573 B) e `numdias=7` devolveu 1.110 (1.003.765 B), cada item com `dataUltimaAtualizacao` (`aaaa-mm-ddThh:mm:ss.mmm`, sem fuso). **Medido:** com `numdias=1` os valores vão de 2026-11-25T17:37 a 2026-11-27T18:54, e com `numdias=7` de 2026-11-21T11:16 a 2026-11-27T18:54; a consulta foi em 2026-11-28T14:04Z. Ou seja, "1 dia" cobriu **3 dias de calendário** (25 a 27/11; ~68 h entre o valor mais antigo e a consulta, comparando uma hora sem fuso com UTC), e "7 dias" cobriu 21 a 27/11. Pode haver cache (`s-maxage=1800`, 30 min, nas 5 respostas gravadas), mas 30 min não explica 3 dias; a semântica da janela **não foi verificada**.
- **Inexistente (medido):** `GET /processo/1` devolveu **404** com corpo `{"instance":"/dadosabertos/processo/1","status":404,"title":"Not Found"}` (72 B). É diferente do `/senador/99999999` de `senado.md`, que dava 200 sem dados; um id só, não generalizo.
- **Cache (medido nas 5 respostas com `-D`):** os detalhes saem com `cache-control: max-age=1800, s-maxage=1800` e `Age` (99 s no PEC 1/2026); a lista `/processo?tramitando=S`, com 1800 s (o #371 mediu a mesma lista). **Latência do detalhe:** 0,23 a 0,46 s nos 46 detalhes daqui; o #371 mediu **4,95 s** num detalhe (`/processo/8983497`, "uma amostra; as demais ficaram abaixo de 1,2 s"). Não sei explicar a diferença (rede, hora, cache de borda, tamanho do processo); com n pequeno, **não há latência típica estabelecida**, e o #370 diz que o ritmo do cliente é `max(3 s, latência)` por requisição (citado, `http_client.py:352-358` **não lido por aqui**), então um detalhe lento alongaria a carga. Lista `dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28`: 3.744.740 B em 5,4 s (o #371 mediu 0,57 s para a mesma consulta; a diferença é de 10 vezes e fica sem explicação); `?tramitando=S`: 9.221.974 B em 0,8 s.

## Formato (medido, 46 processos)

Chaves de topo presentes em todos os 46 detalhes: `ano, autuacoes, casaIdentificadora, codigoMateria, comissaoMpv, conteudo, dataInicioEfetivo, deliberacao, descricaoSigla, documento, id, identificacao, identificacaoExterna, normaGerada, numero, sigla, siglaEnteIdentificador, tramitando` (42 chaves no total; as outras variam por tipo). `dthUltimaAtualizacao` (`aaaa-mm-ddThh:mm:ss.uuuuuu`, sem fuso) está em 32 dos 46.

**`autuacoes[]`** (1 por processo nos 46): `numero`, `descricao` ("Autuação Principal"), `codigoColegiadoControleAtual`, `siglaColegiadoControleAtual` e outros campos do colegiado e do ente de controle, `situacoes[]`, `informesLegislativos[]`, `movimentacoes[]` (lido no PEC 1/2026; nos 46, só conferi as três listas). Em REQ de comissão e PET `informesLegislativos` pode faltar ou ser vazio (3 de 24 na amostra aleatória não têm nenhum).

| Lista | Itens (46 processos) | Chaves (tipo) | Data e hora |
|---|---|---|---|
| `informesLegislativos` | 1.316 brutos, 670 distintos | `id` (int), `data` (str), `colegiado` (objeto: `codigo`, `casa`, `sigla`, `nome`; **vazio `{}` em 70 de 670**), `enteAdministrativo` (objeto: `id`, `casa`, `sigla`, `nome`), `descricao` (str), `idSituacaoIniciada` e `siglaSituacaoIniciada` (só em 248 dos 670 distintos), `documentosAssociados` (lista, em 364 dos 670) | `aaaa-mm-dd hh:mm:ss` em 1.316 de 1.316, **sem fuso** |
| `movimentacoes` | 188 | `id` (int, 188 distintos), `dataEnvio`, `enteOrigem`, `dataRecebimento` (**nulo em 7**), `enteDestino`, `colegiadoDestino` (`{}` em 91 de 188; script M) | `aaaa-mm-dd hh:mm:ss`, sem fuso |
| `situacoes` | 269 | `idTipo`, `sigla`, `descricao`, `inicio`, `fim` (ausente em 43), `colegiado`, `enteAdministrativo` | só data `aaaa-mm-dd` |
| `despachos` (topo, fora de `autuacoes`) | 35 | `id`, `data`, `siglaTipoMotivacao`, `tipoMotivacao`, `cancelado` (`Não` nos 35), `encontroLegislativo`, `providencias[]` (38 itens: 33 despachos com 1, 1 com 2 e 1 com 3; chaves `id`, `tipo`, `descricao`, `ordem`, `analiseTempo`, `analiseConteudo`, `reexame`, `unidadesDestinatarias`; rótulos, sem texto livre) | só data (35 de 35; script M) |

Os `id` de informe (93.334 a 2.333.088) e de movimentação nunca coincidem (0 em comum). Um informe de exemplo, **truncado e sem nomes**: `{"id": 2134832, "data": "2023-05-03 19:16:49", "colegiado": {"codigo": 1998, "casa": "SF", "sigla": "PLEN", ...}, "enteAdministrativo": {"id": 55312, "sigla": "SLSF", ...}, "idSituacaoIniciada": 175, "siglaSituacaoIniciada": "AGDESP", "documentosAssociados": [...]}`.

**Dados controlados (medido, 670 informes distintos):** `siglaSituacaoIniciada` tem 34 valores, `colegiado.sigla` 16 (mais o `colegiado` vazio, que é 70 informes) e `enteAdministrativo.sigla` 22. O que o Senado oferece como "descrição curta controlada" é, portanto, o estado iniciado (só em 37% dos informes), e não um tipo de tramitação em todos.

**`documentosAssociados`** (2.750 itens nos 670 informes): `id`, `tipo`, `siglaTipo`, `identificacao`, `descricao`, `data` (`aaaa-mm-ddThh:mm:ss` nos 2.750; script M), `autoria` (texto com o nome e o partido de quem assina, preenchido em 2.750 de 2.750) e `url`.

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
| Processos citados pelas votações do Senado numa janela de 365 dias | 71 ids; só 2026 (pelo ano do número) liga **33 de 90 votações (37%)** | #371 (citado, não refeito) |
| Informes distintos por processo (aleatória) | mediana 6, média 6,2, máx 25 (**histórico completo** do processo) | medido (n = 24) |
| Informes distintos **com `data` em 2026** por processo (aleatória) | 17 processos com 0; 7 com 2, 2, 3, 4, 6, 6 e 7; soma 30; média 1,25 | medido (n = 24) |
| Estimativa de informes com `data` em 2026 nos 12.871 | **≈ 16.089** (percentis 2,5-97,5 do bootstrap de 5.000, semente 7: 5.363 a 28.423) | **estimativa**; n = 24 (17 zeros, 7 positivos, máx 7), tende a subestimar a cauda; o sorteio não pegou PEC/PLP/MPV |
| Estimativa só dos 4.175 apresentados em 2026 | ≈ 9.916 (média 2,38 em **8** processos) | **estimativa**; n = 8 |
| Estimativa dos 8.696 mais antigos que tramitam | ≈ 5.978 (média 0,69 em 16 processos) | **estimativa**; n = 16 |
| Referência: Câmara, 2026 | 118.684 tramitações (a tramitação inteira) | ADR 0034 (documentado no repo, não refeito) |
| Bytes de uma carga completa de detalhes | ≈ 160 MB (12.871 × média de 12.419 B) ou ≈ 52 MB (4.175) | estimativa |
| Requisições em série, 3 s de pausa, só a pausa | **12.871 → 10,7 h; 4.175 → 3,5 h; 71 (só os citados por votações) → 3,6 min** | cálculo (aritmética sobre os números acima) |
| Atualização diária pelo `numdias` | 328 processos em `numdias=1` (16 min de pausas para os detalhes); 1.110 em `numdias=7` (56 min) | medido; semântica da janela não verificada |

**O que a estimativa não cobre:** informes com data em 2026 de processos que **não tramitam hoje e não foram apresentados em 2026** (por exemplo, arquivados em 2026 com início antes); o sorteio não os alcança. A faixa de 5 mil a 28 mil é do bootstrap de uma amostra de 24; a estimativa por estrato (9.916 + 5.978 = 15.894) usa n = 8 e n = 16 e **não é independente** da primeira. As 16 mil comparadas às 118.684 da Câmara contam **só `informesLegislativos`**; as `movimentacoes` e as `situacoes` (188 e 269 nos 46 processos) ficam fora.

**Cópias exatas (medido, script J; corrige a leitura de "49%").** 10 dos 42 processos com informes têm alguma cópia de um `id` no mesmo processo (646 cópias extras, **todas idênticas ao primeiro**, o dicionário inteiro). O número agregado de 49% (646 de 1.316) **mistura as duas amostras e é puxado por poucos processos**:

| Amostra | Brutos | Extras | Maiores |
|---|---|---|---|
| Aleatória | 303 | 155 (51%) | **151 de um só processo (PDL 470/2023)**; sem ele, 4 extras em 143 brutos |
| Dirigida | 1.013 | 491 (48%) | **4 processos somam 480**: PL 2338/2023 (249), VET 51/2025 (128), PDL 261/2025 (94), PL 856/2025 (9) |

A dirigida foi escolhida (inclui processos com muitos informes), então não dá taxa. **Não se pode dizer que "49% dos informes são cópia" em geral**; o que está medido é que **alguns** processos repetem o mesmo informe dezenas de vezes (4 de 46, PL 2338/2023, VET 51/2025, PDL 261/2025 e PDL 470/2023, concentram 622 das 646 extras). **O motivo da duplicação não foi investigado.**

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
- **Intervalo de confiança (script K, Clopper-Pearson exato, 95%):** 1 de 220 informes de 2026 → **0,012% a 2,51%**; só a dirigida, 1 de 190 → 0,013% a 2,90%; só a aleatória, 0 de 30 → 0% a 11,57% (limite superior unilateral de 95%: 9,5%). **Ressalva de agrupamento:** 190 dos 220 vêm da amostra dirigida e os informes de um processo não são independentes (o mesmo órgão, o mesmo sistema); o intervalo trata os 220 como independentes e é, portanto, **otimista**. Conclusão permitida: **o fenômeno de 28% não aparece nesta amostra**. Não permite concluir que "o Senado não tem o padrão" nem que o caso é "raro" em geral.
- **Os `00:00:xx` estão concentrados (script L):** **34 dos 40 informes da hora 00 estão em 3 processos** (VET 36/2009: 23, PL 5956/2019: 6, PL 5987/2019: 5). Dos 34 `00:00:xx`: 31 são de 2019 ou antes, com segundos `01` (19), `02` (8), `03` (2), `04` (1) e `05` (1); 2 são de **2023-02-02 `00:00:01`** ("Matéria aguardando distribuição", em dois processos distintos, PL 2633/2019 e PL 5987/2019; **não é "legado" de migração**, parece um lote do início da legislatura: **inferência**); e 1 é o `00:00:00` de 2026 (VET 51/2025, 2026-03-04, "A matéria passa a sobrestar, a partir desta data, a pauta das sessões [...]"; **a descrição sugere um evento automático: inferência, sem confirmação**; é o único informe daquele dia no processo).
- **Teste da hipótese "segundos sequenciais para ordenar eventos de um dia sem hora" (script L, só nos 5 processos com `00:00:xx`):** nos dias que têm `00:00:xx`, **todos** os informes do dia do processo são `00:00:xx` (0 informes de hora real no mesmo dia); os segundos são consecutivos (`01, 02` ou `01` a `05`); e o `id` do informe cresce com os segundos nos 5 processos (e dentro de cada dia examinado). Isso é **coerente** com a hipótese, mas é **só inferência**, sobre 5 processos, e o caso de 2026 (um informe só no dia) e os dois de 2023 não seguem esse padrão.
- **Sobre a pergunta "a data vem com ou sem hora":** em **todos** os informes e movimentações o campo é sempre `aaaa-mm-dd hh:mm:ss` (1.316 de 1.316 e 188 de 188; nenhum só com data). **O equivalente de "só data" no Senado mora em `situacoes.inicio|fim` e em `despachos.data` (e em `dataSituacaoAtual`, `dataApresentacao` etc. da lista), não nos informes.**
- **Movimentações:** `dataEnvio` e `dataRecebimento` com `00:00:00`: 0 de 188 e 0 de 181.
- **Fuso (não declarado):** nenhum campo traz deslocamento. Evidência indireta (**inferência, não verificado**): os informes de 2026 vão de 07:xx a 21:xx e se concentram entre 08:00 e 19:59 (script C, histograma), o que é horário de expediente de Brasília e não de UTC (que cairia entre 04:xx e 18:xx de Brasília). Conferi também 3 processos com atualização na véspera (2026-11-27): último informe às 09:02, 11:31 e 12:14, com `dthUltimaAtualizacao` às 11:51, 11:59 e 17:28, o que não contradiz, mas **também não prova**, hora local.

## Ordem e chave natural (medido, nos 46 processos)

- **Nos 46 não há campo de sequência** (`sequencia`): as chaves de um informe são só as da tabela de formato.
- **Ordem:** em **42 de 42** processos com informes (dos 46) a lista vem em ordem **crescente** de `data` (empates entre cópias contam como ordem); entre os informes **distintos**, **0 de 42** processos têm dois com a mesma data e hora. Nos 46, portanto, `data` ordenaria sem desempate, mas isso **não é garantia**.
- **`id` do informe:** 670 pares (processo, `id`) distintos de 1.316 brutos; **nenhum `id` aparece em mais de um processo**; as 646 repetições são cópias exatas (chave natural candidata: (processo, `id`) com as cópias contando uma vez, como o ADR 0034 faz com as 38 duplicatas da Câmara). Estabilidade do `id` entre cargas: **não medida** (uma carga só).
- **`id` da movimentação:** 188 distintos em 188.
- **Processo:** a chave é o `id` do processo (inteiro, ex. `8986903`); `codigoMateria` é o id legado (senado.md); o detalhe traz os dois.
- **Autuações:** sempre 1 nos 46 (outros tipos podem ter mais; não medido).

## Texto livre e dados pessoais (medido; ADR 0005 não avaliado)

- **Equivalente de `despacho`/texto livre:** `informesLegislativos[].descricao`. Não há campo curto controlado separado como a `descricaoTramitacao` da Câmara (112 valores, até 57 caracteres); o análogo controlado é `siglaSituacaoIniciada`, em 37% dos informes.
- **Tamanho (670 distintos):** mín 12, mediana 137, p99 2.125, **máx 4.176** caracteres; 0 vazios; 19 com espaço no começo ou no fim.
- **Controle e o código da Câmara (lido):** nenhum caractere de controle além de `\t`, `\n` e `\r` (0 de 670); mas **212 das 670 descrições (32%) têm `\r\n`, `\n` ou `\t`** (169 com `\r\n`, 43 com `\n` sem `\r`, 1 com `\t`). **`_text` (`apps/legislature/parsing.py:44-56`) faz `strip()` (linha 50) e levanta `RowError` se sobrar qualquer caractere de categoria Unicode `Cc` (linha 51), o que inclui `\n`, `\r` e `\t`; `camara_tramitacao_parsing.py:20` importa esse `_text` e o usa para `siglaOrgao` e `descricaoTramitacao` (linhas 61-62, lidas até aí).** Medido com a mesma regra (script M): **208 das 670 descrições (31%) seriam recusadas** (as outras 4 têm a quebra só nas pontas, que o `strip` tira). Se o Senado reusasse esse `_text` para `descricao`, a falha fechada (ADR 0034, decisão 5; ADR 0005, decisão 6) **derrubaria a carga inteira** na primeira linha. A Câmara não tinha nenhum caractere de controle em `descricaoTramitacao` (`camara.md`, Rodada 5). Como o ADR 0034 trata `despacho` e o Senado só tem um campo de texto, o desenho dessa recusa é decisão do dono.
- **Formato de data e hora (lido):** `_DATE_TIME` (`camara_tramitacao_parsing.py:23`) é `[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}` e o `fullmatch` está na linha 44; o Senado usa **espaço** entre data e hora (`aaaa-mm-dd hh:mm:ss`, 1.316 de 1.316), então esse leitor **recusaria todas as linhas** do Senado sem mudança. `_occurred_at` (linhas 41-51) grava como horário de Brasília (`ZoneInfo("America/Sao_Paulo")`, linha 24; `replace(tzinfo=_BRASILIA)`, linha 51).
- **Pessoas no texto (regex; não é leitura):** **324 de 670 mencionam a palavra "Senador/Senadora"** (menção a senadores, não necessariamente o nome), "Relator/Relatora" em 87, "Deputado/Deputada" em 12, "Ministro/Ministra" em 11, nome com "(PARTIDO/UF)" em **7** (esse é o padrão mais próximo de "nome de parlamentar"), "Sr./Sra./Dr./Dra." em 36 informes (inclui o "Dr." usado antes do nome de senadores) e **145 trechos "Sr./Sra. Nome, cargo"** (o padrão mais estreito; não contei em quantos informes). Pelo que li, são convidados de audiência pública; vi cargos como "Secretário-Executivo do Ministério da Fazenda" e "Advogado, representante de [...]", e alguns parecem não ser parlamentares nem agentes públicos. **CPF, CNPJ, e-mail e telefone: 0 de 670, mas só para os padrões formatados** (CPF com pontos e traço, CNPJ com máscara, `nome@dominio`, telefone `(dd) nnnn-nnnn`); **um CPF sem máscara passaria**, e o ADR 0005 nasceu de um CPF que passou a vir preenchido num arquivo de mesmo esquema. Para o CPF sem máscara medi só a sequência de 11 dígitos isolada (0 de 670; script M), que não cobre dígitos com outro separador. O texto dos informes não foi lido por inteiro.
- **`documentosAssociados[].autoria`** repete o nome e o partido do autor dos 2.750 documentos; `autoria[]` do processo (não lida a fundo) traz `codigoParlamentar` e `autor` (61 autores na PEC 1/2026). **A allowlist do Senado no ADR 0005 (processo: `id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL; votação e votos; senadores) não lista `descricao`, `autoria` nem `documentosAssociados`; pela decisão 1 ("o que não está na lista é descartado na leitura"), ficam fora por padrão.** O `senado.md` não cita o ADR 0005 para esses campos (só "Fica para o P-12 e o P-16" para os endpoints de senadores), e o ADR 0029, decisão 3, **já descartou o informe legislativo** da votação do Senado ("Descartados na leitura: [...] `descricaoVotacao` e o informe legislativo (ADR 0005)"). As listas `/processo` já trazem `autoria` em cada item (chave de `lista2026.json`; valor não impresso), o que a pergunta 5 do #371 também levanta.

## Comparação com a Câmara (só o que foi medido)

| | Câmara (ADR 0034, 0035) | Senado (esta medição) |
|---|---|---|
| Canal | arquivo CSV anual (38,5 MB), 1 requisição | detalhe por processo, **1 requisição por processo** (3,5 h a 10,7 h em série para 4.175 a 12.871; 71 se só os citados por votações) |
| Volume em 2026 | 118.684 tramitações, 46.295 proposições | estimativa ≈ 16 mil **informes** (percentis 2,5-97,5 do bootstrap de 5,4 a 28,4 mil sobre n = 24, 17 zeros, 7 positivos, máx 7; tende a subestimar a cauda; o sorteio não pegou PEC/PLP/MPV), 12.871 processos; as movimentações e situações ficam fora da conta |
| Itens por proposição/processo | **só 2026:** mediana 2, máx 98 (proposições com tramitação em 2026) | **só 2026**, processos com ao menos um informe de 2026: aleatória 7 processos, mediana 4, máx 7 (soma 30); dirigida 20 processos, mediana 7,5, máx 24. **Histórico completo do processo (rótulo):** mediana 6 distintos (aleatória), máx 207 (dirigida) |
| Chave | (proposição, `sequencia`, `dataHora`, `siglaOrgao`, `descricaoTramitacao`) | `id` do informe (inteiro), sem `sequencia` (nos 46) |
| Duplicatas | 40 linhas (0,03%) | 646 de 1.316 (49%) nos 46, mas **151 das 155 da aleatória são de 1 processo e 480 das 491 da dirigida são de 4**; não é taxa geral |
| Data e hora | `dataHora` (com `T`), fuso não declarado | `aaaa-mm-dd hh:mm:ss` (com espaço), fuso não declarado |
| Hora `00:00` | 28,2% | 1 de 220 em 2026 (IC 95% exato 0,012% a 2,51%; amostra agrupada, 190 de 220 da dirigida); `00:00:0N` em 3 processos antigos (**inferência:** segundos para ordenar eventos sem hora) |
| Texto | `descricaoTramitacao` curta + `despacho` longo (3.426) | um só `descricao` (até 4.176), com quebra de linha em 32% |
| Órgão | `siglaOrgao` (74 valores) | `colegiado.sigla` (16 na amostra, mais o `colegiado` vazio em 70 de 670) e `enteAdministrativo.sigla` (22) |

## Perguntas para o dono

Nenhuma é decisão tomada; cada uma muda o modelo, e as opções vêm sem recomendação.

1. **O que é "tramitação" no Senado?** Só `informesLegislativos` (o texto com data e hora, a que mais se parece com a da Câmara), ou também as `movimentacoes` (envio e recebimento entre órgãos, sem texto) e as `situacoes` (estado com início e fim, só data)? São três listas no mesmo detalhe, com chaves e horas diferentes.
2. **Escopo e forma da coleta.** O padrão dos ADR 0031, 0033 e 0034 é um arquivo CSV por conjunto; aqui não há arquivo em massa e a coleta é uma requisição por processo, com 3 s de pausa. Quais processos entram: (a) só os **apresentados em 2026** (4.175; 3,5 h), (b) todos os que **tramitam ou foram apresentados em 2026** (12.871; 10,7 h; inclui informes de 2026 de processos mais antigos), (c) **só os processos citados pelas votações** do Senado (71 ids na janela de 365 dias do #371; cerca de 4 min de pausa; liga 90 de 90 votações por construção, enquanto "só 2026" liga 33 de 90, ou 37%), ou (d) outro recorte? E o incremental: o `numdias` (existe, mas não se sabe se `dataUltimaAtualizacao` muda quando entra um informe novo) ou recarga completa? **Custo da carga longa (#370, citado):** o prazo de 1800 s do cliente vale por download, não por carga; uma falha em 1 de N derruba a carga inteira, e o agendador retenta em `RETRY_HOURS = 6` (`apps/sources/scheduling.py:36`), com o horário da retentativa tirado de `now` **antes** de `ingest` (`scheduling.py:101`; li essas duas linhas e o trecho em volta, não li `draw_next`), isto é, 6 h contadas do início da coleta, sem retomada. Uma carga de 3,5 h a 10,7 h falharia inteira por 1 resposta ruim.
3. **Recorte "2026".** Pela data do informe (como a Câmara, que é pela `dataHora`) ou pelo processo apresentado em 2026? Os dois divergem: processos de 2025 e 2024 têm informes de 2026 (PL 2234/2024: 24 de 24).
4. **O texto `descricao` entra?** Pelo ADR 0005, decisão 1, e pela allowlist do Senado do ADR 0005 (que não lista `descricao`), o campo **fica fora por padrão**; o ADR 0029, decisão 3, já descartou o informe legislativo da votação; e a decisão do dono para o `despacho` da Câmara foi não ingerir (ADR 0034, decisão 2). Sem o texto, o informe fica só com data, `colegiado`, `enteAdministrativo` e `siglaSituacaoIniciada` (37%). Com ele, entram menções a senadores (324 de 670) e a convidados de audiência (nome e cargo; alguns cargos sugerem particulares), e o `_text` atual recusaria 208 das 670 por causa da quebra de linha (ver "Texto livre"). Entra, entra só o de certos tipos, ou fica de fora?
5. **`documentosAssociados` e `autoria`.** Cada informe pode trazer documentos associados (364 de 670), cada um com `autoria` (nome e partido de quem assina), e o processo e a lista trazem `autoria`. Nenhum está na allowlist do Senado no ADR 0005. Entram (e quais campos: `identificacao`, `tipo`, `url`?) ou ficam fora?
6. **Hora.** O ADR 0035, emenda 1, item 5, já diz que **`00:00:30` conta como 00:00** (a tela corta no minuto), então a alternativa "só `00:00:00`" **não existe no precedente**: pelo precedente, `00:00:01` a `00:00:05` (33 informes: 31 de 2019 ou antes e 2 de 2023-02-02) mostrariam só a data. A regra se aplica ao Senado como está, ou o Senado mostra sempre a hora? Dados: 1 de 220 informes de 2026 está em `00:00:00` (amostra agrupada; ver o intervalo), e o que é só data no Senado mora em `situacoes` e `despachos`.
7. **Cópias exatas.** Nos 4 processos que concentram quase todas (622 das 646), o mesmo informe se repete dezenas de vezes. Como tratar uma cópia exata: vale uma linha (chave (processo, `id` do informe), como as 38 duplicatas da Câmara), recusa, ou o dono quer ver o motivo antes?
8. **Anos anteriores.** Processos com informes só em anos anteriores ficam de fora do "2026" (PL 2338/2023, por exemplo, tem 126 informes distintos e nenhum de 2026)? A página do Senado diria "tramitação em 2026" como a da Câmara?

## Não verificado

- **Fuso** de todos os campos de data e hora (nenhum traz deslocamento; só indício de horário local).
- **Significado de `00:00:01`..`00:00:05` e de `00:10:00`** (os 6 `2022-12-21 00:10:00`, que parecem carga em lote), dos dois `2023-02-02 00:00:01` e do `00:00:00` de 2026: é inferência.
- **Por que há informes duplicados**, e se isso depende do tipo, do tamanho do processo ou do dia; o "49%" não é uma taxa geral.
- **Estabilidade ao longo do tempo:** se o `id` do informe, a ordem e o conteúdo mudam entre duas coletas (uma carga só); se a fonte reclassifica (como `senado.md` viu nos votos); **se `dataUltimaAtualizacao` muda quando só um informe novo é acrescentado** (e, portanto, se o `numdias` serve de incremental).
- **Estimativa de volume** com 24 processos aleatórios (n = 8 para os apresentados em 2026), cauda pesada (um processo tem 207 informes); informes com data em 2026 de processos fora da união não foram contados.
- **Semântica do `numdias`** (a janela de 1 dia incluiu 3 dias de calendário).
- **Processo com mais de 1 autuação:** nos 46 (inclui 2 MPV, 1 PLN e 1 PRS) todos têm 1; outros tipos e casos não foram vistos.
- **Texto dos informes** lido só por contagens por padrão (regex) e por amostra de formas; não li os 670, e a presença de dados pessoais além de nomes e de CPF sem máscara fora do padrão de 11 dígitos não está descartada.
- **XML e NDJSON** do detalhe; o parâmetro `v` (versão do serviço); o comportamento de 429 e 503 (nunca ocorreram na saída da sessão, sem registro durável além dos logs dos detalhes).
- **404 para um processo retirado** (medi só um id que nunca existiu).
- **ADR 0005** (allowlist para este campo), **P-16** (licença e uso comercial do Senado, ainda "não dito").
- **Se as duas medições simultâneas (esta e a do #371) saíram do mesmo IP**, e portanto se a taxa combinada passou do limite do ADR 0008.
- **Código do polis:** li `apps/sources/http_client.py:84` (o `USER_AGENT`), `apps/legislature/parsing.py:44-56`, `apps/legislature/camara_tramitacao_parsing.py:1-62` e `apps/sources/scheduling.py:36` e `:95-122`. O que o resto da normalização, o leitor CSV, o `PlainCsvReader` e `draw_next` fariam com este formato **não foi lido por aqui**; o que digo do ADR 0034 e 0035 vem do texto dos ADRs, e o que digo do #370 e do #371 vem dos textos deles (lidos por `git show`), não de mim.

## Comandos

Tudo roda fora do repo, com os dados em um diretório `$D` (aqui, o scratchpad da sessão). Antes de cada requisição, `sleep 3`; `UA='polis-coletor (+https://github.com/masterlxz/polis)'`; `B=https://legis.senado.leg.br/dadosabertos`.

**Downloads (2026-11-28, 13:58Z a 14:07Z, 55 requisições):**

```bash
D=/caminho/sen; mkdir -p $D/dirigida $D/aleatoria; cd $D
UA='polis-coletor (+https://github.com/masterlxz/polis)'; B=https://legis.senado.leg.br/dadosabertos
W='%{http_code} %{size_download} %{time_total}\n'
curl -sS -A "$UA" -o apidocs.json -w "$W" $B/v3/api-docs                                                    # 200, 215.797 B, 157 caminhos, 42 deprecated, versão 4.1.3.120
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -D lista2026.hdr -o lista2026.json -w "$W" "$B/processo?dataInicioApresentacao=2026-01-01&dataFimApresentacao=2026-11-28"   # 4.175 itens
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o tramitando.json -w "$W" "$B/processo?tramitando=S"      # 10.951 itens
sleep 3; curl -sS -A "$UA" -o geracsv.csv -w "$W" https://www12.senado.leg.br/dados-abertos/geracsv                 # catálogo
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o numdias1.json -w "$W" "$B/processo?numdias=1"           # 328
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o numdias7.json -w "$W" "$B/processo?numdias=7"           # 1.110
sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -w "$W" "$B/processo/1"                                    # 404, 72 B
# duas buscas para achar os ids de PL 2338/2023 e PLP 68/2024
for q in "sigla=PL&numero=2338&ano=2023" "sigla=PLP&numero=68&ano=2024"; do sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -w "$W" "$B/processo?$q"; done
# amostra dirigida (22 detalhes); os 22 ids estao na tabela "Dirigida"
for id in 8986903 9055580 8986931 9063446 8987995 9070516 8984726 9069218 8984112 9053761 8985534 8984232 9024204 8984950 8984209 8998698 8986924 8441243 8701679 8985559 8988413 8989972; do
  sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o dirigida/p$id.json -w "$id $W" "$B/processo/$id"; done
# amostra aleatória (24 detalhes; os ids saem do script G)
for id in $(cat aleatoria/ids.txt); do
  sleep 3; curl -sS -A "$UA" -H 'Accept: application/json' -o aleatoria/p$id.json -w "$id $W" "$B/processo/$id"; done
```

(Na medição real, o `-D arquivo.hdr` foi usado também no PEC 1/2026 e nos 3 detalhes de 2026-11-27 (PDL 261/2025, PL 168/2026 e PL 2234/2024); o laço acima não o repete. Esses 3 vieram de processos com atualização na véspera, escolhidos da lista de 2026 por `dataSituacaoAtual >= 2026-11-27`. Os `-w` dos 42 detalhes foram para `fetch1.log` e `fetch2.log`; os das demais requisições só para a saída da sessão.) Contagem das 55 requisições: especificação 1, lista de 2026 1, `tramitando=S` 1, catálogo 1, `numdias` 2, id inexistente 1, duas buscas 2, dirigida 22, aleatória 24.

Os scripts abaixo vêm todos depois deste mesmo prelúdio: `cat prelude.py <script>.py | python3 -I -` com `D` exportado (o `-I` impede que o diretório de dados carregue código; o `D` é lido pelo prelúdio). Os scripts H a M foram acrescentados na revisão do PR; o I lê a especificação e o catálogo já gravados.

**`prelude.py`:**

```python
import collections, csv, glob, json, math, os, random, re, statistics, unicodedata

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
        ident=d["identificacao"],
        id=d["id"],
        bytes=os.path.getsize(arq),
        autuacoes=len(a),
        informes=len(informes(d)),
        distintos=len(distintos(d)),
        mov=sum(len(u.get("movimentacoes", [])) for u in a),
        sit=sum(len(u.get("situacoes", [])) for u in a),
        desp=len(d.get("despachos", [])),
    )


for nome in ("dirigida", "aleatoria"):
    arqs = sorted(glob.glob(f"{D}/{nome}/p*.json"))
    rows = [linha(json.load(open(f)), f) for f in arqs]
    print("##", nome, len(rows), "processos")
    for r in rows:
        print(
            r["ident"],
            r["id"],
            r["bytes"],
            r["autuacoes"],
            r["informes"],
            r["distintos"],
            r["mov"],
            r["sit"],
            r["desp"],
            sep=" | ",
        )
    for k in ("bytes", "informes", "distintos", "mov", "sit"):
        v = sorted(r[k] for r in rows)
        print(
            f"{k}: min {v[0]} mediana {statistics.median(v)} media {statistics.mean(v):.1f} max {v[-1]}"
        )
```

Saída (resumo; as linhas por processo estão nas tabelas acima): dirigida `bytes: min 3228 mediana 18171.0 media 88579.7 max 978415`, `informes: min 0 mediana 12.0 media 46.0 max 375`, `distintos: min 0 mediana 10.5 media 23.7 max 207`, `mov: min 0 mediana 3.5 media 6.3 max 30`; aleatória `bytes: min 2632 mediana 9068.0 media 12418.6 max 94208`, `informes: min 0 mediana 6.0 media 12.6 max 160`, `distintos: min 0 mediana 6.0 media 6.2 max 25`, `mov: min 0 mediana 2.0 media 2.1 max 10`, `sit: min 1 mediana 3.0 media 3.9 max 12`.

**Script B, formato, cópias, chave e ordem:**

```python
def forma(s):
    return re.sub(r"\d", "9", s) if isinstance(s, str) else repr(s)


bru = [(d["id"], x) for d in todos for x in informes(d)]
dis = {(p, x["id"]): x for p, x in bru}
print(
    "processos",
    len(todos),
    "| informes brutos",
    len(bru),
    "| distintos por (processo, id)",
    len(dis),
)

# tipos das chaves de um informe e de uma movimentacao
for rot, itens in (
    ("informe", [x for _, x in bru]),
    (
        "movimentacao",
        [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])],
    ),
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
print(
    "mov.dataEnvio:",
    collections.Counter(forma(m["dataEnvio"]) for m in mov),
    "| dataRecebimento:",
    collections.Counter(forma(m["dataRecebimento"]) for m in mov),
)
print(
    "dthUltimaAtualizacao:",
    collections.Counter(forma(d.get("dthUltimaAtualizacao")) for d in todos),
)

# copias exatas
por_proc = collections.defaultdict(list)
for p, x in bru:
    por_proc[(p, x["id"])].append(x)
extra = sum(len(v) - 1 for v in por_proc.values())
identicas = sum(1 for v in por_proc.values() for y in v[1:] if y == v[0])
print(
    "copias extras do mesmo id no mesmo processo:",
    extra,
    "| identicas ao primeiro (dict inteiro):",
    identicas,
)
print(
    "processos com alguma copia extra:",
    len({p for (p, i), v in por_proc.items() if len(v) > 1}),
    "de",
    len({p for p, _ in bru}),
    "com informes",
)

# mesmo id de informe em processos diferentes?
procs_por_id = collections.defaultdict(set)
for p, i in dis:
    procs_por_id[i].add(p)
print(
    "ids de informe que aparecem em mais de um processo:",
    sum(1 for s in procs_por_id.values() if len(s) > 1),
)
mids = [m["id"] for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print(
    "movimentacoes: ids",
    len(mids),
    "distintos",
    len(set(mids)),
    "| ids em comum com informes:",
    len(set(mids) & {i for _, i in dis}),
)

# ordem em que a fonte entrega
cresc = sum(
    1
    for d in todos
    if informes(d) and [x["data"] for x in informes(d)] == sorted(x["data"] for x in informes(d))
)
print(
    "processos com informes: ",
    sum(1 for d in todos if informes(d)),
    "| em ordem crescente de `data`:",
    cresc,
)
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
print(f"esperado por acaso, 1 minuto em 1440: {100 / 1440:.3f}%")

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
print(
    "2026: n",
    len(r26),
    "| 00:00:00:",
    sum(1 for x in r26 if x["data"][11:] == "00:00:00"),
    "| 00:00:xx:",
    sum(1 for x in r26 if x["data"][11:16] == "00:00"),
)
print(
    "anos < 2020, segundos dos 00:00:xx:",
    sorted(
        collections.Counter(
            x["data"][17:] for x in U if x["data"][:4] < "2020" and x["data"][11:16] == "00:00"
        ).items()
    ),
)
print("2026, hora do dia:", sorted(collections.Counter(int(x["data"][11:13]) for x in r26).items()))

# movimentacoes
mov = [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print(
    "movimentacoes:",
    len(mov),
    "| dataEnvio 00:00:00:",
    sum(1 for m in mov if m["dataEnvio"][11:] == "00:00:00"),
    "| dataRecebimento 00:00:00:",
    sum(1 for m in mov if (m["dataRecebimento"] or "")[11:] == "00:00:00"),
)

# o unico 00:00:00 de 2026
for d in todos:
    for x in distintos(d):
        if x["data"].startswith("2026") and x["data"][11:] == "00:00:00":
            print("o caso de 2026:", d["identificacao"], x["data"], repr(x["descricao"][:70]))

com26 = lambda ds: sum(any(x["data"].startswith("2026") for x in distintos(d)) for d in ds)
print(
    "processos com algum informe distinto de 2026:",
    com26(todos),
    "de",
    len(todos),
    "| dirigida:",
    com26(dirigida),
    "| aleatoria:",
    com26(aleatoria),
)

h0 = collections.Counter(
    d["identificacao"] for d in todos for x in distintos(d) if x["data"][11:13] == "00"
)
print("informes na hora 00, por processo:", h0.most_common(3), "| total:", sum(h0.values()))
```

Saída: `informes distintos: 670`; `hora exatamente 00:00:00: 1`; `hora 00:00:xx: 34`; `hora 00:10:00: 6`; por ano `[total, 00:00:xx, 00:10:00]`: 2009 `[16, 16, 0]`, 2011 `[1, 1, 0]`, 2012 `[2, 2, 0]`, 2013 `[1, 1, 0]`, 2014 `[2, 2, 0]`, 2019 `[20, 9, 0]`, 2020 `[4, 0, 0]`, 2021 `[8, 0, 0]`, 2022 `[9, 0, 6]`, 2023 `[35, 2, 0]`, 2024 `[328, 0, 0]`, 2025 `[24, 0, 0]`, 2026 `[220, 1, 0]`; `2026: n 220 | 00:00:00: 1 | 00:00:xx: 1`; `anos < 2020, segundos dos 00:00:xx: [('01', 19), ('02', 8), ('03', 2), ('04', 1), ('05', 1)]`; hora do dia em 2026: `[(0, 1), (7, 4), (8, 22), (9, 15), (10, 18), (11, 24), (12, 16), (13, 13), (14, 19), (15, 22), (16, 16), (17, 15), (18, 19), (19, 9), (20, 6), (21, 1)]`; `movimentacoes: 188 | dataEnvio 00:00:00: 0 | dataRecebimento 00:00:00: 0`; `o caso de 2026: VET 51/2025 2026-03-04 00:00:00`; `processos com algum informe distinto de 2026: 27 de 46 | dirigida: 20 | aleatoria: 7`; `informes na hora 00, por processo: [('VET 36/2009', 23), ('PL 5956/2019', 6), ('PL 5987/2019', 5)] | total: 40`.

**Script D, texto livre e dados pessoais:**

```python
U = [x for d in todos for x in distintos(d)]
L = [x["descricao"] for x in U]
print("descricoes distintas:", len(L), "| vazias:", sum(1 for s in L if not s.strip()))
ln = sorted(len(s) for s in L)
print(
    "tamanho min/mediana/p99/max:",
    ln[0],
    statistics.median(ln),
    ln[int(0.99 * len(ln)) - 1],
    ln[-1],
)
print(
    "com \\r\\n:",
    sum("\r\n" in s for s in L),
    "| com \\n sem \\r:",
    sum("\n" in s and "\r" not in s for s in L),
    "| com \\r sem \\n:",
    sum("\r" in s and "\n" not in s for s in L),
    "| com \\t:",
    sum("\t" in s for s in L),
)
print(
    "controle alem de \\t \\n \\r:",
    sum(bool(re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", s)) for s in L),
)
print("espaco no comeco ou no fim:", sum(s != s.strip() for s in L))

# dado pessoal no texto (regex = estimativa por baixo/por cima, nao leitura)
pad = {
    "Senador/Senadora": r"\b[Ss]enador(a)?\b",
    "Deputado/Deputada": r"\b[Dd]eputad[oa]\b",
    "Relator/Relatora": r"\b[Rr]elator(a)?\b",
    "Ministro/Ministra": r"\bMinistr[oa]\b",
    "Sr./Sra./Dr./Dra.": r"\b(Sr|Sra|Dr|Dra)\.",
    "nome (PARTIDO/UF)": r"\([A-Za-z\-]{2,12}/[A-Z]{2}\)",
    "CPF": r"\d{3}\.\d{3}\.\d{3}-\d{2}",
    "CNPJ": r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
    "e-mail": r"[\w.\-]+@[\w\-]+\.[\w.\-]+",
    "telefone": r"\(?\d{2}\)?\s?9?\d{4}-\d{4}",
}
for k, p in pad.items():
    print(f"{k}: {sum(bool(re.search(p, s)) for s in L)} de {len(L)}")

# convidados de audiencia: trechos "Sr. <nome>, <cargo>" (so a forma do trecho, sem nomes)
tr = [
    m.group(0)
    for s in L
    for m in re.finditer(r"\b(Sr|Sra)\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][^,;.]{2,60},\s*[^,;.]{3,60}", s)
]
print(
    "trechos 'Sr./Sra. Nome, cargo':",
    len(tr),
    "| forma de um deles, nome omitido:",
    re.sub(r"^(Sr|Sra)\.\s+[^,]+", r"\1. <nome>", tr[0]),
)

da = [y for x in U for y in x.get("documentosAssociados", [])]
print(
    "documentosAssociados:",
    len(da),
    "| chaves:",
    sorted({k for y in da for k in y}),
    "| com `autoria`:",
    sum(1 for y in da if y.get("autoria")),
)
```

Saída: `descricoes distintas: 670 | vazias: 0`; `tamanho min/mediana/p99/max: 12 137.0 2125 4176`; `com \r\n: 169 | com \n sem \r: 43 | com \r sem \n: 0 | com \t: 1`; `controle alem de \t \n \r: 0`; `espaco no comeco ou no fim: 19`; Senador/Senadora 324, Deputado/Deputada 12, Relator/Relatora 87, Ministro/Ministra 11, Sr./Sra./Dr./Dra. 36, nome (PARTIDO/UF) 7, CPF 0, CNPJ 0, e-mail 0, telefone 0 (todos "de 670"); `trechos 'Sr./Sra. Nome, cargo': 145`; `documentosAssociados: 2750 | chaves: ['autoria', 'data', 'descricao', 'id', 'identificacao', 'siglaTipo', 'tipo', 'url'] | com autoria: 2750`. O "36" de "Sr./Sra./Dr./Dra." inclui o "Dr." usado antes do nome de senadores; os 145 trechos "Sr./Sra. Nome, cargo" vêm do padrão mais estreito.

**Script E, universo, estimativa e incremental:**

```python
apres26 = {x["id"] for x in json.load(open(f"{D}/lista2026.json"))}
tramit = {x["id"] for x in json.load(open(f"{D}/tramitando.json"))}
uniao = apres26 | tramit
print(
    "apresentados em 2026:",
    len(apres26),
    "| tramitando:",
    len(tramit),
    "| interseccao:",
    len(apres26 & tramit),
    "| uniao:",
    len(uniao),
)

d26 = [sum(x["data"].startswith("2026") for x in distintos(d)) for d in aleatoria]
em26 = [d["id"] in apres26 for d in aleatoria]
print(
    "amostra aleatoria: n",
    len(d26),
    "| apresentados em 2026:",
    sum(em26),
    "| informes distintos com data em 2026 (soma):",
    sum(d26),
)
print("por processo (d26):", sorted(d26))
m = statistics.mean(d26)
print(
    f"media {m:.2f} mediana {statistics.median(d26)} max {max(d26)} -> x uniao = {m * len(uniao):.0f}"
)
random.seed(7)
bs = sorted(statistics.mean(random.choices(d26, k=len(d26))) * len(uniao) for _ in range(5000))
print(f"bootstrap (5000, semente 7) 2,5% = {bs[125]:.0f}  97,5% = {bs[4874]:.0f}")
e = [v for v, f in zip(d26, em26) if f]
o = [v for v, f in zip(d26, em26) if not f]
print(
    f"estrato apresentados em 2026: n {len(e)} media {statistics.mean(e):.2f} x {len(apres26)} = {statistics.mean(e) * len(apres26):.0f}"
)
print(
    f"estrato anteriores a 2026 (tramitando): n {len(o)} media {statistics.mean(o):.2f} x {len(uniao) - len(apres26)} = {statistics.mean(o) * (len(uniao) - len(apres26)):.0f}"
)

tam = [os.path.getsize(f) for f in glob.glob(f"{D}/aleatoria/p*.json")]
print(
    f"bytes por detalhe (aleatoria): mediana {statistics.median(tam):.0f} media {statistics.mean(tam):.0f} -> x uniao = {statistics.mean(tam) * len(uniao) / 1e6:.0f} MB; x apres26 = {statistics.mean(tam) * len(apres26) / 1e6:.0f} MB"
)
for n, rotulo in ((len(uniao), "uniao"), (len(apres26), "apresentados em 2026")):
    print(
        f"carga em serie, 1 detalhe a cada 3 s, {rotulo}: {n} req = {n * 3 / 3600:.1f} h (so a pausa)"
    )

# incremental pelo filtro numdias
for n in (1, 7):
    v = json.load(open(f"{D}/numdias{n}.json"))
    ts = sorted(x["dataUltimaAtualizacao"] for x in v)
    print(
        f"numdias={n}: {len(v)} processos; dataUltimaAtualizacao de {ts[0]} a {ts[-1]}; {len(v) * 3 / 60:.0f} min de pausas para buscar todos os detalhes"
    )
```

Saída: `apresentados em 2026: 4175 | tramitando: 10951 | interseccao: 2255 | uniao: 12871`; `amostra aleatoria: n 24 | apresentados em 2026: 8 | informes distintos com data em 2026 (soma): 30`; `por processo (d26): [0 x17, 2, 2, 3, 4, 6, 6, 7]`; `media 1.25 mediana 0.0 max 7 -> x uniao = 16089`; `bootstrap (5000, semente 7) 2,5% = 5363  97,5% = 28423`; `estrato apresentados em 2026: n 8 media 2.38 x 4175 = 9916`; `estrato anteriores a 2026 (tramitando): n 16 media 0.69 x 8696 = 5978`; `bytes por detalhe (aleatoria): mediana 9068 media 12419 -> x uniao = 160 MB; x apres26 = 52 MB`; `uniao: 12871 req = 10.7 h`; `apresentados em 2026: 4175 req = 3.5 h`; `numdias=1: 328 processos; dataUltimaAtualizacao de 2026-11-25T17:37:06.897 a 2026-11-27T18:54:29.011; 16 min`; `numdias=7: 1110 processos; ... de 2026-11-21T11:16:57.091 a 2026-11-27T18:54:29.011; 56 min`.

**Script F, campos controlados e chaves de topo:**

```python
U = [x for d in todos for x in distintos(d)]
print("informes distintos:", len(U))
print(
    "com siglaSituacaoIniciada:",
    sum("siglaSituacaoIniciada" in x for x in U),
    "| valores distintos:",
    len({x["siglaSituacaoIniciada"] for x in U if "siglaSituacaoIniciada" in x}),
)
print(
    "colegiado.sigla distintas:",
    len({x["colegiado"].get("sigla") for x in U}),
    "| colegiado vazio:",
    sum(not x["colegiado"] for x in U),
)
print("enteAdministrativo.sigla distintas:", len({x["enteAdministrativo"]["sigla"] for x in U}))
print("com documentosAssociados:", sum(bool(x.get("documentosAssociados")) for x in U))
print("chaves de um informe, na ordem em que vieram:", list(U[0].keys()))
print("tamanho de `descricao` (caracteres), maximo:", max(len(x["descricao"]) for x in U))
print("ids de informe: min", min(x["id"] for x in U), "max", max(x["id"] for x in U))
print(
    "processos:",
    len(todos),
    "| chaves de topo (uniao):",
    len({k for d in todos for k in d}),
    "| chaves de topo (todos tem):",
    sorted(set.intersection(*[set(d) for d in todos])),
)
```

Saída: `com siglaSituacaoIniciada: 248 | valores distintos: 34`; `colegiado.sigla distintas: 17 | colegiado vazio: 70` (o 17 conta o valor ausente como um valor; o script M dá 16 siglas sem contar o vazio); `enteAdministrativo.sigla distintas: 22`; `com documentosAssociados: 364`; `ids de informe: min 93334 max 2333088`; `chaves de topo (uniao): 42`.

**Script G, sorteio da amostra aleatória:**

```python
apres26 = {x["id"] for x in json.load(open(f"{D}/lista2026.json"))}
tramit = {x["id"] for x in json.load(open(f"{D}/tramitando.json"))}
random.seed(20261128)
ids = random.sample(sorted(apres26 | tramit), 24)
print(*ids)
```

Saída (grave-a em `aleatoria/ids.txt` antes do download; o `for id in $(cat ...)` aceita os ids separados por espaço): `8861962 7897075 9106496 9135954 7834921 3335633 9048998 8756412 8747042 8696463 8992806 9082795 7748539 8380185 9112008 8694974 7835670 9052244 8932012 8239329 8908708 8494730 8696986 9095406`.

**Script H, chaves opcionais das listas e do `numdias`:**

```python
for nome in ("lista2026", "tramitando", "numdias1", "numdias7"):
    v = json.load(open(f"{D}/{nome}.json"))
    c = collections.Counter(k for x in v for k in x)
    print(nome, "itens:", len(v))
    for k in ("dataUltimaAtualizacao", "ultimaInformacaoAtualizada", "dataSituacaoAtual"):
        print(f"  {k}: {c[k]} de {len(v)}")
    print(
        "  chaves que não estão em todos os itens:", sorted(k for k, n in c.items() if n < len(v))
    )
```

Saída: `lista2026 itens: 4175`, `dataUltimaAtualizacao: 3906 de 4175`, `ultimaInformacaoAtualizada: 3906 de 4175`, `dataSituacaoAtual: 4010 de 4175`; `tramitando itens: 10951`, `dataUltimaAtualizacao: 5047 de 10951`, `ultimaInformacaoAtualizada: 5047 de 10951`, `dataSituacaoAtual: 10799 de 10951`; `numdias1 itens: 328`, `dataUltimaAtualizacao: 328 de 328`, `dataSituacaoAtual: 323 de 328`; `numdias7 itens: 1110`, `dataUltimaAtualizacao: 1110 de 1110`, `dataSituacaoAtual: 1093 de 1110`. As chaves que faltam em algum item de `lista2026` são `apelido`, `dataDeliberacao`, `dataSituacaoAtual`, `dataUltimaAtualizacao`, `normaGerada`, `objetivo`, `siglaTipoDeliberacao`, `situacaoAtual` e `ultimaInformacaoAtualizada`; em `tramitando`, também `urlDocumento`.

**Script I, varredura local da especificação e do catálogo:**

```python
spec = json.load(open(f"{D}/apidocs.json"))
padrao = re.compile(
    r"informe|andamento|tramita|movimenta|despacho|atualiza|situa[cç]|hist[oó]ric|evento|decis",
    re.I,
)
achados = []
for caminho, v in spec["paths"].items():
    g = v["get"]
    texto = " ".join(str(g.get(k, "")) for k in ("summary", "description")) + " " + caminho
    if padrao.search(texto):
        achados.append((caminho, bool(g.get("deprecated")), g.get("summary")))
print("caminhos que casam o padrão amplo:", len(achados), "de", len(spec["paths"]))
for caminho, dep, resumo in achados:
    print(" ", "[depreciado]" if dep else "[ativo]     ", caminho, "|", resumo)
print(
    "/processo/{id} depreciado na especificação:",
    spec["paths"]["/dadosabertos/processo/{id}"]["get"].get("deprecated", False),
)

with open(f"{D}/geracsv.csv", encoding="utf-8-sig") as f:
    linhas = list(csv.DictReader(f, delimiter=";"))
conjuntos = {}
for r in linhas:
    chave = (r["nom_conjunto_dados"], r["txt_url"])
    conjuntos.setdefault(chave, r)
print("linhas do catálogo:", len(linhas), "| pares (conjunto, url) distintos:", len(conjuntos))
amplo = re.compile(
    r"tramita|andamento|movimenta|informe|despacho|atualiza|situa[cç]|hist[oó]ric", re.I
)
casam = sorted(
    {
        nome
        for (nome, url), r in conjuntos.items()
        if amplo.search(
            " ".join(
                str(r.get(c) or "") for c in ("nom_conjunto_dados", "des_conjunto_dados", "txt_url")
            )
        )
    }
)
print("nomes de conjunto que casam em nome, descrição ou url:", len(casam))
for nome in casam:
    print(" ", nome)
```

Saída (resumida): `caminhos que casam o padrão amplo: 25 de 157` (os ativos e depreciados citados na seção "Onde estão"); `/processo/{id} depreciado na especificação: False`; `linhas do catálogo: 2268 | pares (conjunto, url) distintos: 467`; `nomes de conjunto que casam em nome, descrição ou url: 48`, dos quais os de processo legislativo são "Atualizações da Matéria Legislativa", "Tramitações da Matéria Legislativa", "Matérias em tramitação no Senado Federal", "Matérias que tramitaram na Legislatura atual", "Projetos e Matérias tramitando nas Comissões" e as listas de vetos; o resto são conjuntos administrativos (demonstrações contábeis, pessoal e outros).

**Script J, cópias por amostra e informes de 2026 por processo:**

```python
# informes de 2026 por processo, só os processos com ao menos um (o que a Câmara mede)
for rotulo, ds in (("dirigida", dirigida), ("aleatoria", aleatoria)):
    v = sorted(
        n for n in (sum(x["data"].startswith("2026") for x in distintos(d)) for d in ds) if n
    )
    print(
        f"{rotulo}: {len(v)} processos com informe de 2026 | mediana {statistics.median(v)} | máx {v[-1]} | soma {sum(v)}"
    )

# cópias exatas por amostra (o 49% mistura as duas)
for rotulo, ds in (("dirigida", dirigida), ("aleatoria", aleatoria)):
    linhas = sorted(
        ((len(informes(d)) - len(distintos(d)), len(informes(d)), d["identificacao"]) for d in ds),
        reverse=True,
    )
    brutos = sum(n for _, n, _ in linhas)
    extras = sum(e for e, _, _ in linhas)
    print(
        f"{rotulo}: brutos {brutos} extras {extras} ({100 * extras / brutos:.0f}%) | maior: {linhas[0][2]} com {linhas[0][0]} | 4 maiores somam {sum(e for e, _, _ in linhas[:4])}"
    )
    print(f"  sem o maior: extras {extras - linhas[0][0]} de {brutos - linhas[0][1]} brutos")
```

Saída: `dirigida: 20 processos com informe de 2026 | mediana 7.5 | máx 24 | soma 190`; `aleatoria: 7 processos com informe de 2026 | mediana 4 | máx 7 | soma 30`; `dirigida: brutos 1013 extras 491 (48%) | maior: PL 2338/2023 com 249 | 4 maiores somam 480`; `  sem o maior: extras 242 de 638 brutos`; `aleatoria: brutos 303 extras 155 (51%) | maior: PDL 470/2023 com 151 | 4 maiores somam 155`; `  sem o maior: extras 4 de 143 brutos`.

**Script K, intervalo de confiança exato da hora `00:00:00` em 2026:**

```python
def clopper_pearson(k, n, alfa=0.05):
    """Intervalo exato (bilateral) de uma proporção, por bisseção na cauda binomial."""

    def cauda_sup(p):  # P(X >= k)
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))

    def cauda_inf(p):  # P(X <= k)
        return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(0, k + 1))

    def bissecao(f, alvo, crescente):
        lo, hi = 0.0, 1.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if (f(mid) < alvo) == crescente:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    inf = 0.0 if k == 0 else bissecao(cauda_sup, alfa / 2, True)
    sup = 1.0 if k == n else bissecao(cauda_inf, alfa / 2, False)
    return inf, sup


def zeros_exatos(ds):
    xs = [x for d in ds for x in distintos(d) if x["data"].startswith("2026")]
    return sum(x["data"][11:] == "00:00:00" for x in xs), len(xs)


for rotulo, ds in (("todos", todos), ("dirigida", dirigida), ("aleatoria", aleatoria)):
    k, n = zeros_exatos(ds)
    inf, sup = clopper_pearson(k, n)
    print(
        f"{rotulo}: {k} de {n} informes de 2026 em 00:00:00 | IC 95% exato: {100 * inf:.3f}% a {100 * sup:.2f}%"
    )
print("0 de 30, limite superior unilateral exato de 95%:", end=" ")
print(f"{100 * (1 - 0.05 ** (1 / 30)):.1f}%")
```

Saída: `todos: 1 de 220 informes de 2026 em 00:00:00 | IC 95% exato: 0.012% a 2.51%`; `dirigida: 1 de 190 ... 0.013% a 2.90%`; `aleatoria: 0 de 30 ... 0.000% a 11.57%`; `0 de 30, limite superior unilateral exato de 95%: 9.5%`.

**Script L, os informes `00:00:xx` por processo, por dia e por `id`:**

```python
print("== informes com hora 00:00:xx, por processo e ano")
for d in todos:
    u = [x for x in distintos(d) if x["data"][11:16] == "00:00"]
    if not u:
        continue
    datas = collections.Counter(x["data"][:10] for x in distintos(d))
    divide = sum(1 for x in u if datas[x["data"][:10]] > 1)
    todos_ids_na_ordem = [x["id"] for x in sorted(u, key=lambda x: x["data"])]
    cresc = todos_ids_na_ordem == sorted(todos_ids_na_ordem)
    print(
        d["identificacao"],
        "| 00:00:xx:",
        len(u),
        "| anos:",
        sorted({x["data"][:4] for x in u}),
        "| dividem a data com outro informe do processo:",
        divide,
        "| id cresce com os segundos:",
        cresc,
    )

print("== por dia: informes 00:00:xx contra os outros informes do mesmo dia (mesmo processo)")
mesmo_dia_com_hora_real = 0
total = 0
for d in todos:
    por_dia = collections.defaultdict(list)
    for x in distintos(d):
        por_dia[x["data"][:10]].append(x)
    for dia, xs in por_dia.items():
        z = [x for x in xs if x["data"][11:16] == "00:00"]
        if z:
            total += len(z)
            mesmo_dia_com_hora_real += sum(1 for x in xs if x["data"][11:16] != "00:00")
print(
    "informes 00:00:xx:", total, "| informes de hora real nos mesmos dias:", mesmo_dia_com_hora_real
)

print("== ordem do `id` dentro de cada dia que tem 00:00:xx")
for d in todos:
    por_dia = collections.defaultdict(list)
    for x in distintos(d):
        por_dia[x["data"][:10]].append(x)
    for dia, xs in sorted(por_dia.items()):
        z = [x for x in xs if x["data"][11:16] == "00:00"]
        if len(z) >= 2:
            seg = [x["data"][17:] for x in sorted(xs, key=lambda x: x["data"])]
            ids = [x["id"] for x in sorted(xs, key=lambda x: x["data"])]
            print(d["identificacao"], dia, "| segundos:", seg, "| id cresce:", ids == sorted(ids))
            break

# 00:00:xx a partir de 2023: quais são
for d in todos:
    for x in distintos(d):
        if x["data"][11:16] == "00:00" and x["data"][:4] >= "2023":
            print(
                "00:00:xx de 2023 em diante:",
                d["identificacao"],
                x["data"],
                repr(x["descricao"][:40]),
            )
```

Saída: 5 processos têm `00:00:xx`: `VET 51/2025` (1, ano 2026), `VET 36/2009` (22, anos 2009 a 2014, 13 dividem a data com outro informe `00:00:xx`), `PL 2633/2019` (2, anos 2019 e 2023), `PL 5987/2019` (4, anos 2019 e 2023), `PL 5956/2019` (5, ano 2019), todos com `id cresce com os segundos: True`; `informes 00:00:xx: 34 | informes de hora real nos mesmos dias: 0`; por dia, `VET 36/2009 2009-08-12 | segundos: ['01', '02'] | id cresce: True`, `PL 5987/2019 2019-11-18 | segundos: ['01', '02']`, `PL 5956/2019 2019-11-19 | segundos: ['01', '02', '03', '04', '05']`; `00:00:xx de 2023 em diante`: `PL 2633/2019 2023-02-02 00:00:01 'Matéria aguardando distribuição'`, `PL 5987/2019 2023-02-02 00:00:01 'Matéria aguardando distribuição'` e `VET 51/2025 2026-03-04 00:00:00`.

**Script M, formatos que faltavam, quebra de linha e a regra do `_text`:**

```python
U = [x for d in todos for x in distintos(d)]

# `documentosAssociados[].data`: formato em todos os itens (antes só se viu o exemplo)
da = [y for x in U for y in x.get("documentosAssociados", [])]
print(
    "documentosAssociados[].data:", collections.Counter(re.sub(r"\d", "9", y["data"]) for y in da)
)

# despachos (topo do detalhe)
dp = [x for d in todos for x in d.get("despachos", [])]
print("despachos:", len(dp), "| cancelado:", collections.Counter(x["cancelado"] for x in dp))
print("  providencias por despacho:", collections.Counter(len(x["providencias"]) for x in dp))
print("  chaves de providencias:", sorted({k for x in dp for p in x["providencias"] for k in p}))
print("  data:", collections.Counter(re.sub(r"\d", "9", x["data"]) for x in dp))

# movimentacoes: colegiadoDestino vazio
mov = [m for d in todos for a in d["autuacoes"] for m in a.get("movimentacoes", [])]
print(
    "movimentacoes com colegiadoDestino {}:",
    sum(not m["colegiadoDestino"] for m in mov),
    "de",
    len(mov),
)

# colegiado.sigla: quantas siglas e quantos itens sem sigla
siglas = {x["colegiado"]["sigla"] for x in U if x["colegiado"]}
print(
    "colegiado.sigla distintas (sem contar o vazio):",
    len(siglas),
    "| informes sem colegiado:",
    sum(not x["colegiado"] for x in U),
)


# o que `_text` (apps/legislature/parsing.py:44-56) recusaria: strip e depois qualquer categoria Unicode Cc
def recusada(s):
    return any(unicodedata.category(c) == "Cc" for c in s.strip())


L = [x["descricao"] for x in U]
print(
    "descrições com \\n, \\r ou \\t em qualquer posição:",
    sum(any(c in s for c in "\n\r\t") for s in L),
)
print(
    "descrições que `_text` recusaria (Cc depois do strip):",
    sum(recusada(s) for s in L),
    "de",
    len(L),
)

# CPF sem máscara: sequência de 11 dígitos (o padrão do script D só pega o formato com pontos e traço)
print(
    "11 dígitos seguidos:", sum(bool(re.search(r"(?<!\d)\d{11}(?!\d)", s)) for s in L), "de", len(L)
)
```

Saída: `documentosAssociados[].data: Counter({'9999-99-99T99:99:99': 2750})`; `despachos: 35 | cancelado: Counter({'Não': 35})`; `providencias por despacho: Counter({1: 33, 3: 1, 2: 1})`; `data: Counter({'9999-99-99': 35})`; `movimentacoes com colegiadoDestino {}: 91 de 188`; `colegiado.sigla distintas (sem contar o vazio): 16 | informes sem colegiado: 70`; `descrições com \n, \r ou \t em qualquer posição: 212`; `descrições que _text recusaria (Cc depois do strip): 208 de 670`; `11 dígitos seguidos: 0 de 670`.
