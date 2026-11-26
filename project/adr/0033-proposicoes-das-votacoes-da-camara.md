# 0033: Proposições das votações da Câmara: dois arquivos, ligação sem chave para a votação

**Data:** 2026-11-26

## Contexto
A votação da Câmara (ADR 0031) guarda só `proposition_id`, o id de `ultimaApresentacaoProposicao_idProposicao`, e **`0` quer dizer "sem proposição"** (4.180 das 9.417 votações em 2026-11-26). A página da votação não diz o que se votou. A Etapa 1 do PRD (§15) lista "Proposições e tramitações".

A Rodada 4 de `project/fontes/camara.md` (medida em 2026-11-26, Sessão 107) mostrou que o arquivo anual de proposições não serve para isso e que dois arquivos de votações já trazem o necessário:
- `votacoesProposicoes-2026.csv` (3,6 MB, 7.160 linhas, 7.084 votações, até 3 proposições por votação) e `votacoesObjetos-2026.csv` (17,2 MB, 39.416 linhas, 8.842 votações, **até 212 por votação**) têm título, tipo, número, ano e ementa da proposição. **Juntos cobrem as 9.417 votações**, inclusive as 4.180 com `proposition_id` 0. **Os dois não repetem nenhum par (votação, proposição)** (46.576 pares na união) e têm 26.745 proposições distintas, 21 delas nos dois, **sem nenhum conflito** de dados.
- `proposicoes-2026.csv` (47,1 MB) não basta: 579 dos 4.340 ids das votações de 2026 só estão em `proposicoes-2025.csv` (90,2 MB), e `ano` é `0` em 51% das proposições de 2026.
- `ementa` chega a 5.259 caracteres, pode ser vazia (404 proposições) e tem quebra de linha e TAB; o **TAB é o único caractere de controle** (7 + 35 ocorrências). `proposicao_ano` vem vazio em 32.899 linhas de `votacoesObjetos` e em 1 de `votacoesProposicoes`.

O significado de um arquivo versus o outro (qual é a proposição "principal" da votação) **não foi verificado**.

## Decisão
1. **Fonte: os dois arquivos**, como dois conjuntos de `camara` (`votacoes-proposicoes-2026` e `votacoes-objetos-2026`), formato `csv` (o leitor do ADR 0031), por decisão do dono no admin (`owner_decision`), **desabilitados ao nascer**, 24 h, depois das 08:00 GMT. Ano fixo no cadastro.
2. **Allowlist de 7 colunas, igual nos dois:** `idVotacao`, `proposicao_id`, `proposicao_titulo`, `proposicao_ementa`, `proposicao_siglaTipo`, `proposicao_numero`, `proposicao_ano`. Descartados na leitura (ADR 0005): `uriVotacao`, `proposicao_uri`, `data` e `descricao` (a votação já os tem) e `proposicao_codTipo` (a sigla basta).
3. **Modelo:** `CamaraProposition` (id da Câmara único, título, sigla do tipo, número, ano **opcional**, ementa em branco) e `CamaraVotingProposition` (id da votação em texto, proposição, `origin`; único em (votação, proposição)). Migração `legislature/0007`, aditiva.
4. **A ligação não tem chave para `CamaraVoting`.** Guarda o id da votação em texto e a junção é na leitura, como `CamaraVote` com `Deputy` (ADR 0029 e 0031). **Isto diverge do ADR 0031**, em que o voto aponta para a votação e a normalização espera até 48 h pela coleta de votações: aqui não há espera, recusa por voto sem votação, nem corrida entre coletas.
5. **Cada arquivo é normalizado sozinho**, a partir da carga mais recente do próprio conjunto (`camara_proposition_normalization.normalize_latest`, registrada em `settings.NORMALIZERS` para os dois). Uma só transação, upsert pela chave em lotes de 1.000, falha fechada, nunca apaga, erros só com nomes de coluna e contagens. Teto de 500.000 linhas por carga (o real é 39.416). Entre os dois arquivos vale a **última gravação**; a divergência entre eles não é recusa (medido: 0 conflitos nas 21 proposições comuns). Conflito **dentro do mesmo arquivo** (mesma proposição com dados diferentes) recusa.
6. **`origin` ("proposicoes" ou "objetos") é guardado sem interpretar**, porque o significado de cada arquivo não foi verificado.
7. **Texto da `ementa`:** quebra de linha (inclusive U+2028 e U+2029) e **TAB viram um espaço** (decisão do dono, por analogia com a `descricao` da votação); qualquer outro caractere de controle recusa a linha; teto de 20.000 caracteres (4 vezes o maior medido, 5.259); vazia é válida. `ano` vazio vira nulo. O bruto guarda o texto como veio. A página futura deve escapar o texto.
8. **Fora desta fatia:** API interna e página, tramitações, autores e temas, e o campo `CamaraVoting.proposition_id` (continua gravado como vem, com o `0`).
9. **Plebiscito não tem fatia própria** (decisão do dono): por texto são cerca de 5 proposições por ano; a busca de texto atende quando cobrir proposições.

## Alternativas
- **`proposicoes-YYYY` como fonte:** descartada; 47 a 90 MB por ano, não cobre o ano anterior (579 ids só em 2025) e `ano` é `0` em 51% das linhas.
- **Chave para `CamaraVoting` (como o voto do ADR 0031):** descartada; traria de volta a corrida entre coletas, a espera e a recusa depois de 48 h, e o limite conhecido do ADR 0031 (a espera nunca vira recusa com as cargas paradas). Custo aceito: a ligação pode apontar para uma votação que ainda não chegou.
- **Ler os dois arquivos juntos, como votações e votos:** descartada; criaria a espera de novo sem ganho, já que os pares são disjuntos.
- **Recusar TAB na `ementa` (como em `descricao`):** descartada pelo dono; o TAB é o único controle real (42 ocorrências) e pararia a coleta todo dia.
- **Interpretar `origin` (por exemplo "principal" e "afetada"):** descartada; sem verificação seria inventar um significado.
- **API por proposição (`/proposicoes/{id}`):** descartada; uma chamada por id e a lentidão medida da API (ADR 0031).
- **Tramitações junto:** adiada; `proposicoesTramitacoes-2026` tem 38,9 MB por ano e `despacho` é texto livre que cita agentes públicos (ADR 0005 não avaliado).
- **Generalizar o código copiado das votações:** adiada (ADR 0022 e 0031); sem terceira implementação ainda.

## Consequências
- Quarto e quinto conjuntos da Câmara **sem licença declarada**, por decisão do dono; redistribuição e uso comercial ficam no P-16, e nada vai a público antes.
- **Download diário** de 3,6 MB + 17,2 MB (2026). O teto de 100 MB do `PlainCsvReader` cobre com folga.
- A página da votação passará a mostrar o que se votou **sem depender do `proposition_id`**, inclusive nas 4.180 votações com `0`. Votações com até 212 proposições (`votacoesObjetos`) pedem limite de exibição na página futura.
- A ligação pode existir antes da votação (e para uma votação que a Câmara retire): a leitura faz a junção e trata a ausência.
- **Limites conhecidos:** entre os dois arquivos vale a última gravação (sem checagem de divergência); o significado de `origin` não foi verificado; as 14 proposições de `ultimaApresentacaoProposicao_idProposicao` que não estão em nenhum arquivo medido (2025 e 2026) ficam sem ligação por esse campo, mas as votações têm ligação pelos dois arquivos de objetos; anos anteriores a 2025 não foram medidos.
- Reversível: desabilitar os conjuntos no admin. A coleta não tem migração; a normalização traz a `legislature/0007`, aditiva (duas tabelas novas).
- **Não validado por mim:** a coleta real dos dois arquivos (volumes, tempo, memória do leitor com 17 MB); a estabilidade dos ids de proposição entre cargas; a interpretação jurídica (P-16).
