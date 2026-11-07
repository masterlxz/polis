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

**Lacunas de leitura quando este ADR foi escrito:** as Portarias TSE nº 93/2021 e nº 525/2021 e os termos de uso do TSE não foram lidos (HTTP 403, recusa do servidor). A documentação da API do Senado (Swagger por JavaScript) também não. As decisões 1 a 3 valem com essas lacunas e devem ser reconferidas quando o texto das Portarias for lido. **Reconferido em 2026-11-07:** as três foram lidas e não contradizem as decisões (ver Consequências).

## Decisão

1. **Portão de licença por conjunto.** Um `Dataset` só é habilitado se a fonte declarou licença para **aquele conjunto**, ou se o dono registrou por escrito a decisão de coletar mesmo assim (com o motivo). A licença do TSE é metadado do conjunto, não do portal: a ausência de `license_id` **não herda** a CC BY dos outros. Hoje, no TSE, ficam fora os **9 conjuntos** do portal sem `license_id` (lista em `fontes/tse.md`: comparecimento e abstenção de 2022, 2024 e 2026, resultados suplementares, mesários de 2022, correspondência de urnas e os logs `gedai` de 2026), por decisão do dono. Câmara e Senado não declaram licença nomeada; a decisão de habilitá-los é do dono, registrada no cadastro (P-15 não a toma por ele).
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
8. **Dado pessoal.** Vale o ADR 0005. O `leiame.pdf` do TSE diz que o CPF "não será divulgado" (Res. TSE 23.609/2019, art. 33 § 2º), embora o CSV de 2026 o traga preenchido: o CPF nunca é tratado como dado que o TSE autorizou publicar. O Ato da Mesa 45/2012 (Art. 27 § 1º, III) lista "número de documentos de identificação pessoal" como informação pessoal da Câmara, o que reforça descartar o CPF que o detalhe `/deputados/{id}` ainda devolve.
9. **Fora desta decisão (P-16):** se o polis pode redistribuir os dados, exportá-los em massa ou usá-los comercialmente; o Senado não diz nada sobre uso comercial e não se presume. Enquanto o P-16 não validar, nada vai a público (PRD §11).

## Alternativas
- **Uma política de rede única, sem regras por fonte:** descartada. O Senado tem limite documentado e pede evitar horários redondos; o TSE tem arquivos de 1,36 GB e CDN; a Câmara tem `retry-after` sem significado. Uma regra única seria ou frouxa demais ou lenta demais.
- **Licença por fonte (Source), não por conjunto:** descartada. No TSE ela varia entre conjuntos do mesmo portal; um campo por `Source` esconderia justamente os conjuntos sem licença.
- **Coletar os conjuntos do TSE sem licença citando o TSE:** descartada pelo dono. Presumiria uma autorização que o metadado não dá (PRD §8.2). Custo aceito: sem comparecimento e abstenção por ora (agregados, fora da Etapa 1).
- **Atribuição só onde a fonte exige:** descartada pelo dono. Três regras diferentes e risco de esquecer quando uma fonte mudar.
- **Contornar o 403 do TSE trocando o `User-Agent`:** descartada. É burlar uma recusa explícita do servidor; o ambiente também a barrou. Custo aceito: o texto das Portarias depende de leitura humana.
- **Tentar de novo no 403 como no 429:** descartada. 429 pede "mais devagar"; 403 pede "não". Tratá-los igual mascara bloqueio como falha transitória.

## Consequências
- O cadastro precisa de campos novos para a licença e a decisão de habilitar (por exemplo `license_id`, `license_url` e a justificativa do dono em `Dataset`). **Não são criados neste ADR**: entram com o conector, em tarefa própria (plan mode). **Feito na Sessão 23 (2026-11-07):** `Dataset.license_basis` (`none`, `declared`, `owner_decision`), `license_id`, `license_url`, `license_justification` e a `CheckConstraint` `dataset_enabled_requires_license_basis` (habilitado exige `declared` com `license_id`, ou `owner_decision` com justificativa).
- O `error_code` do `IngestionRun` (ADR 0007) ganhou `blocked` e `license` na Sessão 23 (migração `0002`). A comparação "a licença mudou" (decisão 2) ainda é do conector.
- A interface e a API pública precisam de um componente de atribuição por fonte antes de qualquer tela pública.
- O conector precisa de limitador de taxa, recuo, identificação e agendamento aleatório; testes de contrato cobrem 429, 503 e 403 com respostas simuladas, sem rede. **Feito na Sessão 24 (2026-11-07), sem o agendamento:** `apps/sources/http_client.py` (`PoliteClient`), só `urllib`, testado contra um servidor HTTP local. Escolhas que o ADR não fixava: 4 tentativas e teto de 300 s no recuo; 401 e 451 contam como bloqueio, como o 403; 502 e 504 **não** recuam (só 429 e 503, como no ADR); todo 3xx é recusado; só https. O bloqueio vale por instância do cliente; gravá-lo (`blocked`) é da camada que liga ao `IngestionRun`.
- **Leituras que faltavam (feitas em 2026-11-07, texto colado pelo dono):** a Portaria TSE 93/2021 define dados abertos como os sob "licença aberta" com atribuição como única condição, sem nomear licença; a 525/2021 só aprova o plano (o Anexo não foi lido, vigência encerrada); a Política de Privacidade do TSE não trata de reuso. Nenhuma contradiz as decisões 1 a 3; a 93 apoia as decisões 1 e 3. Detalhes em `fontes/tse.md`. Os textos vieram de cópia manual e a página da 93 avisa que não substitui o DJE-TSE. Se um texto oficial contradisser as decisões, este ADR é revisto.
- Os valores numéricos (3 s, 08:00 GMT, `itens` ≤ 100) vêm de medições de um dia só e são iniciais.
