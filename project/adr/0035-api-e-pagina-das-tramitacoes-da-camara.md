# 0035: API e página das tramitações da Câmara: uma rota por proposição, 404 só para proposição conhecida

**Data:** 2026-11-27

## Contexto
O ADR 0034 trouxe as tramitações de 2026 (118.684 linhas em `CamaraPropositionStep`, 46.295 proposições, coleta real na Sessão 113), sem API nem página. A página da votação lista as proposições (ADR 0032, emenda 5) e não tem rota para cada uma. Medido no arquivo de 2026-11-27: **no máximo 98 tramitações por proposição** (mediana 2, p90 6, p99 10); só 9.869 das 26.754 proposições das votações têm tramitação em 2026 (cerca de 37%). A tramitação não tem chave para `CamaraProposition` (ADR 0034, decisão 4): a junção é na leitura.

## Decisão
1. **Rota por proposição:** `GET /internal/v1/camara/proposicoes/<id>/`, com `<id>` em ASCII `[1-9][0-9]{0,9}` (o id da Câmara, que o banco guarda como inteiro e o ADR 0034 grava em texto sem zero à esquerda). Id acima de `2147483647` é 404 **sem consultar o banco**.
2. **404 só para proposição que o polis conhece:** sem linha em `CamaraProposition`, a resposta é 404 **mesmo havendo tramitações** (decisão do dono, 2026-11-27). Nenhuma página chega a essa rota por outro caminho (o link parte da votação), e a API não devolve proposição "sem título". Proposição conhecida **sem** tramitação é 200 com `tramitacoes: []`.
3. **Resposta:** `{"proposicao": {id_camara, titulo, tipo, numero, ano, ementa}, "tramitacoes": [{sequencia, data_hora, orgao, descricao}], "atribuicao_da_proposicao", "atribuicao_das_tramitacoes"}`. `ano` e `ementa` vazios saem `null` (regra do ADR 0032, decisão 6); `sequencia` nula quando a fonte a deixou vazia (1 linha em 2026). Nada de id interno, de `origem` nem da execução.
4. **`data_hora`** em ISO 8601 **com deslocamento** `-03:00`, convertida do `DateTimeField` para `America/Sao_Paulo`. A fonte não declara o fuso (ADR 0034, decisão 7): o `-03:00` é o palpite, e a página diz isso.
5. **Ordem, feita em Python** (no máximo 98 itens): `data_hora` crescente, depois `sequencia` (nula por último), `orgao` e `descricao`. O banco ordenaria os textos pela collation, que varia (ADR 0032, decisão 2).
6. **Atribuições:** `atribuicao_da_proposicao` é a da execução que viu a proposição por último (`CamaraProposition.ingestion_run`); `atribuicao_das_tramitacoes` é a da coleta mais recente entre as tramitações, e **é nula só quando `tramitacoes` é `[]`**.
7. **Consultas:** 200 com tramitações, **2** (proposição com a execução, e tramitações com a execução, ambas por `select_related`); 404 por proposição desconhecida, 1; 404 por formato do id ou int32, 0.
8. **`total_tramitacoes` no detalhe da votação** (emenda 6 do ADR 0032): cada item de `proposicoes` ganha um inteiro `>= 0`, calculado em **uma consulta a mais** (contagem agrupada por `camara_proposition_id`, com `IN` pelos ids da votação; a unicidade do ADR 0034 começa por essa coluna). A consulta **não roda** se a votação não tem proposição. O detalhe com proposições passa de 4 para 5 consultas.
9. **Página `/camara/proposicoes/[id]`:** título, tipo, número e ano, ementa (recolhida como na votação), tabela de tramitações (data e hora em Brasília, órgão, descrição) e atribuições. Texto da fonte sempre escapado. Nota: **só tramitações de 2026; a hora é gravada como Brasília, não verificado**. `sequencia` não é mostrada (sem significado verificado; a ordem já a usa). A votação linka a proposição **só quando `total_tramitacoes > 0`**.
10. **Fora desta fatia:** anos anteriores, `despacho` (ADR 0034), paginação (o máximo medido é 98), busca por tramitação e o acabamento da página da votação (tamanho no pior caso, `origem`).

## Alternativas
- **Embutir as tramitações no detalhe da votação:** descartada; até 213 proposições por votação com até 98 itens cada, contra uma rota que devolve 98 no máximo.
- **`total_tramitacoes` de todas e link sempre:** descartada; 63% das proposições das votações não têm tramitação em 2026 e o link levaria a uma página vazia.
- **`proposicao: null` quando só há tramitações:** descartada pelo dono; mais código na API e na página para um caso que nenhum link alcança.
- **Ordenar no banco:** descartada (collation).
- **Paginar as tramitações:** descartada; o máximo medido é 98 (cerca de 12 KB).
- **Expor `idTramitacao` ou `origem`:** descartada; o primeiro não é chave (ADR 0034) e o segundo não tem significado verificado (ADR 0033).
- **Mostrar `sequencia` na página:** descartada; sem significado verificado, e a ordem já a usa.

## Consequências
- Cobertura de cerca de 37% das proposições das votações até haver anos anteriores; a página diz "tramitações de 2026".
- O contrato do detalhe da votação ganha uma chave por item (emenda 6 do ADR 0032), sem tirar nenhuma.
- A hora pode estar errada se o fuso da fonte não for Brasília; várias tramitações têm `00:00` (só data, não verificado).
- Sem schema novo nem migração. Reversível: tirar a rota, o link e o campo.
- Nada vai a público antes do P-16.
- **Não validado por mim:** o plano das duas consultas com dado real (a medição é de contagem, não de `EXPLAIN`); o tamanho real da resposta no pior caso (estimado em cerca de 12 KB); a página no navegador do dono.

## Emenda 1 (2026-11-28): tramitação em 00:00 de Brasília mostra só a data (P-23)
Mudança só na página (`/camara/proposicoes/<id>`), PR #362. A API não muda: `data_hora` continua um instante ISO 8601 com `-03:00` (decisão 4).
1. **Medido em 2026-11-28 (PC do dono, 118.684 tramitações):** 33.508 (28,2%) estão exatamente em 00:00 de Brasília. Se as horas fossem reais e espalhadas, seriam cerca de 0,07% (1 de 1.440 minutos). A decisão 4 e a decisão 9 previam "hora e data"; o registro já dizia "várias com 00:00 (só data, não verificado)".
2. **Decisão do dono:** a tabela mostra `07/05/2026` quando a hora em Brasília é 00:00, e `07/05/2026 às 16:58` nas demais. A regra olha o **instante convertido para Brasília** (não o texto da API) e vale só na tabela das tramitações: o Senado e a origem dos dados (`coletado_em`) continuam com a hora, porque lá 00:00 é um instante real.
3. **A nota da página diz que é inferência** ("a fonte provavelmente não informou a hora (não verificado)"). A Câmara não confirmou que `00:00` significa "sem hora".
4. **Descartadas:** mostrar sempre a hora e explicar na nota (continua afirmando uma hora que a fonte provavelmente não deu); campo `hora_informada` na API (muda o contrato por uma heurística que a página aplica igual).
5. **Custo aceito:** uma tramitação realmente à meia-noite aparece sem hora (perde a hora, não o dia); um `00:00:30` conta como 00:00 (a tela já corta no minuto). Reversível: voltar a tabela para `dataHoraBrasilia`.
6. **Não verificado:** o significado de `00:00` na fonte; a página no navegador do dono (P-22).
