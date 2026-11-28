# Senado: processos e tramitações. Regras que a fatia precisa respeitar (levantamento)

**Data:** 2026-11-28. **Natureza:** levantamento por leitura de código, ADRs e docs, para o dono decidir **antes** do modelo. **Não decide nada, não propõe código e não chama a API do Senado** (as medições são de outras tarefas). Rótulos como em `fontes/README.md`: *documentação* (texto lido), *medido* (número de uma medição já registrada nos docs do repo), *inferência* (minha leitura). Toda afirmação sobre código traz `arquivo:linha` de algo que **li**; o que não li está dito. Linhas conferidas na `origin/main` de 2026-11-28 (`3069107`).

## Resumo em 7 linhas

1. **Licença:** o Senado não declara licença nem termos para a API (`fontes/senado.md:57-59`). Habilitar qualquer conjunto do Senado é **decisão do dono, por escrito, no admin** (`owner_decision` + justificativa); o banco recusa habilitar sem isso. Redistribuir e uso comercial seguem no P-16.
2. **Rede:** o `PoliteClient` cobre User-Agent, pausa de 3 s, 429/503 e 403. **Não cobre uma carga de N downloads como um todo:** o prazo de 1800 s vale por download, não por carga; uma falha em 1 de N derruba a carga inteira e recomeça do zero 6 h depois; e uma volta longa do `collect_due` segura todos os outros conjuntos e o batimento do agendador.
3. **Dado pessoal:** a lista do ADR 0005 para o processo do Senado é curta (id, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL). `autoria` e tudo o mais **não estão nela** e, pela decisão 1 do ADR 0005, ficam fora. Texto livre de andamento: mesma lógica do `despacho` (ADR 0034) e do informe legislativo (ADR 0029).
4. **Ligação:** a votação do Senado já guarda `process_id` e `matter_id` (`apps/legislature/models.py:133-134`), sem chave estrangeira, e a API já os expõe. A relação votação-processo é **N votações para 1 processo**, sem tabela de ligação (a Câmara precisa de uma porque é N para N).
5. **O que a Câmara resolve e o Senado não tem:** a Câmara entrega arquivos anuais em massa; o Senado entrega JSON por API, sem paginação em `/processo`, com dois sistemas de ids e endpoints depreciados. O formato de coleta é **novo** (não há leitor de CSV a reaproveitar).
6. **O que decide o custo da fatia:** o **universo de processos** (só os que as votações citam, no máximo 87 em 360 dias; ou todos de um ano; ou os "tramitando") e **se as tramitações entram agora**. Sem o N, não dá para dizer se a etiqueta de rede atual basta. N vem das outras duas tarefas.
7. **13 decisões do dono** na seção 5, cada uma com opções, custo (lido no código) e recomendação.

---

## 1. Licença, atribuição e uso comercial

### 1.1 O que está documentado

| Tema | O que diz | Onde | Rótulo |
|---|---|---|---|
| Licença nomeada | Nenhuma. O catálogo CSV não tem coluna de licença; a especificação OpenAPI traz `info.license`, `info.termsOfService`, `info.contact` e `externalDocs` **nulos**; o Plano de Dados Abertos 2026/2028 define "licença aberta" sem nomear nenhuma | `fontes/senado.md:49`, `:55`, `:57` | medido / documentação |
| Atribuição | A política de uso do **portal** diz: conteúdo "pode ser utilizado [...] desde que seja citada a fonte e para fins lícitos". O `sobre` dos dados abertos fala em "citar sua proveniência" | `fontes/senado.md:41`, `:54` | documentação |
| Uso comercial | Não dito (nem permitido nem proibido). A Câmara, ao contrário, diz que pode | `fontes/senado.md:50` | documentação |
| Redistribuição e armazenamento | Nenhuma restrição além de "fins lícitos" e "citar a fonte". "Ausência de restrição declarada não é autorização verificada" (PRD §8.2) | `fontes/senado.md:61-62` | documentação |
| A política vale para a API? | **Lacuna.** A política fala em "Portal do Senado Federal" e não cita a API nem os dados abertos; a API está em outro host (`legis.senado.leg.br`). Meu entendimento anterior ("é a política mais próxima") é interpretação, e nenhuma fonte lida a liga expressamente | `fontes/senado.md:48`, `:56`, `:59` | inferência |
| Texto por endpoint | A descrição de `/processo` (e de `/processo/{id}`) na especificação **não foi lida** nas rodadas registradas (só `info.*` e a "Restrição de requisições") | `fontes/senado.md:57` | não lido |
| LAI e Decreto 8.777/2016 | O decreto é do Executivo federal; Câmara, Senado e TSE não estão claramente cobertos | `lgpd-lai.md:15` | inferência (de terceiros) |

### 1.2 O que é lacuna e o que depende do P-16

| Item | Situação |
|---|---|
| Uso comercial, exportação em massa, redistribuição | **P-16** (ADR 0008, decisão 9; `lgpd-lai.md`, pergunta 5). "Nada vai a público antes" (PRD §11; repetido nos ADRs 0029 e 0034). |
| Base legal para tratar dado pessoal público (LGPD art. 7º §3º e §7º) | **P-16**, `lgpd-lai.md` perguntas 1 e 2. Para processo legislativo o ponto aparece só em texto livre (seção 3). |
| Se a política do portal alcança a API | Lacuna de leitura, nunca fechada. Hoje o cadastro diz "a política de uso do portal pede citar a fonte; a especificação da API não declara licença nem termos" (`apps/sources/catalog.py:52-56`). |
| "Dados de processos judiciais" no P-16 | **Não é este assunto.** Aquela linha do P-16 trata de processo judicial; processo legislativo não está nela. |

### 1.3 O portão de licença para habilitar um conjunto novo do Senado (ADR 0008, decisão 1)

- **O que exige:** um `Dataset` só é habilitado se a fonte declarou licença **para aquele conjunto** (`declared`, com `license_id`) **ou** se o dono registrou por escrito a decisão de coletar mesmo assim, com o motivo (`owner_decision`, com `license_justification`). `none` não habilita. Não herda de outro conjunto (ADR 0008, decisão 1).
- **Quem decide:** o **dono**, no admin. Câmara e Senado não declaram licença nomeada, e o ADR 0008 diz que "a decisão de habilitá-los é do dono, registrada no cadastro (P-15 não a toma por ele)".
- **Como o código impõe:** `Dataset.Format`, `LicenseBasis` e as constraints `dataset_enabled_requires_license_basis` e `dataset_enabled_requires_allowed_columns` em `apps/sources/models.py` (`Format` em `:57-64`, constraints em `:181-196`; `clean` e `_clean_license` mais adiante no mesmo arquivo, lidos). O catálogo nasce `enabled=False` e **nunca habilita nem copia a justificativa** (`apps/sources/catalog.py:3-6`; comentários em `:117-119` e `:164-166`).
- **Precedente do Senado:** `senado/senadores` (ADR 0028) e `senado/votacoes` (ADR 0029) são `owner_decision`, desabilitados ao nascer, habilitados pelo dono (`catalog.py:155` e `:198`). Um conjunto de processos seguiria a mesma via.
- **Checagem automática de mudança de licença (ADR 0008, decisão 2):** só vale para `declared` com `license_check_url` (CKAN, `ingestion.py:147-151`). O Senado não tem CKAN, então **não há** checagem; o ADR 0029 já diz "se o Senado declarar licença ou termos, reconferir (sem checagem automática)".
- **Atribuição (ADR 0008, decisão 3):** a API devolve fonte, conjunto, data da coleta, `url_origem` e licença (`apps/legislature/views.py:56-65`). Dois detalhes que valem para um conjunto de processos: (a) `url_origem` é `IngestionRun.source_url`, que `ingest` grava como a URL do **conjunto** (`ingestion.py:70`), não a do processo; (b) o nome da fonte no cadastro é "Senado Federal: Dados Abertos" (`catalog.py:44`), e o texto proposto em `fontes/senado.md:67` é "Senado Federal, Dados Abertos Legislativos". Nada disso trava; é decisão de texto.

---

## 2. Etiqueta de rede (ADR 0008, decisões 4 a 6) e o `PoliteClient`

### 2.1 Regra por regra

| Regra do ADR 0008 | O que o código faz | Onde (lido) | Cobre? |
|---|---|---|---|
| `User-Agent` próprio e honesto, nunca de navegador (decisão 4) | Constante fixa `polis-coletor (+https://github.com/masterlxz/polis)`, sem parâmetro para trocar; entra em toda requisição | `http_client.py:84`, `:384-387` | Sim |
| Em série, pausa mínima de 3 s por host (decisão 5) | `min_interval=3.0`; `_pause` espera o que falta entre o **início** de uma requisição e o da seguinte, por host e por instância. O ritmo real é `max(3 s, duração da requisição anterior)` | `http_client.py:260`, `:352-358` | Sim. O comando `collect_due` usa **uma** instância para todos os conjuntos (`collect_due.py:17`), então a pausa vale entre conjuntos da mesma volta |
| 429 e 503: recuo exponencial respeitando `Retry-After` | Até `max_attempts=4`, espera `3 s * 2^(n-1)` ou o `Retry-After` se maior, teto de 300 s. Passou das 4 tentativas: `DownloadError` | `http_client.py:261-263`, `:346-349`, `:404-408` | Sim. **502 e 504 não recuam** (erro na hora; decisão registrada no ADR 0008) |
| 403 ou bloqueio: parar o host, nunca mudar identidade (decisão 5) | 401, 403 e 451 viram `BlockedError`; o host entra em `_blocked_hosts` e a instância recusa novas requisições a ele. `ingest` grava `blocked` e põe a **`Source` inteira** em `paused` | `http_client.py:86`, `:326-327`, `:343-345`; `ingestion.py:83-85` | Sim. **Alcance:** pausar a `Source` `senado` para `senadores` e `votacoes` também (o portão recusa fonte pausada, `ingestion.py:98-99`) |
| 3xx | Todo redirecionamento é recusado (sem `HTTPRedirectHandler`) | `http_client.py:293-304` | Sim. Relevante: `GET /materia/tiposNatureza` responde **301** (`fontes/senado.md:105`); um endpoint depreciado que redireciona viraria erro |
| Agendamento sem horário redondo (decisão 6) | `draw_next`: mesma hora do dia, minuto sorteado em 1 a 59 e **nunca múltiplo de 5**; respeita `earliest_hour_utc`. Os conjuntos do Senado usam 24 h e 08:00 UTC | `scheduling.py:39`, `:50-60`; `catalog.py:161-162`, `:203-204` | Sim, para o **início** da coleta |
| Canal: API para detalhe e incremental; nada novo sobre endpoint `deprecated` (decisão 7) | O cliente não sabe de endpoints depreciados; a regra é de quem escolhe a URL | `fontes/senado.md:71`, `:102-105` | Não é do cliente. **Não verificado** se `/processo/{id}` e subrecursos de tramitação estão fora dos 42 `deprecated` |
| Prazo total e watchdog | `total_timeout=1800 s` **por download**: vigia status, cabeçalhos, corpo e (com a thread de abertura) DNS e conexão. Cada tentativa tem seu `_Watchdog` e a abertura roda numa thread própria | `http_client.py:93-140`, `:265`, `:332`, `:360-381` | Sim, **por download** |

### 2.2 Uma carga com milhares de requisições de detalhe: o que o cliente cobre e o que não cobre

Cada `client.download` é independente. O desenho existente para "N downloads num só `ingest`" é `fetch_pages` (até 20 páginas, `json_list.py:82-123`) e `fetch_senate_votings` (1 download). **Não há** hoje uma função que faça milhares. O que o código impõe a ela:

| Ponto | Fato lido | Consequência para N grande |
|---|---|---|
| Tempo total | Não há prazo total por carga. O ritmo é `max(3 s, latência)` por requisição (`http_client.py:352-358`) | **N x 3 s no mínimo:** 100 -> 5 min; 1.000 -> 50 min; 5.000 -> 4 h 10; 10.000 -> 8 h 20; 20.000 -> 16 h 40. A latência de `/processo/{id}` **não foi medida** (a das listas foi 0,22 a 0,75 s, `fontes/senado.md:96`); só pesa se passar de 3 s |
| Uma falha derruba tudo | Falha de download propaga para `ingest`, vira `error_code=download` e a execução `failed`; nada é gravado e o bruto anterior fica (`ingestion.py:124-127`, `:62-89`). O agendador retenta em `RETRY_HOURS = 6` **do zero** (`scheduling.py:36`, `:101-102`, `:119`) | Com N alto, uma única resposta anômala (um 429 que passou das 4 tentativas, um 502, um corpo fora do formato) joga fora horas de coleta, e a seguinte as repete. **Não há retomada nem cache de detalhes já lidos** |
| Falha fechada por item | O leitor JSON recusa a carga se um campo permitido faltar (`json_list.py:162-164`) ou se um valor for objeto, lista ou booleano (`json_list.py:176-177`, linha rejeitada -> `MALFORMED_ROW`, `ingestion.py:182-186`) | Um só processo com `tramitando` booleano, `autoria` aninhada ou campo omitido (os tipos **não foram medidos**) para a carga inteira, a menos que a função de coleta já converta (como `NESTED` em `json_senado_votacoes.py:37`) |
| Volta longa trava o resto | `collect_due` trata os conjuntos vencidos **em série**, e `scripts/agendador.sh:21-22` só chama a volta seguinte e só toca o batimento depois que `collect_due` termina. O `healthcheck` do agendador acusa parado se o batimento tem mais de 3 min (`compose.prod.yaml:75`) | Uma volta de horas: (a) atrasa os conjuntos que vêm depois na ordem (`ordering = ["source__slug", "slug"]`, `models.py:180`, ou seja, depois de `senado/processos` vêm `senado/senadores`, `senado/votacoes` e `tse/...`), (b) o contêiner aparece `unhealthy`. Isso **já valeria** hoje para qualquer volta de mais de 3 min (a normalização de 118 mil linhas roda dentro dela, `scheduling.py:123-124`); **a duração real dessas voltas não foi medida** |
| Bloqueio tem raio grande | 403 em qualquer das N requisições pausa a `Source` `senado` (seção 2.1) | Quanto mais requisições, maior a chance de 429 e, no limite, de bloqueio. Não se sabe como o 429 se comporta na prática (`fontes/senado.md:32`) |
| Execução presa em `running` | Se o processo morrer no meio, a `IngestionRun` fica `running`; não achei código que a feche (`monitoring.py:21` só a ignora no painel) | Aumenta com carga longa. Não verifiquei o `ingest_dataset` nem testes |
| Ritmo contra o limite do Senado | 10 req/s documentado (`fontes/senado.md:29`); 1 req a cada 3 s é 0,33 req/s | Folga de 30 vezes; **o limite não é o problema, o tempo e a fragilidade são** |

**Conclusão (inferência):** para N de dezenas ou poucas centenas por dia, o cliente atual basta sem mudança. Para N de milhares, o cliente em si está certo, mas **falta uma camada de carga** (prazo total, retomada ou incremental, tolerância por item), que não existe e seria código novo e decisão do dono (seção 5, D8).

---

## 3. Campos: o que entraria, o que fica fora e por quê

### 3.1 O que o ADR 0005 permite para o Senado

A linha **Senado** da allowlist inicial lista, para o processo: `id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL. **Não lista** `autoria`, tramitação, andamento, textos livres. A decisão 1 diz que o que não está na lista é descartado na leitura, e que a lista é "ponto de partida para revisão", cada coluna conferida contra o dicionário de dados na implementação (ADR 0005, "Allowlist inicial"). **O dicionário de dados de `/processo` não está em `fontes/senado.md`**: o doc só tem os **nomes** dos 17 campos de um item de lista (`fontes/senado.md:77`), sem tipo, exemplo nem frequência de nulos.

### 3.2 Campo por campo (nomes de `fontes/senado.md:77`)

| Campo | ADR 0005 | Proposta de leitura | Por quê / o que não se sabe |
|---|---|---|---|
| `id` | Entra (`id`) | **Entra.** Chave natural (`idProcesso`) | É o id novo; a votação o guarda como `process_id` (`models.py:133`). Estabilidade dos ids **não medida** (`fontes/senado.md:206`) |
| `codigoMateria` | Entra | **Entra** como atributo | Id legado (`fontes/senado.md:86`); a votação o guarda (`models.py:134`). Se é único por processo: **não medido** |
| `identificacao` | Entra ("identificação") | **Entra** | Ex. `PEC 1/2026` (`fontes/senado.md:87`), até 30 caracteres nas votações. **Não há `sigla`, `numero` nem `ano` separados no item de `/processo`** (a votação os tem: `fontes/senado.md:78`), então tipo, número e ano, se forem mostrados em colunas, saem de `identificacao` ou da votação. Decisão de modelo (D9) |
| `ementa` | Entra | **Entra** | Texto livre, pode ter quebra de linha; ver 3.3 |
| `dataApresentacao`, `dataSituacaoAtual`, `dataUltimaAtualizacao` | Entra ("datas") | **Entram**, as três ou só as que a página usa | Formato e nulos **não medidos** (a votação traz `dataApresentacao` como `aaaa-mm-dd`, `fontes/senado.md:154`) |
| `situacaoAtual` | Entra ("situação") | **Entra** | Tipo **desconhecido** (pode ser objeto; o leitor recusa objeto, `json_list.py:176-177`) |
| `tipoDocumento` / `tipoConteudo` | Entra ("tipo") | **Entra um deles** | O ADR 0005 diz só "tipo": qual dos dois, ou ambos, é decisão. Conteúdo **não medido** |
| `urlDocumento` | Entra ("URL") | **Entra** | URL do documento no portal, não da API. Escapar na saída |
| `tramitando` | Não listado | **Fora** até revisão | Provavelmente booleano (inferência); o leitor recusa booleano. Útil para escolher o universo (D2), não para guardar |
| `autoria` | **Não listado** | **Fora** | Ver 3.4 |
| `enteIdentificador`, `casaIdentificadora` | Não listados | **Fora** | Conteúdo **desconhecido**. Pelo nome (inferência) dizem quem identificou o processo; podem ser nome de órgão ou de pessoa. Medir antes |
| `objetivo` | Não listado | **Fora** | Texto livre provável (inferência); mesma regra da ementa se entrar um dia |
| `ultimaInformacaoAtualizada` | Não listado | **Fora** | Semântica desconhecida |
| (detalhe `/processo/{id}`: tramitações, movimentações, documentos) | Não listado | **Fora até a fatia própria** | Forma do JSON **não está** em `fontes/senado.md`. As outras tarefas medem |

### 3.3 Texto livre: ementa e andamento

| Texto | Precedente | A mesma lógica vale para o Senado? |
|---|---|---|
| `ementa` | Entra na Câmara e no Senado pelo ADR 0005; a Câmara troca quebra de linha e TAB por espaço, recusa outro controle e põe teto de 20.000 caracteres (ADR 0033, decisão 7; `camara_proposition_parsing.py:19-28`) | **Sim, com um aviso.** A ementa de projeto pode citar pessoa (homenagem, pensão, denominação de obra; **inferência, não medido nos dados do Senado**). O ADR 0033 ingere a ementa da Câmara sem tratar nomes. O parser do Senado hoje **recusa** qualquer controle, inclusive quebra de linha (`parsing.py:51-52`, usado por `senate_voting_parsing.py:72`); o ADR 0029 deixou isso como "risco não coberto por teste". Para a ementa do processo, a decisão é copiar a regra da Câmara ou manter a recusa (D10) |
| `despacho` (Câmara) | **Não ingerido** (ADR 0034, decisões 2 e "alternativas"): texto livre, até 3.426 caracteres, "cita agentes públicos pelo nome", ADR 0005 não avaliado | **Sim.** O texto de andamento do Senado é o equivalente, e **sua forma não foi medida** aqui. Se tiver descrição livre ("Relator: Senador Fulano"), vale o mesmo: fora até ADR próprio. Entrariam só campos estruturados (data, órgão por sigla ou código, situação), como o ADR 0034 fez |
| `informeLegislativo` e `descricaoVotacao` (Senado) | **Descartados na leitura** (ADR 0029, decisão 3) | Precedente direto do próprio Senado a favor de **não ingerir texto livre sem avaliação** |

### 3.4 `autoria`

- **O que sei:** o nome do campo, no item de lista (`fontes/senado.md:77`). **Conteúdo, tipo e forma não medidos.**
- **Por que fica fora:** (1) não está na lista do ADR 0005; (2) no ADR 0033 a Câmara adiou autores ("Fora desta fatia: [...] autores e temas"); (3) risco concreto, **inferência não medida:** autoria de processo legislativo inclui parlamentares (agentes públicos, nome já tratado no ADR 0005 como público) mas pode incluir **particulares** (por exemplo sugestão legislativa de cidadão ou entidade, projeto de iniciativa popular). Particular é dado pessoal fora do papel público, e o ADR 0005 manda medir antes.
- **O que destravaria:** uma rodada de medição de `autoria` (tipos de autor, quantos particulares, se há nome civil ou CPF), registro no ADR 0005 como emenda de leitura, e validação do P-16 se houver particular. **Mesmo caminho do `despacho`:** volta "só com ADR próprio".
- **Ligação possível sem `autoria`:** autor parlamentar ligado a `Senator` por código seria o uso natural; o ADR 0005 (decisão 2) já prevê ligação por id de origem. Fica para essa fatia.

### 3.5 Retirada pela fonte e lápide (ADR 0005, decisão 9; ADR 0026)

| Ponto | Fato | Onde |
|---|---|---|
| A decisão 9 vale para "qualquer fonte" | "Registro ausente de um arquivo **íntegro** [...] vira retirado pela fonte: some da interface e da API, campos pessoais apagados, fica lápide" | ADR 0005, decisão 9 |
| Na prática só o TSE tem | `RETIREMENT_DATASETS = {"tse/consulta-cand-2026"}`; o ADR 0026 limitou a lápide ao TSE | `config/settings.py:120`; ADR 0026, decisão 1 |
| Câmara e Senado **nunca apagam** | Votações do Senado: "nunca apaga" (ADR 0029, decisão 4; `senate_voting_normalization.py:10`). Proposições e tramitações da Câmara: idem (ADR 0033 decisão 5; ADR 0034 decisão 5) | arquivos citados |
| Em carga por detalhe, "ausente" não existe | Um processo que sumiu da lista ou responde 404/200 vazio não é "registro ausente de um arquivo íntegro": não há arquivo. E o Senado devolve **200 sem dados** para código inexistente em `/senador/{codigo}` (`fontes/senado.md:104`; medido só para senador) | `fontes/senado.md` |

O que há de dado pessoal num processo da allowlist proposta é só o que a ementa citar. Se o dono mantiver o precedente (nunca apaga), o conjunto não implementa a decisão 9 e isso deve ficar escrito no ADR da fatia (D6).

---

## 4. Ligação com o que existe

### 4.1 Como a votação do Senado referencia o processo hoje

| O quê | Onde (lido) |
|---|---|
| `SenateVoting.process_id` (`PositiveIntegerField`, **obrigatório**, sem FK) e `matter_id` (idem) | `apps/legislature/models.py:133-134` |
| Lidos de `idProcesso` e `codigoMateria` por `_int` (recusa vazio, `0`, sinal, não ASCII e acima de int32) | `senate_voting_parsing.py:78-79`; `parsing.py:31-41` |
| Atualizáveis no upsert (a fonte pode corrigir) | `senate_voting_normalization.py:46-47` |
| Na allowlist do conjunto `senado/votacoes` | `catalog.py:189-190` |
| Expostos na API do detalhe como `id_processo` e `codigo_materia`; **não** no item da lista | `views.py:203-204` (a lista, `:151-159`, não os traz) |
| **Nenhuma página os usa** (busca por `id_processo`, `codigo_materia` e `processo` em `web/app` e `web/lib` não achou uso; só um comentário de saúde) | `web/` (não li cada arquivo; foi `grep`) |
| Medido: as 87 votações da primeira coleta real passaram pelo `_int` | `fontes/senado.md:199` (87 votações, 7.047 votos, 0 recusas) |

Consequência: **a ligação votação -> processo já existe como número solto**, e um modelo de processo só precisa de `process_id` único para a junção na leitura. Uma votação com `idProcesso` vazio ou `0` **recusaria a carga inteira de votações** (falha fechada); isso não aconteceu em 87 de 87, mas não é garantia.

### 4.2 O que o modelo da Câmara faz, e se o do Senado teria de espelhar

| Peça da Câmara | O que faz (lido) | Senado: reaproveita? |
|---|---|---|
| `CamaraProposition` com chave `camara_id` único; `year` opcional; `ementa` em branco | `models.py:270-300` | **Espelha a ideia:** chave única no id de origem (`process_id`). Os campos mudam (seção 3) |
| `CamaraVotingProposition`: tabela de ligação com o id da votação **em texto**, sem FK para a votação, `origin`, único em (votação, proposição) | `models.py:303-339`; ADR 0033, decisão 4 | **Não precisa.** Na Câmara a relação é N para N (até 212 proposições por votação, arquivos separados). No Senado a votação traz **um** `idProcesso`, então a relação é N votações para 1 processo e a junção é `SenateVoting.process_id == SenateProcess.process_id` na leitura. **Específico do Senado:** nada de `origin` |
| Sem FK entre as peças, junção na leitura, "404 só para o que o polis conhece" | ADR 0033 decisão 4; ADR 0034 decisão 4; ADR 0035 decisão 2 | **Mesma razão vale:** FK de `SenateVoting` para o processo exigiria o processo existir antes ou junto da votação e reintroduziria a espera e a corrida do ADR 0031. `SenateVote` já não tem FK para `Senator` pelo mesmo motivo (`models.py:155-189`, ADR 0029 decisão 5) |
| `CamaraPropositionStep`: id da proposição em texto, `sequence` nulo, chave de 5 campos com `nulls_distinct=False` | `models.py:342-388`; `camara_tramitacao_normalization.py:36` | **Específico da Câmara.** A chave vem de uma medição (`idTramitacao` não é chave; 13 conflitos reais). A do Senado **só se mede com o dado**. Não reaproveitar a chave sem medir |
| Coleta por **arquivo anual** em CSV (`format: csv`, `PlainCsvReader`), 7 e 5 colunas na allowlist | `catalog.py:265-351`; `ingestion.py:116-119`, `:170-175` | **Específico da Câmara.** O Senado é API JSON; o formato é novo (ver abaixo) |
| Normalização própria `normalize_latest`, transação única, upsert em lotes de 1.000, falha fechada, tetos de 500.000 linhas | `camara_proposition_normalization.py:104-190`; `camara_tramitacao_normalization.py:91-141` | **Reaproveitável como molde** (o ADR 0029 já a copiou para as votações; "duplicação anotada para refatorar depois"). **Os ADRs 0033 e 0034 adiam a generalização com o motivo "sem terceira implementação ainda"**; um conjunto de processos do Senado seria mais uma cópia (D12) |
| Registro em `settings.NORMALIZERS` | `config/settings.py:95-115` | **Reaproveitável** (uma linha por conjunto) |
| Retirada pela fonte / lápide | Nenhuma das três peças da Câmara usa; só o TSE | Ver 3.5 |
| API `GET /internal/v1/camara/proposicoes/<id>/`, id ASCII sem zero à esquerda, int32, 404 só para proposição conhecida, atribuição por execução, 2 consultas | `urls.py:51-57`; `views.py:589-623`; ADR 0035 | **Molde reaproveitável.** Pelas rotas atuais do Senado (`senado/votacoes/...`, `urls.py:32-38`; `senadores/...`, `urls.py:22-31`) a forma natural seria `senado/processos/<id>/`; nome e forma é decisão |
| Página `/camara/proposicoes/[id]` e link na votação só se houver conteúdo (`total_tramitacoes > 0`) | `web/app/camara/votacoes/[id]/page.js:113-127`; ADR 0035 decisão 9 | **Molde.** A página da votação do Senado mostra só a `ementa` da votação (`web/app/senado/votacoes/[codigo]/page.js:129`); o link para o processo é novo |
| Atribuição | `_attribution(run)` | **Reaproveitável.** Ver o aviso do `url_origem` na seção 1.3 |
| Conjunto `Dataset` desabilitado ao nascer, `owner_decision`, 24 h, depois de 08:00 UTC | `catalog.py:164-205`, `:265-351` | **Reaproveitável** |

### 4.3 O que é específico do Senado (e obriga código novo ou decisão)

| Ponto | Fato lido | Efeito |
|---|---|---|
| Formato de coleta novo | `Dataset.Format` tem `json_senado` e `json_senado_votacoes`; o despachante está em `ingestion.py:110-123` e a escolha do leitor em `:165-176`. O formato genérico `json` usa `fetch_pages` com `?pagina=` (`json_list.py:75-79`, `:82`), e **os endpoints de `/processo` não paginam** (`fontes/senado.md:31`) | Um formato novo (como o ADR 0029). O nome tem de caber em 20 caracteres (`models.py:77`, `max_length=20`; `json_senado_votacoes` já tem exatamente 20). Acrescentar um valor de `choices` gera migração (o ADR 0029 listou `sources/0009`): **área §4 do AGENTS, confirmação do dono** |
| Dois sistemas de ids | `id`/`idProcesso` e `codigoMateria` (`fontes/senado.md:84-89`); depreciação em curso, `Sunset` vencido e serviço ainda no ar | Chave = `idProcesso` (a votação já a usa). Nada novo sobre `/materia` (ADR 0008, decisão 7) |
| Listagem exige filtro e não pagina | `fontes/senado.md:30-31`; **volume sem filtro de ano não medido** (`:206`) | O universo (D2) é a primeira decisão de custo |
| Lista já traz o "processo" | Item de lista com 17 campos (`:77`) cobre tudo que o ADR 0005 permite, **sem** chamar o detalhe (inferência, não medido para o detalhe) | Só tramitações e movimentações pedem o detalhe por processo, que é onde "milhares de requisições" nasce |
| `apps.sources` não importa outros apps | `config/settings.py:92-94`; nenhum `from apps.legislature` em `apps/sources/*.py` (conferido por `grep`) | Uma coleta que precise dos `idProcesso` das votações lidos do banco **quebraria essa fronteira**, a menos que o id venha por parâmetro. Custo de D2 opção (a) |
| Teto de linhas do leitor | `JsonListReader` tem `max_items=10_000` por padrão e as votações precisaram de 50.000 (`ingestion.py:167`) | Um conjunto com mais de 10.000 processos exige teto próprio, como as votações |
| Formato do bruto | `JsonListReader` lê `{"dados": [...]}` só com escalares, todo campo permitido tem de existir (`json_list.py:154-170`) | A função de coleta precisa achatar/converter (como `json_senado_votacoes.py:72-95`) |

---

## 5. Decisões que são do dono

Cada uma com opções, o custo que li no código e a minha recomendação. **Recomendação não é decisão.** O N de processos (D2) vem das outras duas tarefas e pode mudar D8.

| # | Decisão | Opções | Custo (lido) | Recomendo |
|---|---|---|---|---|
| D1 | **Habilitar** o conjunto de processos do Senado | (a) `owner_decision` com justificativa escrita por você no admin, como `senado/votacoes`; (b) não habilitar até o P-16 | (a) nada de código; o banco já exige a justificativa (`models.py:189-194`). O catálogo nunca habilita. Nada vai a público antes do P-16 em qualquer caso | **(a)**, só depois do modelo e dos testes, em desenvolvimento, como o ADR 0029. A justificativa é sua |
| D2 | **Universo de processos** | (a) só os que as votações citam (no máximo 87 em 360 dias; distintos **não medido**); (b) todos de um ano, por listas (`ano`, e talvez `sigla`); (c) só `tramitando`; (d) todos, em todos os anos | (a) pequeno, mas precisa dos ids vindos do banco e **quebra a fronteira `sources` -> `legislature`** (seção 4.3), ou de uma lista fixa/parâmetro; (b)(c) 1 requisição por filtro, volume **não medido** (`fontes/senado.md:206`); (d) sem medida | **Depende do N medido.** Se (b) couber em poucas listas, **(b) para o cadastro do processo**. (a) só se o dono quiser "só o que se votou" como na Câmara (ADR 0033 foi "das votações") e aceitar o desenho de parâmetro |
| D3 | **Tramitações** entram nesta fatia? | (a) não, só o processo (como o ADR 0033 antes do 0034); (b) sim, com detalhe por processo | (b) é onde nascem as milhares de requisições (seção 2.2) e a forma do JSON não está registrada. A Câmara fez em 3 fatias (0033, 0034, 0035) | **(a)**: processo agora, tramitação em fatia e ADR próprios |
| D4 | **Allowlist do processo** | (a) as 8 do ADR 0005 (seção 3.2); (b) emendar o ADR 0005 para incluir mais | (a) sem custo de revisão. (b) pede medição e, para `autoria`, o P-16 | **(a)** e declarar a lista no ADR da fatia, como o 0034 fez |
| D5 | **`autoria` e texto livre de andamento** | (a) fora, até medir e ADR próprio (como `despacho`); (b) entra o que for parlamentar | (b) exige distinguir parlamentar de particular em dado **não medido** | **(a)** |
| D6 | **Retirada pela fonte** do processo | (a) nunca apaga (como 0029, 0033, 0034), escrevendo no ADR que a decisão 9 do ADR 0005 não é implementada aqui e por quê; (b) lápide (como o TSE) | (b): `Tombstone`, disjuntor, `apply_tombstones`, runbook (ADR 0026), e "ausente" num carga por detalhe não é bem definido (seção 3.5) | **(a)**, com a frase no ADR (a ementa é o único campo que pode citar pessoa) |
| D7 | **Falha de um item** na carga | (a) falha fechada da carga inteira (ADR 0005, decisão 6; tolerância zero); (b) pular o item e registrar; (c) uma carga por filtro (por ano ou sigla), para a falha de um não derrubar os outros | (b) contradiz "tolerância de linhas rejeitadas: zero" (`ingestion.py`, cabeçalho) e esconde dado que a fonte publicou (o argumento do ADR 0029 contra "ignorar votação sem votos"). (c) mais conjuntos no cadastro | **(a)** para N pequeno. Se N grande, **(c)** antes de (b) |
| D8 | **Carga longa** (só se N for de milhares) | (a) nada: aceitar N x 3 s e o risco de recomeçar; (b) prazo total por carga no `ingest`; (c) retomada (guardar detalhes já lidos) ou incremental por `dataUltimaAtualizacao`; (d) tirar a coleta do laço do agendador | (a) horas de coleta perdidas por 1 falha e o resto dos conjuntos esperando, mais o contêiner `unhealthy` (seção 2.2). (b)(c)(d) são **código novo** em `apps/sources` ou no agendador, e (d) toca **CI/deploy/compose** (área §4: confirmação sua). Nada disso existe | **Medir N primeiro.** N de dezenas a poucas centenas: **(a)**. N de milhares: **(c)** antes de qualquer outra |
| D9 | **Modelo do processo** | (a) `SenateProcess` com `process_id` único, `matter_id`, `identification` em texto, datas, situação, tipo, URL; sem FK com `SenateVoting`, junção na leitura; (b) separar `sigla/numero/ano` lendo `identificacao` (ou da votação); (c) FK de `SenateVoting` para o processo | (a) igual ao padrão do repo (ADR 0029 e 0033). (b) `identificacao` é texto (`PEC 1/2026`); parsear é frágil e **o formato de todas as siglas não foi medido**. (c) reintroduz espera e corrida (ADR 0031), e migra uma tabela já povoada | **(a)**, **sem** (b) e **sem** (c). Mostrar `identification` como veio |
| D10 | **Texto da `ementa`** | (a) regra da Câmara (quebra de linha e TAB viram espaço, outro controle recusa, teto 20.000; ADR 0033, decisão 7); (b) manter a recusa de qualquer controle (a do parser de votação do Senado) | (a) reaproveita `camara_proposition_parsing.py:21-28`. (b) pára a coleta do dia se uma ementa tiver quebra de linha (risco já anotado no ADR 0029, sem teste) | **(a)** |
| D11 | **API e página** | (a) só modelo e normalização agora, API e página em fatia seguinte (como 0033 -> 0035); (b) tudo junto | (b) mistura intenções e vai contra "um PR = uma intenção" (AGENTS §10) | **(a)**. Depois, `GET /internal/v1/senado/processos/<id>/`, 404 só para processo conhecido (ADR 0035), link na página da votação **só quando o processo existir** |
| D12 | **Generalizar o código copiado** | (a) copiar de novo e anotar (como 0029, 0033, 0034); (b) extrair o molde de normalização agora | O ADR 0022 (reafirmado em 0031, 0033, 0034) adia a generalização até haver **terceira** implementação (texto dos ADRs 0033 e 0034); a normalização com transação e lotes já existe em várias cópias e esta seria mais uma. (b) é refatoração e **não pertence a esta fatia** (AGENTS §3E) | **(a)** nesta fatia; abrir tarefa própria de refatoração depois, se você quiser |
| D13 | **Texto de atribuição** do Senado | (a) como está ("Senado Federal: Dados Abertos", `catalog.py:44`); (b) alinhar a "Senado Federal, Dados Abertos Legislativos" (`fontes/senado.md:67`) | (b) é mudança de dado de cadastro, sem migração. A `url_origem` ser a do conjunto, não a do processo, vale nas duas | **(a)** por ora; decidir junto com a página pública (ADR 0008, "componente de atribuição antes de qualquer tela pública") |

---

## Divergências que achei e **não** toquei (fora do escopo desta tarefa)

| Onde | O que | Por que importa para esta fatia |
|---|---|---|
| ADR 0005 (linha Senado) x ADR 0029 e `catalog.py:176-196` | O ADR 0005 põe `nomeParlamentar` e `siglaUFParlamentar` dos votos na coluna **"Fora"** e a "Revisão da allowlist" diz que o voto leva só id, voto, data e partido. O ADR 0029 (decisão 3, "3 campos duplicados por voto") e o catálogo **os ingerem**. O ADR 0029 não cita a divergência | Mostra que a lista do ADR 0005 foi ampliada por ADR de fatia **sem emenda** no 0005. Se o dono quiser a mesma prática para o processo, vale registrar a emenda; se não, é melhor a regra do ADR 0034 (declarar a lista no ADR da fatia). Não é decisão minha |
| `fontes/senado.md:193` | A seção "Estado da integração" começa dizendo "Votações, proposições e o detalhe do senador: nada integrado", e logo abaixo registra as votações como integradas (Sessões 69 a 72) | Só texto desatualizado no doc; quem ler o começo da seção pode achar que não há votações |
| `fontes/senado.md:77` e `:78` | O item de `/processo` não tem `sigla`, `numero` e `ano`; o de `/votacao` tem | Afeta o modelo (D9) |

---

## Perguntas para o dono

Só as que são suas (produto, risco, regra). O resto está assumido na seção 5.

1. **Universo (D2) e tramitações (D3).** Primeiro o cadastro do processo, só o que as votações citam ou todos de um ano? E as tramitações ficam para uma fatia à parte? (Eu recomendo processo primeiro e tramitação depois, mas o universo depende do N das outras tarefas.)
2. **Retirada pela fonte (D6).** Mantém "nunca apaga" no processo do Senado, escrevendo no ADR que a decisão 9 do ADR 0005 não é implementada aqui?
3. **`autoria` (D5).** Fica fora até uma medição própria e o P-16, como o `despacho`? Ou você quer a autoria parlamentar já nesta rodada, aceitando medir o que é particular antes?
4. **Habilitação (D1).** Confirma o mesmo caminho do `senado/votacoes`: `owner_decision` com a justificativa escrita por você, só em desenvolvimento, e nada público antes do P-16?
5. **Carga longa (D8), só se o N for de milhares.** Aceita investir em código de retomada ou incremental, ou prefere reduzir o universo para o cliente atual bastar?

Premissas que **assumi** (me corrija): ementa entra pela allowlist do ADR 0005 como na Câmara; a fatia segue um PR por intenção; o conjunto nasce desabilitado; migração de `choices` é aditiva e passa pela sua confirmação antes de ser gerada.

---

## Não verificado

- **Nada da API do Senado foi chamado.** A forma, os tipos, os nulos e o volume de `/processo` e de `/processo/{id}` (e de tramitações, movimentações, documentos) vêm só de `fontes/senado.md`, que tem os **nomes** dos 17 campos de um item de lista (`:77`) e nada do detalhe.
- **Conteúdo de `autoria`, `enteIdentificador`, `casaIdentificadora`, `objetivo`, `situacaoAtual`, `tipoDocumento`, `tipoConteudo`.** Tipo, exemplo e frequência de nulos desconhecidos. A afirmação de que autoria pode incluir particular é **inferência**, não dado.
- **Se `/processo/{id}` e os subrecursos de tramitação estão entre os 42 endpoints `deprecated`** e se respondem 301 ou 200 vazio para id inexistente (o 200 vazio foi medido só para `/senador/{codigo}`).
- **Número de processos** por ano, por filtro e entre os citados pelas votações (distintos).
- **Latência de `/processo/{id}`** e comportamento real do 429 e do 503 sob carga (`fontes/senado.md:32`).
- **Duração real das voltas do `collect_due` hoje** (por exemplo a normalização das 118 mil tramitações) e, portanto, se o `healthcheck` de 3 min já dispara.
- **Os testes** do `PoliteClient`, da coleta e do agendador: li o código, não os testes (`tests/test_http_client.py`, `tests/test_scheduling.py` existem, não foram abertos). Nada foi executado (ADR 0017).
- **Se alguma página usa `id_processo`/`codigo_materia`:** conferi por `grep` em `web/app` e `web/lib`, não arquivo por arquivo.
- **Texto da política de uso do portal e do `sobre`:** só o que `fontes/senado.md` transcreve; não reabri os links. **Plano de Dados Abertos** e **LAI**: não lidos por mim (o doc diz que o Plano foi lido por texto extraído).
- **Interpretação jurídica** (LGPD, redistribuição, uso comercial): é o P-16; este documento não a faz.
