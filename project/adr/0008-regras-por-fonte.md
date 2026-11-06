# 0008: Regras de uso por fonte (P-15)

**Data:** 2026-11-06

## Contexto
O P-15 pede regras específicas para cada fonte de dados: termos, licenças e limites. As leituras e medições estão em `project/fontes/` (Sessões 18 e 19) e mostram três regimes diferentes, que um conector único não pode tratar como iguais:

| | Câmara | Senado | TSE |
|---|---|---|---|
| Licença nomeada | não encontrada | não encontrada | CC BY nos metadados, **por conjunto** (181 de 190 no portal) |
| Atribuição | não exigida | "citar a fonte" (política do portal; não se liga expressamente à API) | exigida pela CC BY |
| Uso comercial | permitido pelo FAQ | não dito | CC BY não o restringe |
| Limite de taxa | não documentado | 10 req/s documentado | não documentado |
| Recusa observada | 429 (limite de taxa, passou) | nenhuma | 403 em `www.tse.jus.br` (não passou) |

Este ADR cobre licença, atribuição, etiqueta de rede e agendamento. Quais **colunas** entram, retenção e retirada pela fonte já estão no ADR 0005; o modelo `Source`/`Dataset`/`IngestionRun` está no ADR 0007. A interpretação jurídica (LGPD, redistribuição, uso comercial) continua no P-16 e não está validada.

**Lacunas de leitura quando este ADR foi escrito:** as Portarias TSE nº 93/2021 e nº 525/2021 e os termos de uso do TSE não foram lidos (HTTP 403, recusa do servidor). A documentação da API do Senado (Swagger por JavaScript) também não. As decisões 1 a 3 valem com essas lacunas e devem ser reconferidas quando o texto das Portarias for lido.

## Decisão

1. **Portão de licença por conjunto.** Um `Dataset` só é habilitado se a fonte declarou licença para **aquele conjunto**, ou se o dono registrou por escrito a decisão de coletar mesmo assim (com o motivo). A licença do TSE é metadado do conjunto, não do portal: a ausência de `license_id` **não herda** a CC BY dos outros. Hoje, no TSE, ficam fora `comparecimento-e-abstencao-2024`, `comparecimento-e-abstencao-2026` e os logs `gedai` de 2026 (decisão do dono). Câmara e Senado não declaram licença nomeada; a decisão de habilitá-los é do dono, registrada no cadastro (P-15 não a toma por ele).
2. **Mudança de licença para a falha fechada.** Se um conjunto habilitado deixar de declarar a licença com que foi habilitado, a coleta seguinte daquele conjunto para e alerta, como na decisão 6 do ADR 0005. Nada é apagado por isso.
3. **Atribuição uniforme.** Toda tela, exportação e resposta da API pública que use dado de uma fonte mostra o nome da fonte, a data da coleta e o link do original; nos conjuntos do TSE com CC BY, também a licença. Uma regra só, mesmo onde a fonte não a exige (Câmara). Isso cumpre a CC BY (TSE) e a política "citar a fonte" (Senado) sem três regras diferentes.
4. **Identificação do coletor.** `User-Agent` próprio e honesto, com o nome do projeto e a URL do repositório, em toda requisição. Nunca um `User-Agent` de navegador para passar por bloqueio (a Câmara proíbe só robôs que "imitem pessoas", item 22 dos termos do portal).
5. **Etiqueta de rede (valores iniciais, ajustáveis sem mudar a regra).**
   - Em série, sem paralelismo, com pausa mínima de 3 segundos entre requisições (o que foi medido sem problemas nas três fontes). O Senado documenta 10 req/s; ficamos muito abaixo.
   - **429 ou 503:** recuo exponencial respeitando `Retry-After` quando houver; a Câmara manda `retry-after: 30` em todas as respostas, sem significado documentado.
   - **403 ou qualquer bloqueio explícito:** a coleta daquele host para, registra e alerta. **Nunca** se tenta de novo com outra identidade. Quem decide o que fazer é o dono.
   - Câmara: `itens` ≤ 100 (acima disso houve 504).
6. **Agendamento.** Minuto aleatório, nunca horário redondo (a especificação do Senado pede para evitar 00:00, 01:00, 01:15 etc.). Câmara: depois das 08:00 GMT, porque os arquivos são regenerados de madrugada. TSE: os pacotes são regenerados várias vezes ao dia com o mesmo nome, então a mudança é detectada por **SHA-256 do conteúdo** (e `DT_GERACAO`), não por `Last-Modified`.
7. **Canal.** Arquivo em massa para carga completa; API para detalhe e atualização incremental. Nada novo sobre endpoints `deprecated` do Senado (42 de 157, quase todo o grupo `materia`).
8. **Dado pessoal.** Vale o ADR 0005. O Ato da Mesa 45/2012 (Art. 27 § 1º, III) lista "número de documentos de identificação pessoal" como informação pessoal da Câmara, o que reforça descartar o CPF que o detalhe `/deputados/{id}` ainda devolve.
9. **Fora desta decisão (P-16):** se o polis pode redistribuir os dados, exportá-los em massa ou usá-los comercialmente; o Senado não diz nada sobre uso comercial e não se presume. Enquanto o P-16 não validar, nada vai a público (PRD §11).

## Alternativas
- **Uma política de rede única, sem regras por fonte:** descartada. O Senado tem limite documentado e pede evitar horários redondos; o TSE tem arquivos de 1,36 GB e CDN; a Câmara tem `retry-after` sem significado. Uma regra única seria ou frouxa demais ou lenta demais.
- **Licença por fonte (Source), não por conjunto:** descartada. No TSE ela varia entre conjuntos do mesmo portal; um campo por `Source` esconderia justamente os conjuntos sem licença.
- **Coletar os conjuntos do TSE sem licença citando o TSE:** descartada pelo dono. Presumiria uma autorização que o metadado não dá (PRD §8.2). Custo aceito: sem comparecimento e abstenção por ora (agregados, fora da Etapa 1).
- **Atribuição só onde a fonte exige:** descartada pelo dono. Três regras diferentes e risco de esquecer quando uma fonte mudar.
- **Contornar o 403 do TSE trocando o `User-Agent`:** descartada. É burlar uma recusa explícita do servidor; o ambiente também a barrou. Custo aceito: o texto das Portarias depende de leitura humana.
- **Tentar de novo no 403 como no 429:** descartada. 429 pede "mais devagar"; 403 pede "não". Tratá-los igual mascara bloqueio como falha transitória.

## Consequências
- O cadastro precisa de campos novos para a licença e a decisão de habilitar (por exemplo `license_id`, `license_url` e a justificativa do dono em `Dataset`). **Não são criados neste ADR**: entram com o conector, em tarefa própria (plan mode). Hoje o `Dataset` só tem a allowlist (ADR 0007).
- O `error_code` fechado do `IngestionRun` (ADR 0007) não tem um código para "bloqueado pela fonte" nem "licença mudou"; o conector vai precisar acrescentar um ou dois (`blocked`, `license`). Isso exige alterar a lista fechada e a `CheckConstraint`, com migração.
- A interface e a API pública precisam de um componente de atribuição por fonte antes de qualquer tela pública.
- O conector precisa de limitador de taxa, recuo, identificação e agendamento aleatório; testes de contrato cobrem 429, 503 e 403 com respostas simuladas, sem rede.
- **O P-15 só fecha por inteiro quando as Portarias TSE 93 e 525/2021 e os termos de uso do TSE forem lidos.** Se elas disserem algo que contradiga as decisões 1 a 3, este ADR é revisto.
- Os valores numéricos (3 s, 08:00 GMT, `itens` ≤ 100) vêm de medições de um dia só e são iniciais.
