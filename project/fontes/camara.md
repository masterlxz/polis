# Fonte: Câmara dos Deputados (Dados Abertos)

Campos do PRD §8.1. Rótulos de origem: ver [README.md](README.md). Medições feitas em **2026-11-05**, a partir das 22:05 GMT, de uma única máquina e sem paralelismo (latências dependem da minha rede). Versão da API no momento: `0.4.349 - 11/05/2026` (declarada na própria especificação).

## Identificação
- **Instituição:** Câmara dos Deputados. Serviço "Dados Abertos" (existe desde 2006; versão atual lançada em 2017). Fonte: FAQ (documentação).
- **Portal:** <https://dadosabertos.camara.leg.br/>
- **Documentação técnica:** <https://dadosabertos.camara.leg.br/swagger/api.html> e a especificação OpenAPI 3.0.1 em <https://dadosabertos.camara.leg.br/api/v2/api-docs> (medido: 200, JSON, 194 KB, 78 caminhos).
- **FAQ (termos práticos):** <https://dadosabertos.camara.leg.br/faq/faq-home.html>

## Tipo de acesso
Dois caminhos (medido):
1. **API REST**, base `https://dadosabertos.camara.leg.br/api/v2`, método GET (e HEAD, segundo a documentação).
2. **Arquivos em massa**, `https://dadosabertos.camara.leg.br/arquivos/<conjunto>/<formato>/<conjunto>[-<ano>].<formato>`. A especificação lista 32 conjuntos (deputados, proposições, proposicoesAutores, proposicoesTemas, votações, votacoesVotos, votacoesOrientacoes, votacoesObjetos, votacoesProposicoes, eventos, órgãos, frentes, grupos, legislaturas, licitações e outros).

## Formatos
- **API:** JSON e XML (documentação). Medido apenas JSON (`Accept: application/json`).
- **Arquivos:** CSV, JSON e XLSX existem (medido, via `HEAD`). XML e ODS: não verificado.
- **CSV de deputados (medido):** UTF-8 com BOM, separador `;`, campos entre aspas, 13 colunas (`uri, nome, idLegislaturaInicial, idLegislaturaFinal, nomeCivil, cpf, siglaSexo, urlRedeSocial, urlWebsite, dataNascimento, dataFalecimento, ufNascimento, municipioNascimento`). **Não há coluna `id`**: o identificador está no fim da `uri`.
- **Discursos (documentação, FAQ):** o texto vem em RTF (Windows-1252) codificado em Base64.

## Autenticação
Nenhuma. O FAQ diz que não há cadastro nem identificação (documentação), e todas as chamadas abaixo foram feitas sem credencial (medido).

## Limites de requisição
- **Documentado:** listagens retornam 15 itens por padrão; limite de **100** por requisição. Nenhum limite de taxa (requisições por tempo) documentado.
- **Medido:** `itens=100` funciona (200). `itens=101` (acima do limite documentado) respondeu **504 após 15,2 s**, com corpo de texto simples `upstream request timeout`, e não um erro de validação (uma única tentativa; não repeti).
- **Medido:** todas as respostas, inclusive as 200, trazem o cabeçalho `retry-after: 30`. O significado não é documentado; não é um 429. Não sei se há limitação por taxa.
- **Não verificado:** comportamento sob volume (não testei de propósito, por etiqueta com um serviço público).

## Frequência de atualização
- **Arquivos em massa (medido):** em 2026-11-05, os arquivos consultados tinham `Last-Modified` entre 04:00 e 07:06 GMT do mesmo dia, **inclusive de anos já encerrados** (`votacoes-2025`, `proposicoes-1990`). Inferência: são regenerados diariamente, de madrugada, mesmo sem mudança nos dados. Não confirmei por mais de um dia.
- **API (medido):** `Cache-Control: public, max-age=1800` em `/deputados`, `max-age=360` em `/proposicoes`. Sem `ETag` nem `Last-Modified` nas respostas JSON observadas. Há registros de hoje nas listagens (votação de 2026-11-05T15:51:53).

## Termos de uso e licença
Texto do FAQ (documentação, <https://dadosabertos.camara.leg.br/faq/faq-home.html>), transcrito:
- "É totalmente de graça — os dados são públicos! E não, não é preciso se cadastrar, nem se identificar para baixar qualquer dos conjuntos de dados."
- "Posso cobrar por um aplicativo ou serviço que use os dados da Câmara? Sim, pode. Não há qualquer restrição quanto ao isso. Mas se você puder tornar pública pelo menos uma pequena parte do resultado do seu trabalho, seria uma honrosa retribuição à sociedade!"
- "Os dados abertos incluem as informações pessoais de parlamentares e colaboradores? Não, pelo menos por enquanto. Existem restrições às informações que podem ser divulgadas, especialmente as de caráter pessoal e/ou familiar. O Ato da Mesa 45/2012 é atualmente o principal dos marcos regulatórios da Câmara que definem quais informações podem ser tornadas públicas ou não."
- Marcos citados no FAQ: Lei 12.527/2011 (Lei de Acesso à Informação) e Ato da Mesa 45/2012.

**Leitura de 2026-11-06 (documentação):** reli `https://dadosabertos.camara.leg.br/`, o FAQ e `https://dadosabertos.camara.leg.br/swagger/api.html`: nenhuma menção a Creative Commons, ODbL, domínio público, regra de atribuição, limite de requisições ou termos de uso. `www2.camara.leg.br/transparencia/dados-abertos` redireciona (302) para `dadosabertos.camara.leg.br`, então não há página institucional separada. A página de metadados do Ato da Mesa 45/2012 traz só a ementa ("Dispõe sobre a aplicação, no âmbito da Câmara dos Deputados, da Lei de Acesso à Informação") e "Não consta revogação expressa".

**Ato da Mesa 45/2012, texto atualizado (documentação, lido em 2026-11-06 depois de um 429 anterior, com uma nova requisição de User-Agent genérico):** `http://www2.camara.leg.br/legin/int/atomes/2012/atodamesa-45-16-julho-2012-773823-normaatualizada-cd-mesa.html`. O Art. 27 (com redação dada pelo Ato da Mesa nº 246/2018) trata das informações pessoais:
- **§ 1º lista, "entre outros", como informações pessoais:** nome de cônjuge ou companheiro e parentes até o 4º grau; endereço de residência, e-mail particular e telefone particular; **número de documentos de identificação pessoal**; identificadores de contratos de telecomunicações reembolsáveis; dados de reembolso médico-hospitalar; informações médicas; descontos facultativos ou judiciais sobre remuneração; **informações patrimoniais e financeiras**; dados biométricos.
- **§ 2º:** quando relativas à intimidade, vida privada, honra e imagem, têm acesso restrito por até 100 anos.
- **§ 4º e § 6º:** quem obtém acesso responde pelo uso indevido; o acesso de terceiros "vincula-se à finalidade e à destinação" e exige termo de responsabilidade.
- **§ 8º:** o interesse público preponderante se caracteriza, entre outros, quando a informação é "decorrente de investidura em cargo ou função pública" ou "vinculada a atos e documentos atinentes ao exercício da atividade legislativa".
- O Ato é sobre **acesso** a informação pela Câmara (aplicação da LAI); **não** fala de licença nem de reuso por terceiros dos dados abertos. Isso é leitura minha do texto.

**Termos de uso e política de privacidade do portal (documentação, lido em 2026-11-06):** `https://www2.camara.leg.br/termo-de-uso-e-politica-de-privacidade`. É voltado a quem se cadastra e usa o portal (cadastro, senha, comentários). Não cita dados abertos, licença, atribuição ou reuso. Único ponto técnico: "Podemos coibir a participação de sistemas automatizados ou robôs (scripts, bots, entre outros) que tentem **imitar pessoas**" (item 22). Não é o caso de um coletor que se identifica como tal; a aplicação à API é interpretação (P-16).

**Conclusão:** depois de ler tudo o que a Câmara publica sobre o tema, a Câmara continua **sem licença nem atribuição declaradas**. O que existe é o FAQ (uso, inclusive comercial, sem restrição) e o Art. 27 do Ato, que limita as informações pessoais. O CPF de deputado (que a API de detalhe traz) cai em "número de documentos de identificação pessoal" no § 1º, III; o § 8º não o torna público por si só. Isso reforça a regra do ADR 0005 de não coletar o CPF. Interpretação jurídica é do P-16.

**Não verificado:** a aplicação do Art. 27 ao CPF que a API devolve no detalhe do deputado (por que a Câmara o serve, se o Ato o lista como pessoal); o regulamento do § 10.

## Restrições de armazenamento, transformação e redistribuição
Nenhuma sobre reuso declarada no FAQ nem nos termos do portal (documentação). As restrições existentes são sobre **informações pessoais** (Art. 27 do Ato da Mesa 45/2012, acima). Ausência de restrição declarada não é autorização verificada: PRD §8.2.

## Regras operacionais (decisão de engenharia, não parecer jurídico)
| Tema | Regra proposta | Base |
|---|---|---|
| Atribuição | Citar "Câmara dos Deputados, Dados Abertos" mesmo sem exigência encontrada; o FAQ pede retribuição à sociedade | FAQ (documentação) |
| Taxa | Série, sem paralelismo; pausa entre requisições; respeitar `retry-after: 30` se vier em 429/503 | medido: `retry-after: 30` em todas as respostas, sem 429 |
| Tamanho de página | `itens` ≤ 100 (acima disso houve 504) | FAQ e medido |
| Canal | Arquivos anuais em massa para carga; API para detalhe e atualização incremental | medido |
| Janela | Arquivos regenerados de madrugada (04:00 a 07:00 GMT): coletar depois das 08:00 GMT | medido, um dia só |
| Dado pessoal | Só o que a allowlist do ADR 0005 permite; CPF vem no detalhe da API mas não no CSV em massa: não coletar o detalhe para obter CPF (o Ato da Mesa 45/2012, Art. 27 § 1º, III, lista documentos de identificação como informação pessoal) | ADR 0005; Ato da Mesa 45/2012 (documentação) |
| Robôs | Identificar o coletor com `User-Agent` próprio e honesto; os termos do portal só falam em sistemas que "imitem pessoas" | termos do portal, item 22 |
| Armazenamento e redistribuição | Sem restrição declarada; **não tratar como autorização** até o P-16 | PRD §8.2 |

## Entidades e campos (medido, listagens da API, 2026-11-05)
| Recurso | Campos de cada item da listagem |
|---|---|
| `/deputados` | `id, uri, nome, siglaPartido, uriPartido, siglaUf, idLegislatura, urlFoto, email` |
| `/proposicoes` | `id, uri, siglaTipo, codTipo, numero, ano, ementa, dataApresentacao` |
| `/votacoes` | `id, uri, data, dataHoraRegistro, siglaOrgao, uriOrgao, uriEvento, proposicaoObjeto, uriProposicaoObjeto, descricao, aprovacao` |
| `/legislaturas` | `id, uri, dataInicio, dataFim` |

Resposta de listagem: `{"dados": [...], "links": [...]}`; paginação por `pagina` e `itens`, com `X-Total-Count` e cabeçalho `Link` (`self`, `next`, ...). Recursos documentados (sem medir todos): deputados (e despesas, discursos, eventos, órgãos, frentes, histórico, mandatos externos, ocupações, profissões), proposições (autores, relacionadas, temas, tramitações, votações), votações (orientações, votos), eventos (pauta, deputados, órgãos, votações), órgãos, partidos, blocos, frentes, grupos, legislaturas e `/referencias/*` (27 caminhos).

## Identificadores oficiais (medido)
- Deputado: inteiro (ex.: `220593`), na `uri`. Cada deputado que exerceu mandato por um dia recebe um id exclusivo (documentação, portal).
- Proposição: inteiro (ex.: `2651254`).
- Votação: **texto** no formato `<número>-<número>` (ex.: `2641546-7`), não inteiro.

## Volumes (medido, 2026-11-05)
| O quê | Valor |
|---|---|
| `/deputados` | `X-Total-Count: 513` (página de 100: 35 KB). Páginas 1 e 2: 200 ids distintos. |
| `/proposicoes` (sem filtro) | `X-Total-Count: 15022`; página 151 (a última) traz itens de 2003 a 2007 |
| `/votacoes` (sem filtro de data) | `X-Total-Count: 1452`; item mais antigo observado: `2026-08-11T10:08:39` |
| `/legislaturas` | 57 itens (de 1826 a 2027) |
| `deputados.csv` | 1,3 MB; 7.889 linhas de dados, 7.889 `uri` distintas; legislaturas 1 a 57 |
| `proposicoes-2026` | CSV 42,3 MB; JSON 76,4 MB; XLSX 11,5 MB |
| `proposicoes-1990.csv` | 2,6 MB |
| `votacoes-2025.csv` | 8,8 MB |
| `votacoesVotos-2025.csv` | 58,2 MB |

Tempos de resposta (medido, uma amostra cada): `/deputados` 0,19 a 0,22 s; `/legislaturas` 0,5 s; `/votacoes` p.1 4,4 s e p.15 5,7 s; `/proposicoes` p.1 4,6 s e p.151 10,4 s; arquivo `deputados.csv` 0,45 s.

## Dados pessoais (medido, em agregado)
O CSV de deputados tem as colunas `cpf`, `nomeCivil` e `dataNascimento`. Em 7.889 linhas: `cpf` **vazio em todas**; `nomeCivil` preenchido em todas; `dataNascimento` em 7.004; `municipioNascimento` em 6.519; `dataFalecimento` em 4.359; `urlRedeSocial` em 567. Coerente com o FAQ, que diz não incluir informação pessoal de caráter restrito. Para o P-12 (retenção) e o P-16 (LGPD): o que fica público na fonte ainda inclui nome civil e data de nascimento.

## Problemas conhecidos e limitações
- **Aviso oficial:** a especificação diz que a versão "é ainda incompleta, sujeita a mudanças e não substitui a versão original do Dados Abertos". A página inicial traz alerta de mudança em `/eventos/{id}/pauta`. Implica: conector com versionamento de esquema (PRD §9.2).
- **`ano = 0` em proposições recentes (medido):** 62 dos 100 itens mais recentes de `/proposicoes` têm `ano: 0` (tipos como PRL, EMR, SBT, com `dataApresentacao` de 2026-11). Não usar `ano` como chave sem validar.
- **Escopo das listagens sem filtro (inferência):** `/votacoes` sem filtro de data parece cobrir só uma janela recente (o item mais antigo tem ~86 dias), e não o histórico. Para histórico, os arquivos por ano parecem o caminho. Não confirmei.
- **Paginação profunda é lenta** (10,4 s na página 151 de proposições).
- **Erro fora do padrão:** o 504 com texto simples (acima) quebra um parser que espera JSON de erro. Um 404 normal traz JSON com `status, title, detail, instance, code` e o cabeçalho `x-business-error: true` (medido).
- **Discursos** exigem decodificar Base64 e converter RTF (documentação).

## Insumos para o P-02 (sem decidir)
- A API serve consulta e sincronização por filtros de data; o arquivo em massa serve carga histórica. O volume de um ano (dezenas de MB) cabe em disco comum, mas um conector precisa tratar arquivos grandes sem carregá-los inteiros na memória.
- Sem `ETag` na API e com arquivos regenerados diariamente (inclusive anos fechados), detectar mudança exige comparar conteúdo ou `ETag`/`Last-Modified` dos arquivos, não só a data.
- Ids heterogêneos (inteiro e texto) pedem uma coluna de id de origem em texto.

## Rodada 2: detalhe do deputado e votos individuais (medido, 2026-11-05)
Complementa as seções acima. Só estrutura e contagens; nenhum valor individual foi impresso ou commitado.

**Detalhe `GET /deputados/{id}` (um deputado em exercício, n=1).** Campos: `id, uri, nomeCivil, cpf, sexo, urlWebsite, redeSocial[], dataNascimento, dataFalecimento, ufNascimento, municipioNascimento, escolaridade` e o bloco `ultimoStatus` (`id, uri, nome, siglaPartido, uriPartido, siglaUf, idLegislatura, urlFoto, email, data, nomeEleitoral, situacao, condicaoEleitoral, descricaoStatus` e `gabinete`: `nome, predio, sala, andar, telefone, email`).
- **`cpf` vem preenchido: 11 dígitos, e passa na verificação dos dígitos de CPF** (um deputado; não sei se vale para todos). No CSV em massa `deputados.csv` a mesma coluna está **vazia nas 7.889 linhas** (medido na rodada 1). Ou seja: o mesmo dado sai com tratamento diferente conforme o canal. O FAQ diz que os dados abertos não incluem informação pessoal de caráter restrito (documentação); não interpreto a divergência, só registro.
- `dataNascimento` em `aaaa-mm-dd`; `escolaridade`, `sexo` e `redeSocial` presentes; `ultimoStatus.email` vazio, mas `gabinete.email` e `gabinete.telefone` preenchidos (institucionais; não examinei o conteúdo).
- A listagem `GET /deputados` **não** traz esses campos (só `id, uri, nome, siglaPartido, uriPartido, siglaUf, idLegislatura, urlFoto, email`).

**Votos individuais pela API (não consegui medir).**
- `GET /votacoes/{id}/votos` de uma votação de plenário com objeto: **200 com lista vazia** (`dados: []`), provavelmente votação simbólica.
- `GET /votacoes/{id}/votos` de outra votação de plenário: **504 após cerca de 15 s, com corpo de texto simples** (`upstream request timeout`), **2 tentativas, 2 falhas** (a segunda após 20 s de pausa).
- `GET /votacoes/{id}/orientacoes`: **504 após cerca de 15 s**, 1 tentativa.
- Com o `itens=101` da rodada 1, são **quatro casos do mesmo 504** em chamadas diferentes. Para um conector: subrecursos de votação podem travar de forma repetível; é preciso timeout, retentativa limitada e tratamento de corpo que não é JSON.

**Votos individuais pelo arquivo em massa (`votacoesVotos-2025.csv`, 58,2 MB, lido por `Range` nos primeiros 250 KB).** UTF-8 com BOM, separador `;`, 12 colunas: `idVotacao, uriVotacao, dataHoraVoto, voto, deputado_id, deputado_uri, deputado_nome, deputado_siglaPartido, deputado_uriPartido, deputado_siglaUf, deputado_idLegislatura, deputado_urlFoto`. Nas 751 linhas da amostra (as primeiras do arquivo, enviesadas): 100% preenchidas; `voto` com os valores `Sim` (632), `Não` (117) e `Artigo 17` (2); outros valores, como abstenção ou obstrução, não apareceram e **não foram verificados**. Sem coluna de CPF nem de data de nascimento. Cada linha repete nome, partido, UF e foto do deputado, ou seja, é desnormalizada.

Reproduzir o CPF do detalhe (imprime só comprimento e se são dígitos; o `id` é público):
```bash
curl -sS -H 'Accept: application/json' https://dadosabertos.camara.leg.br/api/v2/deputados/204379 \
  | python3 -c 'import json,sys;c=json.load(sys.stdin)["dados"].get("cpf") or "";print("cpf: comprimento",len(c),"| só dígitos",c.isdigit())'
# esperado em 2026-11-05: cpf: comprimento 11 | só dígitos True
```

**Não verificado nesta rodada:** os campos de todos os deputados no detalhe (o CPF em mais de um); votos nominais pela API; `orientacoes`; a lista completa de valores de `voto`; discursos e despesas (despesas pertencem à Etapa 3, ADR 0005).

## Reproduzir as medições
Use um `User-Agent` genérico e espere alguns segundos entre as requisições.
```bash
B=https://dadosabertos.camara.leg.br/api/v2
curl -sS -D - -o /dev/null -H 'Accept: application/json' "$B/deputados?itens=100&pagina=1"   # X-Total-Count, Cache-Control, retry-after
curl -sS -I https://dadosabertos.camara.leg.br/arquivos/proposicoes/csv/proposicoes-2026.csv   # tamanho e Last-Modified
curl -sS "$B/api-docs" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["paths"]))'  # 78
```
O `itens=101` (504) não é para repetir sem necessidade.

## Estado da integração
Nenhuma. Histórico de sincronizações: não se aplica ainda.

## Ainda não medido nesta rodada
Taxa máxima aceita sem bloqueio; comportamento de `429` ou bloqueio por IP; XML e ODS; despesas, discursos e votos por deputado (volumes e custo); consistência entre a API e os arquivos para o mesmo registro; estabilidade dos ids ao longo do tempo; completude histórica.
