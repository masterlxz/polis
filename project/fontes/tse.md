# Fonte: Tribunal Superior Eleitoral (Portal de Dados Abertos)

Campos do PRD §8.1. Rótulos de origem: ver [README.md](README.md). Medições feitas em **2026-11-05**, depois das 22:23 GMT, de uma única máquina e sem paralelismo. Ciclos medidos: **2026** (geral, eleição de outubro de 2026, ainda em apuração e prestação de contas) e **2024** (municipal). Por decisão do dono, **só estrutura e contagens**: nenhum valor individual (nome, CPF, título, bens, valores) foi impresso ou commitado. Mesmo formato da [Câmara](camara.md) e do [Senado](senado.md).

## Identificação
- **Instituição:** Tribunal Superior Eleitoral (TSE).
- **Portal de dados abertos:** <https://dadosabertos.tse.jus.br/>, uma instalação **CKAN 2.11.6** (medido: `<meta name="generator" content="ckan 2.11.6">`). Na página inicial: 190 conjuntos de dados, 7 organizações, 12 grupos.
- **Arquivos de dados:** todos servidos de `https://cdn.tse.jus.br/estatistica/sead/...` (medido: 942 de 942 recursos de 2026 e 849 de 849 de 2024 apontam para esse host).
- **Página "Sobre":** <https://dadosabertos.tse.jus.br/about>. Diz que o portal concretiza a **Política de Dados Abertos do TSE (Portaria TSE nº 93/2021)**, tem plano em **Portaria TSE nº 525/2021**, e **substitui o Repositório de Dados Eleitorais (RDE)** (documentação).
- **Contato:** Ouvidoria do TSE (documentação, <https://dadosabertos.tse.jus.br/pages/sobre>).
- **`www.tse.jus.br/eleicoes/estatisticas/repositorio-de-dados-eleitorais` respondeu 403 "Access Denied"** ao meu cliente (medido, corpo de erro de borda do CDN). Não tentei contornar (por exemplo, disfarçando o `User-Agent`). Fica registrado: páginas do `www.tse.jus.br` podem bloquear clientes automatizados.

## Tipo de acesso
1. **Arquivos ZIP no CDN** (o caminho principal para os dados). Cada ZIP traz um CSV por UF e um `leiame.pdf` (medido).
2. **API do CKAN** em `https://dadosabertos.tse.jus.br/api/3/action/...`: medi `package_list` e `package_search`. Ela entrega **metadados** (conjuntos, recursos, URLs, licença, datas), não os dados em si. Se o DataStore do CKAN está ativo para os conjuntos: não verificado.
3. **Não há API de consulta de dados eleitorais** neste portal, pelo que medi. Outros canais do TSE (resultados em tempo real, DivulgaCand, etc.) não foram medidos.

## Formatos
- **Medido:** CSV dentro de ZIP (candidatos, bens, prestação de contas, votação); TXT; PDF; JPEG (fotos de candidatos); `.sha512` ao lado dos ZIPs de boletim de urna.
- **CSV amostrado (consulta_cand 2026 e 2024, bem_candidato 2026, despesas pagas 2024):** codificação **ISO-8859-1/Windows-1252** (não UTF-8), fim de linha **CRLF**, delimitador `;`, campos entre aspas, **sem BOM**, cabeçalho na primeira linha. Pelo que medi, valores ausentes aparecem como marcadores em texto ou código, e não como campo vazio: a coluna `CD_SITUACAO_CANDIDATURA` só contém valores da lista que o meu script tratou como ausentes (`#NULO#`, `#NE#`, `-1`, `-3`, convenção que conheço do TSE). Não verifiquei **quais** desses marcadores ocorrem, nem o mapa completo.
- Datas no formato `dd/mm/aaaa`.

## Autenticação
Nenhuma (medido: todas as chamadas sem credencial).

## Limites de requisição
- **Documentado:** não achei limite de taxa nem política de uso de rede no portal.
- **Medido:** nenhum 429, 503 ou cabeçalho de limite. Fiz cerca de 40 requisições em série com pausa de 3 s (acima das 20 a 30 que eu havia planejado, por ter reexecutado a amostra).
- **`Range` aceito (medido):** `accept-ranges: bytes` e respostas 206 em todos os ZIPs testados. Isso permite ler o índice do ZIP e o começo de um item sem baixar o arquivo.
- **Bloqueio em `www.tse.jus.br`:** 403 (acima). Não sei se o CDN ou o portal têm limite por IP; não testei.

## Frequência de atualização
- **Declarada no CKAN (campo `Frequência de atualização`, documentação):** `candidatos-2026` "4 vezes ao dia"; `candidatos-2024` "Diária"; `resultados-2026` e `resultados-2024` "Diária"; boletim de urna "Eleição". `prestacao-de-contas-eleitorais` não declara.
- **Medido (`Last-Modified`, 2026-11-05):** `consulta_cand_2026.zip` 19:35 GMT; `bem_candidato_2026.zip` 22:33 GMT (minutos antes da minha medição); `votacao_candidato_munzona_2026.zip` 20:15; `prestacao_de_contas_..._candidatos_2026.zip` 07:35. Já os de **2024 também foram regenerados hoje**: `consulta_cand_2024` 05:24, `bem_candidato_2024` 05:24, `votacao_candidato_munzona_2024` 05:28, `prestacao_de_contas_..._candidatos_2024` 02:56. Em contraste, `votacao_secao_2024_TO.zip` é de 2026-10-29 e o boletim de urna de 2026 (AC, 1º turno) de 2026-10-06. Conclusão (inferência, um dia só): os pacotes principais são regenerados **no mesmo nome de arquivo, várias vezes por dia ou por dia**, mesmo para eleições encerradas.
- **`Cache-Control: max-age`** de 2.139 s a 43.200 s, variando por arquivo (medido).
- **Dentro dos dados** cada linha traz `DT_GERACAO` e `HH_GERACAO` (medido), e o portal manda ler a "data de geração" ao importar (documentação, página "Sobre").

## Termos de uso e licença
- **Licença declarada no CKAN (medido, metadado `license_id`):** `cc-by` (Creative Commons Attribution), com `license_url` apontando para <http://www.opendefinition.org/licenses/cc-by>. Presente em 14 de 16 conjuntos de 2026 e 15 de 16 de 2024. **Sem licença declarada:** 2026: `resultados-2026-logs-...-gedai-2-turno` e `comparecimento-e-abstencao-2026`; 2024: `comparecimento-e-abstencao-2024`.
- **Texto do portal (documentação, <https://dadosabertos.tse.jus.br/about>):** "Os arquivos fornecidos podem ser importados para qualquer programa estatístico, base de dados ou planilha eletrônica. Consultas, filtros e cruzamentos são de responsabilidade da pessoa interessada em analisar os dados." E: "Estão incompletos os dados de candidatos e de resultados das eleições de 1994 a 1998, pois os mesmos não foram completamente centralizados nas bases no TSE."
- **Diferença em relação às outras duas fontes:** é a única das três com **licença nomeada** (CC BY) nos metadados. A CC BY exige **atribuição**, na mesma linha da exigência de "citar a fonte" do Senado. A Câmara não declara atribuição.

**Leitura de 2026-11-06:**
- `package_show` de `comparecimento-e-abstencao-2026` e `-2024` (medido): `license_id` e `license_title` **vazios**, `isopen: false`, sem `license_url` nem `license_notes`; as `notes` são só um aviso de software para abrir arquivos grandes. Ambos são dados agregados ("Perfil de comparecimento e abstenção"), área gestora CGE.
- `https://dadosabertos.tse.jus.br/dataset/` (medido): o filtro de licenças mostra um único item, "Creative Commons Atribuição - 181", de 190 conjuntos no portal inteiro. Ou seja, **9 conjuntos do portal não têm licença**. Identificados por `package_search` (medido, 2026-11-06, `rows=1000`, 190 retornados: 181 `cc-by`, 9 vazios): `comparecimento-e-abstencao-2022`, `-2024` e `-2026`; `resultados-eleicoes-suplementares-2022` e `-2024`; `resultados-2020-suplementares`; `mesarios-2022`; `correspondencia-entre-numero-interno-e-modelo-da-urna-1`; e `resultados-2026-logs-do-sistema-de-preparacao-das-urnas-eletronicas-gedai-2-turno`.
- `/about` (documentação): chama a Portaria 93/2021 de "Política de Dados Abertos do Tribunal Superior Eleitoral" e aponta "Termos de uso e privacidade" em `http://www.tse.jus.br/transparencia/politica-de-privacidade-e-termos-de-uso`; o Plano de Dados Abertos 2021-2023 está em `https://www.tse.jus.br/hotsites/catalogo-publicacoes/pdf/plano-dados-abertos-2021-2023.pdf`. Não abri esses dois links.

- **CPF de 2026 reconferido (medido, 2026-11-06, `consulta_cand_2026.zip`, só classe de formato):** 29 CSVs com `NR_CPF_CANDIDATO`; 42.028 linhas com 11 dígitos e 6 linhas com 2 caracteres não numéricos (placeholder). Ou seja, o CPF de 2026 continua preenchido em todas as UFs, mudando de 2024 (constante de 2 caracteres). Total de 42.034 linhas, igual ao medido na Sessão 17. Arquivo apagado.
- **`leiame.pdf` do `consulta_cand_2026.zip` (documentação, lido em 2026-11-06 com `pdftotext`; 208 KB, 1 dos 30 itens do ZIP):**
  - Codificação "Latin 1", campos entre aspas com `;`. `#NULO` (numérico: `-1`) é branco no banco; `#NE` (numérico: `-3`) é informação não registrada naquele ano. O campo UF pode ser `BR` (nacional), `VT` (voto em trânsito) ou `ZZ` (exterior). Coerente com o que o leitor já trata.
  - "Os arquivos estão em constante processo de atualização": alguns podem estar em branco ou com mensagem de erro por indisponibilidade temporária de um estado.
  - **CPF:** cita o § 2º do art. 33 da Resolução TSE nº 23.609/2019 (incluído pela Resolução nº 23.729/2024): endereços, telefone e e-mail pessoais, "número do CPF e o documento pessoal de identificação **não serão divulgados** no DivulgaCandContas". E conclui: "são considerados como não divulgáveis, para as Eleições 2024, as informações registradas na variável `NR_CPF_CANDIDATO` dos arquivos de candidaturas do Portal de Dados Abertos". É o que explica o CPF constante de 2 caracteres em 2024.
  - **Candidatos não divulgáveis:** seus dados pessoais vêm como `-4` (numérico), `"NÃO DIVULGÁVEL"` (texto) ou vazio (idade).
  - Não traz licença, atribuição ou termos de reuso.
- **Contradição a registrar (medido + documentação):** o `leiame.pdf` de 2026 ainda fala em "Eleições 2024" e diz que o CPF não é divulgável, mas o CSV de 2026 traz o CPF de 11 dígitos em 42.028 linhas. Não sei se a regra mudou para 2026, se o `leiame` está desatualizado ou se o TSE publicou o CPF por engano. Inferência: as 6 linhas de 2 caracteres não numéricos são o `-4` dos "não divulgáveis". Em qualquer hipótese, a regra do ADR 0005 (descartar o CPF na leitura) está certa, e o `NR_CPF_CANDIDATO` não deve ser tratado como dado que o TSE autorizou publicar.

**Não verificado:**
- **Texto das Portarias TSE nº 93/2021 e nº 525/2021:** as duas URLs de `www.tse.jus.br` devolveram HTTP 403 também na leitura de hoje. Uma tentativa minha de contornar o 403 com outro `User-Agent` foi barrada pelo ambiente e **não deve ser repetida**: o 403 é uma recusa do servidor. Para ler, é preciso abrir pelo navegador, ou o dono colar o texto.
- Termos de uso do portal e Plano de Dados Abertos (links acima, não abertos).
- O `leiame.pdf` dos outros ZIPs (li só o de `consulta_cand_2026`); a Resolução TSE nº 23.609/2019 em si (só o trecho citado pelo `leiame`).
- Se a CC BY vale para os conjuntos sem `license_id` (inferência: não herdam; a ausência é de metadado, não de decisão conhecida).
- Restrições específicas sobre dados pessoais. O que isso implica para o polis é interpretação jurídica (P-16).

## Restrições de armazenamento, transformação e redistribuição
Nenhuma declarada além da licença acima. Ausência de restrição declarada não é autorização verificada: PRD §8.2. Ver "Dados pessoais".

## Regras operacionais (decisão de engenharia, não parecer jurídico)
| Tema | Regra proposta | Base |
|---|---|---|
| Atribuição | Citar "TSE, Portal de Dados Abertos" e a licença CC BY em toda tela e exportação com dado de conjunto `cc-by` | CC BY (medido, metadado) |
| Conjuntos sem licença | **Não coletar** os 9 conjuntos sem `license_id` (lista na seção "Termos de uso e licença") até o P-16 ou até o TSE declarar licença; checar `license_id` por conjunto antes de habilitar um `Dataset` | medido |
| Taxa | Série, pausa de 3 s entre requisições (como nas medições), sem paralelismo; limite do CDN desconhecido | medido |
| Leitura | `Range` para o índice do ZIP; arquivos de até 1,36 GB: leitura em fluxo, nunca em memória inteira | medido |
| Janela | Arquivos regenerados várias vezes ao dia com o mesmo nome: usar SHA-256 do conteúdo (e `DT_GERACAO`) para saber se mudou, não só `Last-Modified` | medido |
| Codificação | ISO-8859-1, CRLF, `;`: já tratado pelo leitor (`apps/sources/zip_csv.py`) | medido |
| Dado pessoal | CPF, título, nascimento, cor/raça só pela allowlist do ADR 0005; nenhuma coluna fora dela é gravada | ADR 0005 |
| Armazenamento e redistribuição | CC BY permite com atribuição; o dado pessoal dentro do conjunto não é coberto por essa conclusão: P-16 | PRD §8.2 |

## Conjuntos e volumes (medido, 2026-11-05)
O CKAN lista 16 conjuntos por ano (2026 e 2024), cada um com dezenas ou centenas de recursos (um por UF, turno ou tipo):

| Conjunto (2026) | Recursos | Formatos |
|---|---|---|
| candidatos | 92 | CSV, JPEG, PDF |
| prestação de contas eleitorais | 7 | CSV, TXT |
| prestação de contas partidárias | 2 | CSV |
| resultados | 63 | CSV, PDF |
| resultados: boletim de urna | 112 | CSV (em ZIP) e hash |
| resultados: arquivos transmitidos para totalização | 56 | ZIP |
| resultados: correspondências esperadas e efetivadas (1º e 2º turno) | 168 cada | CSV |
| resultados: logs do sistema de preparação das urnas (1º e 2º turno) | 112 cada | ZIP |
| eleitorado | 33 | CSV |
| comparecimento e abstenção | 3 | CSV |
| mesários | 2 | CSV |
| pesquisas eleitorais | 6 | CSV, PDF |
| processual | 5 | CSV |
| denúncias eleitorais | 1 | CSV |

Tamanho dos ZIPs (medido, `HEAD`; o campo `size` do CKAN vem **vazio**, então só o CDN informa):

| Arquivo | 2026 | 2024 |
|---|---|---|
| `consulta_cand` (candidatos) | 3,3 MB | 64,7 MB |
| `bem_candidato` (bens) | 3,8 MB | 44,3 MB |
| `votacao_candidato_munzona` | 421,0 MB | 48,2 MB |
| `prestacao_de_contas_eleitorais_candidatos` | 325,3 MB | **1.362,2 MB** |
| boletim de urna (AC, 1º turno) | 17,0 MB | (não medido) |
| `votacao_secao_<UF>` (TO) | (não medido) | 10,2 MB |

Os ZIPs de candidatos têm 28 a 30 itens (um CSV por UF, mais `leiame.pdf`). O de prestação de contas de candidatos de 2024 tem 112 itens (despesas pagas e contratadas por UF, entre outros); o tamanho descomprimido total **não foi somado**. O volume de 2026 reflete uma eleição geral ainda em andamento e é menor que o de 2024 em candidatos, mas maior em votação; não investiguei o motivo.

## Esquemas (medido, só nomes de colunas)
- **`consulta_cand` (candidatos), 50 colunas, igual em 2026 e 2024:** `DT_GERACAO, HH_GERACAO, ANO_ELEICAO, CD_TIPO_ELEICAO, NM_TIPO_ELEICAO, NR_TURNO, CD_ELEICAO, DS_ELEICAO, DT_ELEICAO, TP_ABRANGENCIA, SG_UF, SG_UE, NM_UE, CD_CARGO, DS_CARGO, SQ_CANDIDATO, NR_CANDIDATO, NM_CANDIDATO, NM_URNA_CANDIDATO, NM_SOCIAL_CANDIDATO, NR_CPF_CANDIDATO, DS_EMAIL, CD_SITUACAO_CANDIDATURA, DS_SITUACAO_CANDIDATURA, TP_AGREMIACAO, NR_PARTIDO, SG_PARTIDO, NM_PARTIDO, NR_FEDERACAO, NM_FEDERACAO, SG_FEDERACAO, DS_COMPOSICAO_FEDERACAO, SQ_COLIGACAO, NM_COLIGACAO, DS_COMPOSICAO_COLIGACAO, SG_UF_NASCIMENTO, DT_NASCIMENTO, NR_TITULO_ELEITORAL_CANDIDATO, CD_GENERO, DS_GENERO, CD_GRAU_INSTRUCAO, DS_GRAU_INSTRUCAO, CD_ESTADO_CIVIL, DS_ESTADO_CIVIL, CD_COR_RACA, DS_COR_RACA, CD_OCUPACAO, DS_OCUPACAO, CD_SIT_TOT_TURNO, DS_SIT_TOT_TURNO`.
- **`bem_candidato` (bens), 19 colunas (2026):** `DT_GERACAO, HH_GERACAO, ANO_ELEICAO, CD_TIPO_ELEICAO, NM_TIPO_ELEICAO, CD_ELEICAO, DS_ELEICAO, DT_ELEICAO, SG_UF, SG_UE, NM_UE, SQ_CANDIDATO, NR_ORDEM_BEM_CANDIDATO, CD_TIPO_BEM_CANDIDATO, DS_TIPO_BEM_CANDIDATO, DS_BEM_CANDIDATO, VR_BEM_CANDIDATO, DT_ULT_ATUAL_BEM_CANDIDATO, HH_ULT_ATUAL_BEM_CANDIDATO`.
- **Despesas pagas de candidatos (prestação de contas 2024), 28 colunas:** `DT_GERACAO, HH_GERACAO, AA_ELEICAO, CD_TIPO_ELEICAO, NM_TIPO_ELEICAO, CD_ELEICAO, DS_ELEICAO, DT_ELEICAO, ST_TURNO, TP_PRESTACAO_CONTAS, DT_PRESTACAO_CONTAS, SQ_PRESTADOR_CONTAS, SG_UF, DS_TIPO_DOCUMENTO, NR_DOCUMENTO, CD_FONTE_DESPESA, DS_FONTE_DESPESA, CD_ORIGEM_DESPESA, DS_ORIGEM_DESPESA, CD_NATUREZA_DESPESA, DS_NATUREZA_DESPESA, CD_ESPECIE_RECURSO, DS_ESPECIE_RECURSO, SQ_DESPESA, SQ_PARCELAMENTO_DESPESA, DT_PAGTO_DESPESA, DS_DESPESA, VR_PAGTO_DESPESA`. Note que o ano se chama `ANO_ELEICAO` num conjunto e `AA_ELEICAO` em outro.

## Identificadores oficiais (medido, só nomes)
`SQ_CANDIDATO` (sequencial do candidato), `NR_CANDIDATO` (número de urna), `CD_ELEICAO`, `SG_UE`/`NM_UE` (unidade eleitoral), `SQ_PRESTADOR_CONTAS`, `SQ_DESPESA`, `NR_DOCUMENTO`. Não verifiquei a estabilidade de `SQ_CANDIDATO` entre ciclos nem se candidatos recorrentes têm uma chave de pessoa única (a coluna `NR_CPF_CANDIDATO`, quando publicada, serviria; ver abaixo).

## Dados pessoais (medido, só formato e agregado)
Método: ler por `Range` o índice do ZIP e o começo do primeiro CSV, em memória, e classificar o **formato** de cada coluna sensível (dígitos, comprimento, presença de `@`, placeholder), sem imprimir valores. Amostras: `consulta_cand_2026_AM.csv` (479 linhas, o arquivo inteiro) e `consulta_cand_2024_TO.csv` (4.619 linhas, 64% do arquivo).

| Coluna | 2026 (AM, 479 linhas) | 2024 (TO, 4.619 linhas) |
|---|---|---|
| `NR_CPF_CANDIDATO` | **11 dígitos em 479/479; 479/479 passam na verificação dos dígitos de CPF; 474 valores distintos** | texto **constante de 2 caracteres**, 1 valor distinto; 0/4.619 passam na verificação (não é CPF) |
| `NR_TITULO_ELEITORAL_CANDIDATO` | 12 dígitos em 479/479 | 12 dígitos em 4.619/4.619 |
| `DT_NASCIMENTO` | `dd/mm/aaaa` em 479/479 | `dd/mm/aaaa` em 4.619/4.619 |
| `DS_EMAIL` | texto de 14 caracteres em todas, **nenhuma com `@`** | idem (14 caracteres, nenhuma com `@`) |

Leitura:
- **Em 2026 o CPF completo e válido de cada candidato está no CSV aberto; em 2024 não está** (constante). O esquema de 50 colunas é o mesmo, então um conector que só olha o esquema **não percebe** a diferença. Não sei por que mudou (política, falha de processamento, ou o arquivo ser regenerado várias vezes ao dia): é um achado de uma única medição, e vale reconferir antes de qualquer decisão.
- O **título de eleitor** (12 dígitos) vem completo nos dois ciclos.
- `DS_EMAIL` parece ser um texto fixo de não divulgação (inferência: 14 caracteres iguais em todas as linhas, sem `@`); não confirmei o conteúdo.
- Presentes também: nome do candidato, nome social, data de nascimento, gênero, grau de instrução, estado civil, **cor/raça** e ocupação. A LGPD (Lei 13.709/2018, art. 5º, II) trata origem racial ou étnica como dado pessoal sensível; o que isso implica para o polis é interpretação jurídica (P-16).
- **Bens** (`bem_candidato`): descrição livre e valor por bem. **Prestação de contas**: `NR_DOCUMENTO` (documento do fornecedor, que pode ser CPF/CNPJ) e valores. Não examinei esses conteúdos.

**Para o P-12 (retenção) e o P-16 (LGPD):** a decisão que o TSE força é *quais colunas o polis ingere e guarda*, não só quais ele exibe. Registro como pendência; não decido.

## Preenchimento (medido, só percentual, mesma amostra)
`consulta_cand`, de 50 colunas: 47 colunas com **100%** de preenchimento nos dois ciclos. Exceções: `NR_FEDERACAO` 23% (2026) e 13% (2024); `CD_SIT_TOT_TURNO` 95% e 96%; `CD_SITUACAO_CANDIDATURA` **0%** nos dois (só valores nulos/`-1`/`-3`, embora `DS_SITUACAO_CANDIDATURA` venha 100%). **Limite do método:** "preenchido" aqui é "diferente de vazio, `#NULO#`, `#NE#`, `-1` e `-3`". Textos de não divulgação (como o `DS_EMAIL`) contam como preenchidos, então 100% não significa dado real. As amostras são as primeiras linhas de uma UF, não representam o conjunto.

## Problemas conhecidos e limitações
- **Conteúdo de uma coluna muda entre ciclos sem mudar o esquema** (CPF, acima).
- **Nomes de arquivo estáveis, conteúdo regenerado várias vezes ao dia**, sem versão no nome (medido: `Last-Modified` de hoje em arquivos de 2024 e 2026). Detectar mudança exige `ETag`/`Last-Modified` ou o par `DT_GERACAO`/`HH_GERACAO`.
- **Codificação ISO-8859-1 e CRLF** (um conector que assume UTF-8 corrompe acentos). **Conferido em 2026-11-06** em `consulta_cand_2026.zip` (3,3 MB, 29 CSVs, 23,7 MB descomprimidos), só contagens: 0 bytes entre `0x80` e `0x9F` (os que distinguiriam Windows-1252), 548.590 bytes `≥ 0xA0` (acentos), nenhum BOM UTF-8, nenhum item decodifica como UTF-8 válido, e as 42.063 quebras de linha são todas CRLF. Coerente com ISO-8859-1 (e com Windows-1252, que só difere naquela faixa). Vale para esse arquivo de 2026, não para os demais conjuntos nem para 2024.
- **Placeholders em texto** (`#NULO#`, `#NE#`, `-1`, `-3`) no lugar de vazio.
- **ZIPs grandes** (até 1,36 GB num único arquivo de 2024) e um item por UF.
- **CKAN sem tamanho** (`size` vazio).
- **Nomes inconsistentes** entre conjuntos (`ANO_ELEICAO` e `AA_ELEICAO`).
- **403 em `www.tse.jus.br`** para cliente automatizado.
- **Dados de 1994 a 1998 incompletos** (documentação).
- **Conjunto de 2026 em andamento:** a prestação de contas e os resultados de 2026 ainda mudam.

## Insumos para o P-02 (sem decidir)
Comparação com as outras duas fontes:

| | Câmara | Senado | TSE |
|---|---|---|---|
| Canal principal | API + arquivos anuais | API (sem paginação) | **arquivos ZIP em CDN**; API só de metadados |
| Volume maior medido | arquivo anual de dezenas de MB | respostas de ~130 KB | **até 1,36 GB por arquivo** |
| Limite de taxa | não documentado | 10 req/s documentado | não documentado |
| Atualização | arquivos regenerados de madrugada | cache de minutos | **regenerados várias vezes ao dia**, mesmo nome |
| Licença nomeada | não | não | **CC BY (nos metadados)** |
| Dado pessoal sensível no aberto | nome civil e nascimento | não examinado | **CPF (2026), título, nascimento, cor/raça** |

- O TSE é o único dos três que **pede pipeline de arquivos grandes**: leitura em fluxo (streaming), `Range`, ZIP com muitos itens, ISO-8859-1. Isso pesa em P-05 (banco) e P-07 (armazenamento de documentos) mais do que Câmara e Senado.
- Sem API de consulta, a "sincronização incremental" é recarga por conjunto e comparação de conteúdo.
- O dado pessoal sensível aberto exige uma decisão de minimização **antes** de desenhar o schema (P-12, P-16).

## Reproduzir as medições
Use um `User-Agent` genérico e espere alguns segundos entre as requisições. Os números de tamanho e a hora de `Last-Modified` mudam quando o TSE regenera os arquivos.
```bash
P=https://dadosabertos.tse.jus.br/api/3/action
curl -sS -G "$P/package_search" --data-urlencode 'fq=tags:"Ano 2026"' --data-urlencode rows=0 \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["result"]["count"])'            # 16
curl -sS -I https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_2024_TO.zip \
  | grep -iE '^(content-length|last-modified|accept-ranges)'                                # 10175412, 29 Oct 2026, bytes
# Formato das colunas sensíveis (só classes, sem valores); baixa 3,3 MB:
curl -sS -o c26.zip https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip
python3 -I -c "import zipfile,sys;sys.stdout.buffer.write(zipfile.ZipFile('c26.zip').read('consulta_cand_2026_AM.csv'))" \
  | iconv -f latin1 -t utf8 \
  | awk -F';' 'NR>1{v=$21; gsub(/"/,"",v); k=length(v) (v ~ /^[0-9]+$/ ? " dígitos" : " não-dígitos"); n[k]++} END{for(k in n) print "NR_CPF_CANDIDATO:", k, n[k]}'
# esperado em 2026-11-05: "NR_CPF_CANDIDATO: 11 dígitos 479" (a coluna 21 é NR_CPF_CANDIDATO; mude para 38 e vem o título, 12 dígitos)
```
A medição de 2024 (CPF constante de 2 caracteres) foi feita lendo o fim e o começo do ZIP de 64,7 MB por `Range`, com um script descartável não versionado; para reproduzir sem ele, baixe o ZIP inteiro e use o mesmo `awk` sobre `consulta_cand_2024_TO.csv`.

## Estado da integração
Nenhuma. Histórico de sincronizações: não se aplica ainda.

## Ainda não medido nesta rodada
Se o CPF de 2026 aparece em todas as UFs e se continua assim depois de novas gerações; o conteúdo e a cobertura de bens, doações, fornecedores e extratos bancários; os arquivos de eleitorado, boletim de urna (conteúdo), resultados (conteúdo) e pesquisas eleitorais; o `leiame.pdf`; as Portarias 93/2021 e 525/2021; outros canais do TSE (resultados em tempo real, DivulgaCand); DataStore do CKAN; limite real por IP ou por taxa; contagem total de linhas por arquivo; tamanho descomprimido total dos pacotes; eleições anteriores a 2024.
