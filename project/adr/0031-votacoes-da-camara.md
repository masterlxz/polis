# 0031: Câmara: votações e votos pelos arquivos anuais em massa, dois conjuntos

**Data:** 2026-11-24

## Contexto
A Etapa 1 do PRD tem o Senado com votações e votos por senador (ADR 0029 e 0030), mas a Câmara só tem a lista de deputados. Os votos individuais pela API da Câmara deram **504 em 4 de 4 tentativas** (`fontes/camara.md`, Rodada 2), e seriam uma chamada por votação. O caminho viável são os arquivos anuais em massa.

Medição de 2026-11-24 (`fontes/camara.md`, Rodada 3): `votacoes-2026.csv` tem 5,6 MB, 20 colunas, **9.153 votações** (ids `<n>-<n>`, sem repetição); `votacoesVotos-2026.csv` tem 19,2 MB, 12 colunas, **57.855 votos em 170 votações** (1,9% têm voto nominal; as outras só têm os totais `votosSim`, `votosNao` e `votosOutros`). Os dois são UTF-8 com BOM, separados por `;`. Não há variante `.zip` (404). Todo `idVotacao` de voto existe em `votacoes`, e não há voto repetido por (votação, deputado). **951 registros de `votacoes` ocupam mais de uma linha física**: 947 em `ultimaApresentacaoProposicao_descricao` (descartada) e **5 em `descricao`** (permitida). **466 votos têm `voto` vazio, todos na votação `2645346-18`.**

## Decisão
1. **Dois conjuntos**, um por arquivo: `camara/votacoes-2026` e `camara/votos-2026`, por decisão do dono no admin (`owner_decision`), nascem desabilitados. Uma requisição por arquivo por dia, depois das 08:00 GMT (os arquivos são regenerados de madrugada). **Ano fixo no cadastro**, como o TSE: virar o ano é um cadastro novo e uma decisão do dono.
2. **Formato `csv`** (o valor já existia no enum, sem leitor próprio): `PlainCsvReader` (`apps/sources/plain_csv.py`), subclasse do `ZipCsvReader` que troca só a abertura do arquivo e herda a validação. **Registro multilinha aceito** neste formato, **teto de 100 MB** (o maior arquivo real foi 58 MB, votos de 2025), checado antes de ler. Sem migração.
3. **Allowlists.** Votações (10): `id`, `data`, `dataHoraRegistro`, `siglaOrgao`, `aprovacao`, `votosSim`, `votosNao`, `votosOutros`, `descricao`, `ultimaApresentacaoProposicao_idProposicao` (o "objeto" do ADR 0005, sempre numérico nos 9.153 registros). Votos (6): `idVotacao`, `dataHoraVoto`, `voto`, `deputado_id`, `deputado_siglaPartido` (o partido do momento do voto) e **`deputado_idLegislatura`**. Esta última é uma **emenda de leitura do ADR 0005**: ele lista só `deputado_id`, mas a chave de `Deputy` é (legislatura, id da Câmara), e a coluna não é dado pessoal (57 nas 57.855 linhas). Descartados: `uri*`, `uriPartido`, nome, UF e foto do deputado, o órgão e o evento por id, a abertura da votação e o texto da última apresentação.
4. **Normalização (fatia seguinte, com estas regras já fixadas):**
   - Lê a carga mais recente dos dois conjuntos, sem rede, e casa por `idVotacao` em memória (comparação de texto, não `int()`).
   - **Falha fechada**: coluna permitida ausente ou repetida, `idVotacao` de voto sem votação, votação ou voto repetido param a carga. Upsert, nunca apaga.
   - `CamaraVoting` e `CamaraVote` **sem FK para `Deputy`** (o voto guarda o `deputado_id`, a legislatura e o partido do momento do voto; a junção é na leitura), como a decisão 5 do ADR 0029.
   - **`descricao`: quebras de linha viram espaço** (decisão do dono); o bruto guarda o texto como veio. Qualquer outro caractere de controle recusa a carga.
   - **`voto` vazio é gravado como vem** (decisão do dono), sem mapear. A API e a página futuras tratam vazio como "sem posição registrada", nunca como voto.
   - Siglas de `voto` (`Sim`, `Não`, `Abstenção`, `Obstrução`, `Artigo 17`) e `aprovacao` (`1`, `0`, vazio) como vêm; o significado não foi verificado.

## Alternativas
- **Um formato que baixa os dois arquivos num run:** descartada; cria estado de ligação entre eles e um 2º download no mesmo run, sem ganho. Aqui são dois arquivos, ao contrário do Senado (ADR 0029), onde dois conjuntos foram descartados por a fonte entregar tudo numa resposta só.
- **URL calculada pelo relógio (como a janela de 360 dias do Senado):** descartada; esconde a virada do ano.
- **API por votação (`/votacoes/{id}/votos`):** descartada; 504 em 4 de 4 tentativas e uma chamada por votação.
- **Falha fechada para registro multilinha:** descartada pelo dono; 5 linhas parariam a coleta do ano inteiro, todo dia, até a Câmara corrigir.
- **Pular os votos vazios:** descartada; some a presença de 466 deputados que a fonte publica, o que o ADR 0029 recusou para o Senado. **Falha fechada para voto vazio:** descartada; uma votação pararia a coleta toda.
- **Refatorar o `zip_csv.py` para separar o núcleo:** descartada nesta fatia; a subclasse reaproveita sem tocar no que funciona. Se um 3º leitor aparecer, a separação passa a ter dor concreta.
- **Módulo novo que repete a validação de cabeçalho:** descartada; duplica regras de segurança (ADR 0005, decisões 1 e 6).

## Consequências
- Terceira fonte sem licença declarada, por decisão do dono; redistribuição e uso comercial ficam no P-16, e nada vai a público antes.
- **19 MB por dia** de download em 2026 (votos); em 2025 o arquivo de votos tinha 58 MB. O teto de 100 MB cobre isso com folga.
- **Só 1,9% das votações têm voto nominal.** A página futura da votação sem lista mostra só os totais da fonte; os totais `votosSim` e `votosNao` divergem da contagem dos votos em **1 de 170** votações nominais (não verifiquei qual).
- O `PlainCsvReader` usa métodos privados do `ZipCsvReader` (`_read_layout`, `_read_item`, `_open_text`) com um item de mentira; se o contrato deles mudar, `tests/test_plain_csv.py` falha. É o custo de não refatorar agora.
- Reversível: desabilitar os conjuntos no admin; esta fatia não tem migração (a da normalização é aditiva).
- **Não validado por mim:** o significado das siglas e de `aprovacao`; a estabilidade do `id` da votação no tempo (visto em uma medição); o pico de memória do leitor com um arquivo de dezenas de MB (herda a leitura em fluxo, sem teste novo); a coleta real; a interpretação jurídica (P-16).
