# 0029: Senado: votações com o voto de cada senador, bruto achatado e voto sem chave para `Senator`

**Data:** 2026-11-13

## Contexto
A próxima fatia da Etapa 1 do PRD (§15) é "votações". A API `GET /votacao?dataInicio&dataFim` do Senado devolve uma **lista** de votações, cada uma com a lista `votos` embutida (81 itens medidos). Medição de 2026-11-13 (`fontes/senado.md`, Rodada 3): janela de 365 dias = 87 votações, 7.047 votos, 1,65 MB, 0,68 s; janela de 30 dias = 11 votações, 208 KB. `codigoSessaoVotacao` é inteiro e único (87 de 87); o intervalo máximo é de 1 ano. O sufixo `.json` (sem `Accept`) dá o mesmo conteúdo, e o cliente do projeto não envia `Accept`.

A medição corrigiu duas premissas: **40 das 87 votações são secretas e trazem os 81 itens** (o item `Votou` diz que votou, não como; os totais vêm preenchidos), e nas abertas os totais vêm nulos. E os votos têm **93 códigos de parlamentar** num ano, contra 81 senadores em exercício hoje (suplentes que votaram e saíram).

## Decisão
1. **Conjunto `senado/votacoes`**, por decisão do dono no admin (`owner_decision`), como o ADR 0028. O cadastro nasce desabilitado e nunca copia a justificativa. Uma requisição por dia, depois das 08:00 GMT.
2. **Formato `json_senado_votacoes`** (`apps/sources/json_senado_votacoes.py`): pede os **últimos 360 dias** (relógio do servidor; a API aceita até 1 ano) e grava o arquivo achatado `{"dados": [...]}`, **uma linha por voto** com os campos escalares da votação repetidos, ordenado por (votação, parlamentar). Mesmo conteúdo, mesmo SHA-256. Corpo que não é lista, lista vazia, votação sem código inteiro ou **sem votos**, voto sem código, votação ou voto repetidos, arquivo maior que 20 MB ou mais de 50.000 votos **recusam a carga** (falha fechada, como o ADR 0028).
3. **Allowlist de 19 colunas:** da votação, `codigoSessaoVotacao`, `dataSessao`, `sigla`, `numero`, `ano`, `identificacao`, `ementa`, `resultadoVotacao`, `votacaoSecreta`, os três totais, `idProcesso` e `codigoMateria`; do voto, `codigoParlamentar`, `nomeParlamentar`, `siglaPartidoParlamentar`, `siglaUFParlamentar` e `siglaVotoParlamentar`. Descartados na leitura: sexo, o texto livre do voto (`descricaoVotoParlamentar`), `descricaoVotacao` e o informe legislativo (ADR 0005).
4. **`SenateVoting` e `SenateVote` em `apps/legislature`.** A votação tem chave única no `codigoSessaoVotacao`; o voto, em (votação, código do parlamentar). Normalização como a do ADR 0028: lê a carga mais recente, sem rede; linha inválida ou conflito (inclusive a mesma votação com dados diferentes entre linhas) param tudo; upsert, então a fonte que corrige resultado, ementa ou voto atualiza; **nunca apaga** (votação que saiu da janela fica); comando `normalize_senado_votacoes`; registro em `settings.NORMALIZERS`.
5. **O voto não tem chave para `Senator`.** Guarda código, nome, partido e UF **do momento do voto**. A junção com `Senator` é por código, na leitura.
6. **Votação secreta é gravada com a marca** (`secret`), os totais e os itens como vêm. `Votou` é participação, nunca posição: a interface e a API futuras não podem apresentá-lo como voto. Totais ficam nulos quando a fonte os traz nulos; não são calculados nem preenchidos.
7. **Siglas de voto e resultado são gravados como vêm, sem mapeamento.** O significado de `AP`, `LS`, `P-NRV`, `MIS`, `NCom`, `LP`, `NA`, `LAP` e de `A`/`R` não foi verificado.

## Alternativas
- **Bruto aninhado (uma linha por votação):** descartada; o `JsonListReader` só aceita valor escalar, com tolerância zero.
- **Dois conjuntos (votações e votos):** descartada; 2 requisições por dia e estado de ligação entre eles, sem ganho.
- **Chave estrangeira do voto para `Senator`:** descartada; a carga falharia justamente nos votos de suplentes que saíram da lista (12 códigos além dos 81 em um ano). Custo aceito: 3 campos duplicados por voto.
- **Janela de 30 a 90 dias:** descartada com os números da medição; um ano custa 1,6 MB por dia e traz o histórico na primeira coleta sem código de backfill, além de pegar correções em votos recentes.
- **Ignorar as votações secretas:** descartada pelo dono; some quase metade das votações e a participação.
- **Ignorar a votação sem votos e seguir:** descartada pelo dono; esconderia dado que a fonte publicou.

## Consequências
- Terceira carga sem licença declarada, por decisão do dono. Se o Senado declarar licença ou termos, reconferir (sem checagem automática). Redistribuição e uso comercial ficam no P-16; nada vai a público antes.
- **A coleta diária para se a fonte mandar uma votação anômala** (sem votos, com campo obrigatório vazio, ou código repetido); o motivo fica em `IngestionRun.error_code` e o bruto anterior permanece. É o preço da falha fechada.
- **Risco não coberto por teste:** a ementa é texto livre e o parser compartilhado recusa qualquer caractere de controle, inclusive quebra de linha. Nos 87 registros medidos não há nenhum; se aparecer, a coleta do dia para. Tratar quando acontecer, com teste.
- `rows_read` de cada carga é de ~7 mil linhas (uma por voto); o teto do leitor para este formato é 50.000 (o padrão de 10.000 estouraria perto de 125 votações por ano).
- A janela só olha 360 dias para trás: votação mais antiga que isso só entra com um backfill que não existe (fatia futura, se for preciso).
- A duplicação com o código da lista de senadores e da Câmara continua anotada para refatorar depois.
- Reversível: desabilitar o `Dataset` no admin; as tabelas novas são aditivas (migrações `sources/0009` e `legislature/0004`).
- **Não validado por mim:** o significado das siglas; que `codigoSessaoVotacao` seja estável no tempo (visto em uma coleta); a interpretação jurídica (P-16).
