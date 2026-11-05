# 0005: Minimização de dados pessoais (P-12)

**Data:** 2026-11-05

## Contexto
O PRD §11 exige minimização de dados pessoais e política de retenção, e o §4 põe a privacidade como princípio. A medição das três fontes do primeiro corte (`project/fontes/`) mostrou o risco concreto: o CSV aberto de candidatos do TSE de 2026 traz o CPF completo e válido de cada candidato e o título de eleitor, com o **mesmo esquema** de 2024, onde a coluna do CPF era uma constante. Quem só valida o esquema não percebe a mudança.

O PRD §9.1 ("preservar o dado original quando permitido") e o §4 (verificabilidade) puxam no sentido oposto da minimização quando o original contém CPF. Este ADR resolve essa tensão. Ele **refina a leitura** do §9.1 (preservar o original *filtrado*, com hash e URL de origem) e não altera o PRD. A interpretação jurídica (LGPD, nome social, dado sensível) continua no P-16 e não está validada.

## Decisão

1. **Lista de permissão de colunas por fonte (allowlist).** Cada fonte declara as colunas que ingere. O que não está na lista é descartado **na leitura** e nunca chega ao banco. Vale para fontes futuras: nenhuma fonte entra sem allowlist declarada no cadastro de fontes (PRD §8.1).
2. **Ligação de pessoas entre fontes** por ids de origem (`id` da Câmara, `CodigoParlamentar` do Senado, `SQ_CANDIDATO` do TSE) mais atributos públicos (nome, data de nascimento, UF de nascimento), com revisão humana nos casos ambíguos (homônimos, PRD §6.1). **Sem CPF e sem título de eleitor, nem em hash.** A ligação é uma afirmação com evidência, pode ser desfeita e nunca apaga as origens (PRD §9.3 e §9.4).
3. **Fora da Etapa 1:** bens de candidatos, prestação de contas, doações e fornecedores (carregam CPF/CNPJ de terceiros e valores). Entram na Etapa 3, com nova rodada do P-12 e validação do P-16.
4. **Atributos demográficos do TSE** (cor/raça, gênero, estado civil, grau de instrução, ocupação) não são ingeridos na Etapa 1. Entram, um a um, quando uma funcionalidade concreta pedir e o P-16 validar.
5. **Camada bruta filtrada:** guarda só as colunas da allowlist, mais o SHA-256 do arquivo original, a URL, a data de geração e o `ETag`.
6. **Mudança na fonte:** leitura por **nome de coluna**, nunca por posição. Coluna permitida que sumiu ou mudou de formato: **falha fechada** (a carga daquele arquivo para, nada é gravado, alerta). Coluna nova fora da allowlist: ignorada, com alerta. Cada fonte tem testes de contrato com arquivos de exemplo pequenos.
7. **Data de nascimento:** guardada completa, só para uso interno (ligação e revisão); exposta no máximo como **ano de nascimento**, na interface e na API pública (PRD §14).
8. **Nome:** a interface e a API exibem o nome público (parlamentar ou de urna); o **nome social prevalece** sobre o civil; o **nome civil é só interno** e nunca é exposto nem vai para logs.
9. **Retirada pela fonte:** falha técnica (5xx, arquivo ausente, download cortado) **nunca apaga**. Registro ausente de um arquivo **íntegro** (hash e contagem batendo, esquema válido) vira "retirado pela fonte": some da interface e da API pública na mesma carga, os campos pessoais são apagados do banco e da camada bruta filtrada, e fica uma **lápide** (id de origem, fonte, data da retirada). Após restaurar um backup, as lápides são reaplicadas antes de qualquer exposição pública.
10. **Pedidos de correção ou remoção:** dado que vem de uma fonte é encaminhado à fonte, e o polis segue o que ela fizer (decisão 9). Dado produzido pelo polis (ligações, análises) é corrigido ou removido pelo polis, com registro do que mudou e por quê. Pedidos com base na LGPD passam por validação jurídica (P-16) antes de qualquer resposta. Prazo de resposta: não fixado aqui.
11. **Retenção da camada bruta filtrada:** as últimas **3 cargas por arquivo** (valor inicial, ajustável sem mudar a regra). A história de alterações vive no modelo normalizado, com origem e data (PRD §4).

Pressupostos: os campos internos (data completa, nome civil) só são acessíveis ao administrador (PRD §11, "controle de acesso administrativo"). Nada disso vai a público antes da validação do P-16 (PRD §11, último parágrafo).

### Allowlist inicial

Ponto de partida para revisão. Cada coluna é conferida contra o dicionário de dados da fonte na implementação.

| Fonte | Entra | Interno (nunca exposto) | Fora |
|---|---|---|---|
| **TSE** `consulta_cand` | Tipo, ano, turno e código da eleição; cargo; UF e unidade eleitoral; `SQ_CANDIDATO`, `NR_CANDIDATO`, `NM_URNA_CANDIDATO`, `NM_SOCIAL_CANDIDATO`; partido, federação e coligação; situação da candidatura e resultado; `DT_GERACAO`, `HH_GERACAO` | `NM_CANDIDATO` (nome civil; assumido, não confirmado no dicionário de dados), `DT_NASCIMENTO`, `SG_UF_NASCIMENTO` | `NR_CPF_CANDIDATO`, `NR_TITULO_ELEITORAL_CANDIDATO`, `DS_EMAIL`, gênero, grau de instrução, estado civil, cor/raça, ocupação, `CD_SITUACAO_CANDIDATURA` (0% preenchida na amostra), fotos |
| **Câmara** (API e `deputados.csv`) | `id`, `uri`, `nome`, partido, UF, legislaturas inicial e final; proposições (`id`, tipo, número, ano, ementa, data); votações (`id`, datas, órgão, objeto, descrição, aprovação); votos individuais: `idVotacao`, `dataHoraVoto`, `voto`, `deputado_id`, `deputado_siglaPartido` (partido no momento do voto) | `nomeCivil`, `dataNascimento`, `ufNascimento` | **`cpf` (vem vazio no CSV em massa, mas preenchido e válido no detalhe `/deputados/{id}` da API; descartar na leitura nos dois canais)**, `email`, `sexo`/`siglaSexo`, `escolaridade`, redes sociais e site, município de nascimento, data de falecimento, gabinete, `urlFoto`; nos votos, `deputado_nome`, `deputado_uri`, `deputado_uriPartido`, `deputado_siglaUf`, `deputado_urlFoto` |
| **Senado** | Processo (`id`, `codigoMateria`, identificação, ementa, datas, situação, tipo, URL); votação (`identificacao`, `ementa`, `sigla`, `numero`, `ano`, `idProcesso`, `codigoMateria`, `codigoSessaoVotacao`, `dataSessao`, `resultadoVotacao`); senadores: `CodigoParlamentar`, `NomeParlamentar`, `SiglaPartidoParlamentar`, `UfParlamentar`, mandato (códigos, legislaturas, exercícios, titular e suplentes por código), filiações (partido e datas), comissões (código, sigla, nome, participação, datas); votos individuais: `codigoParlamentar`, `siglaVotoParlamentar`, `siglaPartidoParlamentar` | `NomeCompletoParlamentar`, `DataNascimento`, `UfNaturalidade` | `EmailParlamentar`, telefones, `EnderecoParlamentar`, `Naturalidade` (município), `SexoParlamentar`/`sexoParlamentar`, `FormaTratamento`, fotos e URLs particulares, serviços; nos votos, `nomeParlamentar`, `siglaUFParlamentar`; `totalVotosSim`/`Nao`/`Abstencao` (vêm nulos nas votações nominais; calcular a partir dos votos) |

### Revisão da allowlist (Sessão 7, 2026-11-05)

Depois de medir os endpoints de senadores e os votos individuais (`fontes/senado.md` e `fontes/camara.md`, "Rodada 2"), a tabela acima foi corrigida. **As 11 decisões não mudaram.** O que mudou:
- **CPF da Câmara:** a versão anterior dizia "`cpf` (vem vazio)", medido só no CSV em massa. O detalhe `/deputados/{id}` da API devolve o CPF preenchido e válido (um deputado). A coluna continua fora da allowlist e é descartada na leitura nos dois canais; o ponto reforça a decisão 1 (descarte na leitura) e a 6 (leitura por nome de coluna): o mesmo dado muda de tratamento conforme o canal.
- **Votos individuais** entram na Etapa 1 (ato público). Cada linha de voto carrega só o id do parlamentar, o voto, a data e o partido no momento do voto. Nome, UF, foto e sexo ficam na tabela de pessoas, e a ligação é feita pelo id. Isso evita repetir dado pessoal em milhões de linhas.
- **Totais de votação do Senado:** `totalVotosSim`, `Nao` e `Abstencao` vêm nulos nas votações nominais; os totais devem ser calculados a partir dos votos individuais.
- **Valores de voto:** o Senado usa `Sim`, `Não`, `AP`, `LS`, `P-NRV`, `NCom` e `Presidente (art. 51 RISF)`; a Câmara, pelo menos `Sim`, `Não` e `Artigo 17`. O significado das siglas ainda não foi verificado; o conector deve guardar o valor original e mapeá-lo para um conjunto próprio só depois de verificado.
- **Senadores:** `DataNascimento`, `UfNaturalidade` e `NomeCompletoParlamentar` ficam como internos (decisões 2, 7 e 8). Endereço, e-mail e telefones parecem institucionais (n=1) e não são necessários, então ficam fora.

Ainda não medido: o CPF no detalhe para mais de um deputado; os votos nominais da Câmara pela API (travaram em 504); a lista completa de valores de `voto`; discursos e apartes.

## Alternativas
- **Ingerir tudo e esconder o que for sensível só na exibição:** descartado. Uma coluna nova ou uma que muda de conteúdo (o CPF do TSE) já estaria no banco, e cada tela teria de lembrar de escondê-la. Lista de permissão falha para o lado seguro; lista de bloqueio falha para o lado inseguro.
- **Camada bruta intacta (com CPF):** descartada. Guardaria o que a decisão 1 manda descartar. Custo aceito da alternativa escolhida: se uma coluna entrar na allowlist depois, é preciso baixar de novo da fonte.
- **Nenhuma camada bruta:** descartada. Impede reprocessar e auditar cargas recentes.
- **CPF ou título como chave de ligação, mesmo em hash:** descartado. O CPF tem cerca de 10⁹ valores possíveis, e um hash sem segredo é reversível por força bruta; com HMAC o risco cai, mas passa a existir uma chave a proteger e o dado continua pessoal pela LGPD.
- **Não guardar a data de nascimento:** descartado por piorar demais a ligação entre fontes.
- **Expor a data de nascimento completa ou o nome civil:** descartado (minimização; risco ao exibir o nome civil de quem usa nome social).
- **Reter registros retirados pela fonte:** descartado. Manteria um dado que a fonte decidiu retirar, talvez por ordem judicial ou pedido de remoção.
- **Corrigir dados de fonte no polis:** descartado. Quebraria a rastreabilidade (PRD §4).

## Consequências
- A ligação entre fontes fica menos automática e depende de revisão humana nos ambíguos.
- Uma coluna adicionada à allowlist depois exige nova carga da fonte (a fonte pode ter mudado nesse meio-tempo).
- Perde-se o histórico dos registros retirados pela fonte.
- O conector precisa de leitura por nome de coluna, validação de formato, testes de contrato por fonte, detecção de arquivo íntegro e uma tabela de lápides reaplicada após restauração de backup.
- Nenhuma fonte entra sem allowlist declarada no cadastro de fontes.
- **Não substitui o P-16:** a interpretação jurídica (LGPD, nome social, dado sensível, prazo de resposta a pedidos) continua em aberto. Vale reconferir o CPF do TSE de 2026, que é uma medição de um único dia.
- Habilita desenhar o schema (P-02, P-05) sabendo quais colunas existem.
