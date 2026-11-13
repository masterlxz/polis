# 0028: Senado: lista de senadores em exercício, `Senator` próprio, coleta por decisão do dono

**Data:** 2026-11-13

## Contexto
O Senado não nomeia licença nem declara termos para a API (`fontes/senado.md`, leituras de 2026-11-05 e 06). A política do portal pede citar a fonte; o uso comercial não é dito e nenhuma fonte lida a liga expressamente à API. O ADR 0008 (decisão 1) só deixa habilitar um conjunto sem licença declarada por decisão escrita do dono; a decisão 9 deixa redistribuição e uso comercial para o P-16 e impede que algo vá a público antes.

A lista `GET /senador/lista/atual.json` (81 senadores, medida de novo em 2026-11-12) é uma resposta única, aninhada (`ListaParlamentarEmExercicio.Parlamentares.Parlamentar[].IdentificacaoParlamentar`), sem paginação, e o código do parlamentar vem como **texto**. A API responde 200 com corpo vazio para "não existe" (medido).

## Decisão
1. **Habilitar só `senado/senadores`**, por decisão do dono, no admin (`license_basis = owner_decision`). O cadastro (`seed_sources`) nunca habilita nem copia a justificativa. Uma requisição por dia, só depois das 08:00 GMT, pelo cliente educado (ADR 0008, decisões 4 e 5).
2. **Allowlist de 4 campos:** `CodigoParlamentar`, `NomeParlamentar`, `SiglaPartidoParlamentar`, `UfParlamentar`. Descartados na leitura: nome completo (civil, ADR 0005), e-mail, telefones, foto, suplentes, mandato e bloco.
3. **Formato `json_senado`** (`apps/sources/json_senado.py`): desembrulha o envelope num arquivo `{"dados": [...]}` ordenado pelo código (mesmo conteúdo, mesmo SHA-256) e o resto do pipeline é o da Câmara. Envelope ausente, lista vazia, item sem identificação, código repetido, arquivo grande ou itens demais **recusam a carga**: uma lista vazia aceita marcaria todos como fora da lista.
4. **`Senator` próprio** em `apps/legislature`, fora de `Person` e de `Deputy` (mesmo motivo do ADR 0022). Chave única: só o código do parlamentar (o mandato atravessa duas legislaturas). Saída do exercício como no ADR 0027 (`in_office`, `left_list_at` = início da coleta, só a carga mais recente mexe, nunca apaga, sem disjuntor). Sem lápide (ADR 0026 é só TSE).
5. **API interna** `GET /internal/v1/senadores/<codigo>/`: lista explícita de chaves, atribuição "Senado Federal: Dados Abertos" com a data da coleta. Nada público antes do P-16.
6. **Justificativa para o admin (campo `license_justification`):** "Decisão do dono em 2026-11-13: o Senado não declara licença; a política do portal pede só citar a fonte; dado de parlamentar em exercício é de interesse público; só a lista de senadores com allowlist de 4 campos, sem dado pessoal; atribuição obrigatória; uso comercial não presumido; nada público antes do P-16 (ADR 0008, decisão 9; ADR 0028)."

## Alternativas
- **Generalizar `Deputy` (casa e id de origem):** descartada; as chaves diferem (legislatura e id da Câmara contra só o código) e mexeria na API e nos testes da Câmara.
- **Coletar mais campos (mandato, nome completo, contato):** descartada; sem uso hoje e amplia o dado pessoal.
- **Não coletar até o P-16:** descartada pelo dono, como no ADR 0021.
- **Formato `json` da Câmara:** descartado; ele espera páginas planas, e esta resposta é única e aninhada.

## Consequências
- Segunda fonte sem licença declarada coletada. Se o Senado passar a declarar licença ou termos, esta decisão é reconferida (não há checagem automática).
- O bruto guarda tudo como texto, então o parser do Senado converte o código. O leitor JSON é o mesmo da Câmara; ver o problema abaixo.
- **Não validado por mim:** a aplicação da política do portal aos dados da API; a interpretação jurídica é do P-16. O significado de `em_exercicio: false` é o do ADR 0027 (pode ser licença, titular de volta ou fim de mandato).
- Dá para ter dois ids legados e novos no Senado (processo e matéria) quando entrarem votações; esta fatia usa só o código do parlamentar.
- A duplicação com o código da Câmara fica anotada para refatorar depois.
- Reversível: desabilitar o `Dataset` no admin; as cargas seguem a retenção de 3 execuções.
- **Achado da sessão, fora desta decisão:** o `parse_row` da Câmara exige `id` inteiro, mas o leitor grava texto; nada rodou de ponta a ponta com a Câmara. Corrigir num PR próprio.
