# Fonte: Senado Federal (Dados Abertos Legislativos)

Campos do PRD §8.1. Rótulos de origem: ver [README.md](README.md). Medições feitas em **2026-11-05**, depois das 22:14 GMT, de uma única máquina e sem paralelismo (latências dependem da minha rede). Versão da API no momento: `4.1.3.113` (declarada na especificação). Formato do registro igual ao da [Câmara](camara.md), para comparar.

## Identificação
- **Instituição:** Senado Federal (infraestrutura técnica: Prodasen, segundo a política de uso do portal).
- **Portal de dados abertos:** <https://www12.senado.leg.br/dados-abertos> (catálogo e plano de dados abertos).
- **API legislativa:** <https://legis.senado.leg.br/dadosabertos/> (redireciona para o Swagger UI). Especificação OpenAPI em <https://legis.senado.leg.br/dadosabertos/v3/api-docs> (medido: 200, JSON, 174 KB, 157 caminhos). A descrição da API diz abranger Senado e Congresso Nacional.
- **Catálogo de dados abertos em CSV:** <https://www12.senado.leg.br/dados-abertos/geracsv>
- **Política de uso do portal:** <https://www12.senado.leg.br/institucional/documentos/politica-de-uso-do-portal-do-senado-federal>
- **Plano de Dados Abertos 2026/2028:** link no portal (PDF); **não lido**.

## Tipo de acesso
1. **API REST** em `https://legis.senado.leg.br/dadosabertos/...` (medido).
2. **Catálogo** com 223 conjuntos de dados em duas categorias, Administrativo (80) e Legislativo (143), espalhados por vários hosts (medido, ver "Catálogo").
3. **Arquivos estáticos** pontuais, por exemplo `.../dadosabertos/arquivos/*.csv` e `.../dadosabertos/dados/*.zip` (medido em 4 exemplos). Não há, pelo que vi, o equivalente aos arquivos anuais da Câmara; não varri o catálogo inteiro para afirmar.

## Formatos
- **Documentação (especificação):** JSON, XML e CSV, escolhidos por cabeçalho `Accept` ou por sufixo (`.json`, `.xml`, `.csv`). NDJSON em 7 endpoints, iCal em 1.
- **Medido:** JSON (`Accept: application/json`) e CSV por sufixo (`/senador/lista/atual.csv`, `text/csv`, 188,5 KB).
- **Dois estilos de JSON convivem (medido):**
  - **Legado:** derivado do XML, aninhado, com envelope e metadados. Ex.: `/senador/lista/atual` devolve `ListaParlamentarEmExercicio` > `Metadados` (`Versao`, `VersaoServico`, `DataVersaoServico`, `DescricaoDataSet`) > `Parlamentares` > `Parlamentar`, com `noNamespaceSchemaLocation` apontando para um `.xsd`.
  - **Novo:** lista plana de objetos, sem envelope. Ex.: `/processo` e `/votacao`.

## Autenticação
Nenhuma. A descrição da API diz "acesso público, sem necessidade de autenticação" (documentação), e todas as chamadas foram feitas sem credencial (medido).

## Limites de requisição
- **Documentado (especificação):** "Mais de 10 requisições por segundo estão sujeitas a receber o erro HTTP 429"; evitar rotinas em horários redondos (00:00:00, 01:00:00, 01:15:00 etc.) para não gerar picos; em momentos de muita demanda as requisições estão sujeitas a **503**.
- **Documentado:** `/processo` exige ao menos um filtro (número, ano, idProcesso, codigoMateria, tramitando, e outros); `/votacao` exige ao menos um filtro, e o intervalo `dataInicio`+`dataFim` deve ser de até 1 ano.
- **Paginação:** pela especificação, só os endpoints de `comissao` têm `pagina`/`tamanho`. Os demais que medi (`/processo`, `/votacao`, `/senador/lista/atual`) devolvem tudo de uma vez (medido).
- **Medido:** nenhum 429 nem 503 ocorreu. Fiz cerca de 1 requisição a cada 3 s, muito abaixo do limite, então não sei como o 429 se comporta na prática (não testei de propósito). Nenhum cabeçalho `Retry-After` ou `RateLimit` nas respostas observadas.

## Frequência de atualização
- **API (medido):** `Cache-Control: max-age=` de 900 s (`/senador/lista/atual`), 1800 s (`/processo`), 600 s (`/votacao`), 300 s e 120 s em outros. Há cabeçalho `Age`, ou seja, existe cache de borda.
- **Catálogo (documentação, coluna `des_frequencia_atualizacao`, 223 conjuntos):** Diário 73, "A especificar" 77, On-line 28, Mensal 13, Anual 9, Quadrimestral 8, "Não especificada" 4, vazio 3. Mais de um terço dos conjuntos não declara a frequência.
- **Arquivos estáticos (medido, 4 exemplos):** `ComissoesMistasCongresso.csv` com `Last-Modified` de 2026-11-05 21:19 GMT e `tiposColegiado.csv` de 2026-11-05 17:19 GMT, enquanto `DocumentosSicon.zip` (reuniões anteriores a 2012) tem `Last-Modified` de 2021-11-18. Ou seja, alguns são regenerados no dia e outros são estáticos. Uma única data de medição.

## Termos de uso e licença
Textos oficiais (documentação), transcritos:
- **Política de uso do portal** (<https://www12.senado.leg.br/institucional/documentos/politica-de-uso-do-portal-do-senado-federal>): "Todo o conteúdo deste Portal é de propriedade autoral do Senado Federal, mas pode ser utilizado pelos usuários, desde que seja citada a fonte e para fins lícitos."
- Mesma política: "Este Portal deve ser usado apenas para propósitos legalmente amparados e seu uso não deve infringir, restringir ou inibir o uso por outras pessoas." Também proíbe ataques ao portal, "incluindo ataques do tipo DDoS".
- **Página de dados abertos** (<https://www12.senado.leg.br/dados-abertos>): "Dados Abertos são representados em meio digital, processáveis por máquina, referenciados na rede mundial de computadores e disponibilizados sob licença que permita sua livre utilização." É a definição geral; a página não nomeia uma licença.

**Diferença em relação à Câmara:** o Senado condiciona o uso a **citar a fonte**; o FAQ da Câmara não menciona atribuição.

**Não verificado:**
- Se a política do *portal* se aplica expressamente aos dados da API. A política fala em "conteúdo deste Portal"; a API fica em outro host (`legis.senado.leg.br`). Meu entendimento é que é a política mais próxima, mas é interpretação.
- Não há licença nomeada (por exemplo Creative Commons): o catálogo CSV não tem coluna de licença (medido).
- Nada sobre uso comercial: o Senado não diz nem que pode nem que não pode. A Câmara diz explicitamente que pode.
- A Lei de Acesso à Informação (LAI) não foi lida. Qualquer interpretação jurídica é do P-16.

**Leitura de 2026-11-06 (documentação):**
- `https://www12.senado.leg.br/dados-abertos/sobre`: define dados abertos como "exigindo-se, no máximo, citar sua proveniência". É definição geral, não licença do Senado.
- Plano de Dados Abertos 2026/2028 (`.../dados-abertos/pdf/plano-2026-2028-de-dados-abertos-do-senado-federal.pdf`, texto extraído com `pdftotext`): o glossário define dados abertos como "disponibilizados sob licença aberta que permita sua livre utilização, consumo ou cruzamento". **Não nomeia** licença nenhuma; busquei por licen*, creative, cc by, citar, proveni*, reutiliza*, atribui* e só esse trecho apareceu.
- A política de uso do portal fala só em "Portal do Senado Federal"; **não cita a API nem os dados abertos**, uso comercial ou limite numérico de requisições (a única restrição técnica é a proibição de ataques, incluindo DDoS).
- `https://legis.senado.leg.br/dadosabertos/docs/` é Swagger renderizado por JavaScript. Li a especificação que ele carrega (`/dadosabertos/v3/api-docs`, versão 4.1.3.113, medido em 2026-11-06): os campos `info.license`, `info.termsOfService`, `info.contact` e `externalDocs` são **nulos**. A descrição só traz formatos de saída, a "Restrição de requisições" (10 req/s, horários redondos, 503) e um aviso sobre a remodelagem dos sistemas. Ou seja, a API **não declara licença nem termos**.

**Conclusão (inferência):** a política do portal continua sendo a regra mais próxima, mas **nenhuma fonte lida a liga expressamente à API**. Licença nomeada: não encontrada. Uso comercial: não dito.

## Restrições de armazenamento, transformação e redistribuição
Nenhuma declarada além da política acima (citar a fonte, fins lícitos). Ausência de restrição declarada não é autorização verificada: PRD §8.2.

## Regras operacionais (decisão de engenharia, não parecer jurídico)
| Tema | Regra proposta | Base |
|---|---|---|
| Atribuição | Citar "Senado Federal, Dados Abertos Legislativos" em toda tela e exportação que use o dado (cumpre a política do portal e a definição de "citar proveniência") | política do portal (documentação) |
| Taxa | Bem abaixo de 10 req/s (ex.: 1 a cada 3 s, como nas medições); em 429/503, recuar e tentar mais tarde | especificação (documentação) |
| Horário | Não agendar em horários redondos (00:00, 01:00, 01:15 etc.); usar minuto aleatório | especificação (documentação) |
| Filtros | `/processo` e `/votacao` exigem filtro; `/votacao` com no máximo 1 ano por chamada | especificação (documentação) |
| Endpoints depreciados | Não construir sobre os 42 `deprecated` (quase todo o grupo `materia`) | medido |
| Armazenamento e redistribuição | Fins lícitos, citando a fonte; **uso comercial não dito**: não presumir até o P-16 | política do portal; PRD §8.2 |

## Entidades e campos (medido, 2026-11-05)
| Recurso | Forma | Campos de cada item |
|---|---|---|
| `/processo?sigla=PEC&ano=2026` | lista plana (14 itens, 23,6 KB) | `autoria, casaIdentificadora, codigoMateria, dataApresentacao, dataSituacaoAtual, dataUltimaAtualizacao, ementa, enteIdentificador, id, identificacao, objetivo, situacaoAtual, tipoConteudo, tipoDocumento, tramitando, ultimaInformacaoAtualizada, urlDocumento` |
| `/votacao?dataInicio=2026-10-01&dataFim=2026-10-31` | lista plana (3 itens, 55,6 KB) | `ano, casaSessao, codigoMateria, codigoSessao, codigoSessaoLegislativa, codigoSessaoVotacao, dataApresentacao, dataSessao, descricaoVotacao, ementa, idProcesso, identificacao, informeLegislativo, numero, numeroSessao, resultadoVotacao, sequencialSessao, sequencialVotacao, sigla, siglaTipoSessao, totalVotosAbstencao, totalVotosNao, totalVotosSim, votacaoSecreta, votos` (os `votos` vêm aninhados) |
| `/senador/lista/atual` | aninhado, estilo legado (81 senadores, 129,6 KB) | `Parlamentares.Parlamentar[].IdentificacaoParlamentar.*` (`CodigoParlamentar`, `CodigoPublicoNaLegAtual`, `NomeParlamentar`, `NomeCompletoParlamentar` etc.) |

Grupos de endpoints na especificação (157 caminhos, 42 depreciados): `materia` 39, `plenario` 25, `senador` 20, `processo` 18, `composicao` 16, `comissao` 14, `legislacao` 10, `taquigrafia` 4, `votacaoComissao` 3, `orcamento` 3, `discurso` 2, `autor` 2, `votacao` 1.

## Identificadores oficiais (medido)
Coexistem **dois sistemas de identificação**:
- **Novo:** `id` / `idProcesso` do processo legislativo, inteiro (ex.: `8986903`, para a `PEC 1/2026`).
- **Legado:** `codigoMateria`, inteiro (ex.: `172391`), "código legado da matéria do MATE" (documentação). A listagem de `/processo` devolve os dois ids no mesmo item (medido); a especificação diz que `/processo` aceita `codigoMateria` como filtro (documentação).
- Texto legível: `identificacao` (ex.: `PEC 1/2026`).
- Senador: `CodigoParlamentar`; há também `CodigoPublicoNaLegAtual`.
- Votação: `codigoSessaoVotacao`, `codigoSessao`, `sequencialVotacao`; não identifiquei um único id de votação.

## Catálogo (medido)
`geracsv`: 1,1 MB, UTF-8 com BOM, separador `;`, 2.230 linhas, 14 colunas (`nom_categoria, nom_sub_categoria, des_grupo_dados, cod_orgao_responsavel, nom_orgao_responsavel, nom_conjunto_dados, des_conjunto_dados, txt_url, des_frequencia_atualizacao, dth_ultima_atualizacao, nom_dicionario_dados, des_dicionario_dados, des_tipo_campo, num_ordem`). Cada linha parece ser um campo do dicionário de dados, e não um conjunto (inferência: 2.230 linhas para 223 conjuntos, e colunas `nom_dicionario_dados`, `des_tipo_campo`, `num_ordem`). Das linhas, **33 têm texto livre na coluna `nom_categoria`** (notas de rodapé, trechos de atos), ou seja, o CSV não é limpo.
URLs dos 223 conjuntos: 118 em `legis.senado.leg.br`, 40 em `www12.senado.leg.br`, 24 em `adm.senado.gov.br`, 14 em `legis.senado.gov.br`, 7 em `www.senado.leg.br` e 6 em `www.lexml.gov.br`. Por extensão: html 86, csv 60, xml 19, json 5, xlsx 1, zip 1, sem extensão 51. Muitos conjuntos apontam para uma página HTML e não para o dado.

## Tempos de resposta (medido, uma amostra cada)
API: 0,22 a 0,75 s (`/senador/lista/atual` 0,37 s; `/processo` 0,34 s; `/votacao` 0,75 s; versão `.csv` 1,7 s). A primeira requisição ao redirecionador `/dadosabertos/` levou **23 s** (uma amostra, não repeti).

## Dados pessoais
**Não medido em agregado nesta rodada.** Os endpoints de senadores (`/senador/{codigo}/...`: profissão, filiações, histórico acadêmico, licenças, cargos) sugerem dado pessoal e profissional público; não olhei o conteúdo. Fica para o P-12 e o P-16 antes de qualquer integração.

## Problemas conhecidos e limitações
- **Depreciação em massa (documentação e medido):** 42 de 157 endpoints estão `deprecated`, incluindo quase todo o grupo `materia`. A descrição da API diz que os serviços depreciados devolvem os cabeçalhos `Deprecation`, `Sunset` e `Link` (sucessor). Conector precisa de versionamento e plano de migração desde o início (PRD §9.2).
- **`Sunset` vencido e o serviço ainda responde (medido):** `GET /materia/172391` devolveu 200 com `Deprecation: Tue, 18 Mar 2025`, `Sunset: Sun, 01 Feb 2026` e `Link: <.../dadosabertos/processo/{idProcesso}>; rel="successor"`. A data de desativação passou há cerca de nove meses e o serviço continua no ar em 2026-11-05. Não dá para confiar na data como cronograma.
- **Código inexistente devolve 200 (medido):** `GET /senador/99999999` respondeu **200** só com os metadados (`DetalheParlamentar` sem dados), não 404. Um conector que confia no status HTTP trata "não existe" como "vazio".
- **Redirecionamento 301 em endpoint depreciado (medido):** `GET /materia/tiposNatureza` devolveu 301 para um arquivo estático (`.../dadosabertos/dados/ListaTiposNatureza.json`).
- **Dois estilos de JSON e dois sistemas de ids** (acima).
- **Catálogo sujo** e com muitos conjuntos sem frequência declarada.
- **Hosts diversos** para os conjuntos do catálogo.

## Insumos para o P-02 (sem decidir)
- Um limite documentado de taxa pede throttling no conector, bem abaixo de 10 req/s e fora de horários redondos, com tratamento de 429 e 503.
- Sem paginação nas listagens principais, a carga histórica se faz por filtros de data e processo, respeitando "intervalo de até 1 ano" nas votações. É um desenho diferente do da Câmara (arquivos anuais).
- Dois sistemas de ids (processo e matéria legada) e depreciação em curso pedem uma tabela de correspondência de ids e um id de origem em texto.
- A atribuição (citar a fonte) casa com o princípio de rastreabilidade do PRD, e custa pouco se o modelo já guarda a URL de origem.

## Rodada 2: senadores e votos individuais (medido, 2026-11-05)
Complementa as seções acima. Só estrutura e contagens; nenhum valor individual foi impresso ou commitado.

**Lista `GET /senador/lista/atual` (81 senadores em exercício).** `IdentificacaoParlamentar`: `CodigoParlamentar` (81/81), `CodigoPublicoNaLegAtual` (81/81), `NomeParlamentar` (81/81), `NomeCompletoParlamentar` (81/81), `SiglaPartidoParlamentar`, `UfParlamentar`, `SexoParlamentar`, `FormaTratamento`, `EmailParlamentar` (79/81), `Telefones` (149 entradas), `UrlFotoParlamentar`, `UrlPaginaParlamentar`, `UrlPaginaParticular` (18/81), `MembroMesa`, `MembroLideranca`, `Bloco` (80/81: código, nome, apelido, data de criação). `Mandato`: `CodigoMandato`, `DescricaoParticipacao`, `UfParlamentar`, primeira e segunda legislaturas (número, início, fim), `Exercicios` (131 exercícios; 50 com data fim e causa de afastamento), `Suplentes` (150, com código e nome) e `Titular` (11, para quem é suplente em exercício). **A lista não traz data de nascimento nem CPF.**

**Detalhe `GET /senador/{codigo}` (um senador, n=1).** Além dos campos acima: `DadosBasicosParlamentar` com `DataNascimento` (`aaaa-mm-dd`), `EnderecoParlamentar`, `Naturalidade` e `UfNaturalidade`; `OutrasInformacoes.Servico[]` (13 serviços, com nome, descrição e URL) e `Telefones`. **Sem CPF.** `EnderecoParlamentar` parece institucional (o texto menciona "Senado" e "Anexo") e o e-mail termina em `@senado.leg.br` (inferência, n=1).

**Subrecursos do mesmo senador (n=1).**
| Subrecurso | O que devolveu |
|---|---|
| `/profissao`, `/historicoAcademico` | Só metadados e o código; **sem itens** para este senador |
| `/filiacoes` | 4 filiações (partido: código, nome, sigla; data de filiação; 3 com data de desfiliação) |
| `/mandatos` | 1 mandato, com exercícios, 2 partidos e suplentes |
| `/comissoes` | 82 participações (código, nome, sigla e casa da comissão; participação; início; 56 com fim); 20 KB, 0,78 s |
| `/discursos` | `Pronunciamentos` vazio na janela padrão (sem filtro de data; não medi com intervalo) |

**Votos individuais, `GET /votacao?dataInicio=2026-10-01&dataFim=2026-10-31` (3 votações nominais).** Cada uma traz **81 votos individuais** (um por senador, 81 códigos distintos). Cada voto tem 7 campos: `codigoParlamentar` (inteiro), `nomeParlamentar`, `sexoParlamentar`, `siglaPartidoParlamentar`, `siglaUFParlamentar`, `siglaVotoParlamentar` e `descricaoVotoParlamentar` (esta preenchida em só 2% a 4% dos votos).
- **`siglaVotoParlamentar` tem mais que sim e não:** `Sim`, `Não`, `AP`, `LS`, `P-NRV`, `NCom` e `Presidente (art. 51 RISF)` (nas três votações juntas). O significado das siglas `AP`, `LS`, `P-NRV` e `NCom` **não foi verificado** na documentação.
- **Os totais `totalVotosSim`, `totalVotosNao` e `totalVotosAbstencao` vêm nulos** nas três votações nominais, embora os 81 votos individuais estejam lá. Pela especificação, votações secretas trazem só totais (documentação); as três medidas eram `votacaoSecreta = N`. Os totais, se necessários, têm de ser calculados a partir dos votos.
- Cada votação traz também `identificacao`, `ementa`, `sigla`, `numero`, `ano`, `idProcesso`, `codigoMateria`, `codigoSessaoVotacao`, `dataSessao`, `resultadoVotacao` e `informeLegislativo`.

Reproduzir os votos e os totais nulos:
```bash
curl -sS -H 'Accept: application/json' "https://legis.senado.leg.br/dadosabertos/votacao?dataInicio=2026-10-01&dataFim=2026-10-31" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d),"votações;",[len(v["votos"]) for v in d],"votos cada; totalVotosSim:",{v["totalVotosSim"] for v in d})'
# esperado em 2026-11-05: 3 votações; [81, 81, 81] votos cada; totalVotosSim: {None}
```

**Não verificado nesta rodada:** os campos de senadores além do n=1; discursos e apartes com filtro de data; votações secretas; o significado das siglas de voto; `profissao` e `historicoAcademico` para outros senadores.

## Rodada 3: votações em janela de 30 dias e de 1 ano (medido, 2026-11-13)
Duas requisições `GET /votacao?dataInicio&dataFim` (200, `application/json`, `cache-control: max-age=600`), uma pausa de 8 s entre elas, da mesma máquina. Só estrutura e contagens; nenhum voto individual foi impresso ou commitado.

| Janela | Votações | Votos | Tamanho | Tempo |
|---|---|---|---|---|
| 2026-10-14 a 2026-11-13 (30 dias) | 11 | 891 | 208.811 B | 0,31 s |
| 2025-11-14 a 2026-11-13 (365 dias) | 87 | 7.047 | 1.652.031 B | 0,68 s |

- **Votação (25 chaves, todas presentes nas 87):** `codigoSessaoVotacao` (inteiro, **87 de 87 distintos**, sem nulo), `idProcesso`, `codigoMateria`, `codigoSessao`, `codigoSessaoLegislativa`, `numeroSessao`, `sequencialSessao`, `sequencialVotacao` (nulo em 2 votações abertas), `identificacao`, `sigla`, `numero`, `ano`, `casaSessao`, `siglaTipoSessao`, `dataSessao` e `dataApresentacao` (`aaaa-mm-dd`), `descricaoVotacao`, `ementa`, `resultadoVotacao` (`A` em 82, `R` em 5), `votacaoSecreta` (`N` 47, `S` 40), `informeLegislativo` (objeto em 83, nulo em 4), `totalVotosSim`, `totalVotosNao`, `totalVotosAbstencao`, `votos`. Tamanhos máximos vistos: `ementa` 606, `descricaoVotacao` 164, `identificacao` 30, `nomeParlamentar` 25.
- **Cada votação traz exatamente 81 votos**, sem voto repetido por (votação, parlamentar). `codigoParlamentar` é inteiro; **93 códigos distintos no ano** (os 81 de hoje mais suplentes que votaram e saíram); 23 desses códigos não votaram em todas. Partido nunca vazio e UF sempre com 2 letras. Voto: 7 chaves (`codigoParlamentar`, `nomeParlamentar`, `sexoParlamentar`, `siglaPartidoParlamentar`, `siglaUFParlamentar`, `siglaVotoParlamentar`, `descricaoVotoParlamentar`, esta preenchida em 1.788 de 7.047).
- **`siglaVotoParlamentar` tem 13 valores no ano:** `Sim` 2.718, `Votou` 2.043, `P-NRV` 988, `AP` 536, `Não` 437, `LS` 124, `MIS` 74, `Presidente (art. 51 RISF)` 48, `NCom` 50, `Abstenção` 13, `LP` 8, `NA` 7, `LAP` 1. **O significado de `AP`, `LS`, `P-NRV`, `MIS`, `NCom`, `LP`, `NA` e `LAP` continua sem verificação.**
- **Votação secreta (40 de 87) NÃO vem sem votos:** traz os mesmos 81 itens, mas o conteúdo do voto não aparece. `Votou` (2.043 itens) só diz que o senador votou, não como; as outras siglas são ausência ou impedimento. Nas secretas os **totais vêm preenchidos** (40 de 40: por exemplo 43, 2 e 1); nas abertas **vêm nulos** (47 de 47). Isso corrige a medição de 2026-11-05 ("votações secretas só trazem totais"), que se baseava na especificação e não em dado.
- **Ainda não medido:** o que acontece com janela maior que 1 ano (a documentação diz que o intervalo é de até 1 ano); o comportamento com `dataFim` no futuro; o significado das siglas. Votações antigas **mudam** depois de publicadas: ver "Estado da integração" (Sessão 70).

## Reproduzir as medições
Use um `User-Agent` genérico e espere alguns segundos entre as requisições.
```bash
B=https://legis.senado.leg.br/dadosabertos
curl -sS "$B/v3/api-docs" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d["paths"]), sum(v["get"].get("deprecated",False) for v in d["paths"].values()))'   # 157 42
curl -sS -H 'Accept: application/json' "$B/senador/lista/atual" | python3 -c 'import json,sys;print(len(json.load(sys.stdin)["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"]))'   # 81 (muda com a composição)
curl -sS -D - -o /dev/null -H 'Accept: application/json' "$B/materia/172391" | grep -iE '^(deprecation|sunset|link)'
curl -sS -H 'Accept: application/json' "$B/senador/99999999" -w '\n%{http_code}\n'   # 200 sem dados
```
Os números de senadores e de itens de processo e votação mudam com o tempo.

## Estado da integração
Desde a Sessão 66 (2026-11-13, ADR 0028): coleta e normalização da **lista de senadores em exercício** (`senado/senadores`, `GET /senador/lista/atual.json`, allowlist de 4 campos), conjunto cadastrado e habilitado pelo dono em 2026-11-13 (Sessão 68). Medido de novo em 2026-11-12: 200, JSON, 129.557 bytes, 81 senadores, código do parlamentar como texto. Votações, proposições e o detalhe do senador: nada integrado.

**Primeira coleta real (2026-11-13, Sessão 68, banco de desenvolvimento):** 81 lidas e 81 gravadas; normalização 81 criadas e, na segunda execução, 0 criadas e 81 existentes. 27 UFs, nome mais longo com 25 caracteres, 81 em exercício. **O partido nunca vem vazio, mas a fonte usa o texto `S/Partido` para quem não tem partido** (1 valor, 1 coleta). Para coletar, a fonte precisa estar "Em integração" ou "Ativa" além do conjunto habilitado. Uma coleta só: a saída da lista (`saiu_da_lista_em`) ainda não foi vista com dado real.

**Votações (Sessão 69, ADR 0029):** conjunto `senado/votacoes` (formato `json_senado_votacoes`, `GET /votacao.json` com janela de 360 dias, uma linha por voto), cadastrado **desabilitado**; `SenateVoting` e `SenateVote` e o comando `normalize_senado_votacoes`. Medido em 2026-11-13 (Rodada 3). O sufixo `.json` sem `Accept` devolveu o mesmo conteúdo que o `Accept: application/json` (11 votações em 30 dias, 208.811 bytes).

**Primeira coleta real das votações (2026-11-13, Sessão 70, banco de desenvolvimento de outro PC que o das Sessões 67 a 69):** conjunto habilitado pelo dono; 7.047 lidas e 7.047 gravadas; normalização com 87 votações e 7.047 votos criados e, na segunda execução, 0 criados. Votações de 2025-11-25 a 2026-11-12 (nenhuma entre 13 e 24/11/2025, por isso a janela de 360 dias deu o mesmo que a de 365). Sempre 81 votos por votação; nas 40 secretas nenhum `Sim`, `Não` ou `Abstenção`; nas 47 abertas os totais batem com a contagem de votos. **A fonte reclassifica votos já publicados:** na mesma data, contra a Rodada 3 da manhã, `P-NRV` 988 → 993, `MIS` 74 → 75 e `NCom` 50 → 44 (soma igual). `S/Partido` aparece em 22 votos.

**API interna das votações (Sessão 71, ADR 0030):** `GET /internal/v1/senado/votacoes/` (50 por página) e `/<codigo>/` (secreta com `participacao`, aberta com `votos`, contagem por sigla calculada e totais da fonte à parte). Numa secreta real (7104) os totais da fonte, 63/4/0, somam exatamente os 67 `Votou`; não conferido nas outras 39.

## Ainda não medido nesta rodada
O comportamento real do 429 (não testei o limite); volume e custo de `/processo` sem filtro de ano e de `/votacao` num ano inteiro; discursos, taquigrafia, orçamento e votações de comissão; conteúdo dos endpoints `/senador/{codigo}/...` e seus dados pessoais; XML e NDJSON; consistência entre os endpoints legados e novos para o mesmo registro; estabilidade dos ids; o Plano de Dados Abertos 2026/2028; leitura jurídica da política de uso para a API.
