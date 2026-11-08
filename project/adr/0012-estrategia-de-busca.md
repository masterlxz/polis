# 0012: Estratégia de busca: PostgreSQL, atrás de um módulo (P-06)

**Data:** 2026-11-08

> **Atualização (2026-11-08):** o spike do ADR 0015 disparou o gatilho (a) da decisão 5. Com dados sintéticos enviesados, 300 mil nomes e 2 vCPU emulados, a busca por trigramas saturou a 3 buscas por segundo (p95 de 1,7 a 13,8 s) contra os 10 por segundo e 1,5 s da meta (ADR 0010). Esta decisão fica **em revisão**: a decisão 1 (só PostgreSQL com `pg_trgm` no modelo medido) não se sustenta como está; ver "Resultado do spike" no ADR 0015. A revisão (token, prefixo, pré-filtro, cache ou busca dedicada) ainda não foi decidida nem testada.

## Contexto
O P-06 pede a estratégia de busca. Entradas: o ADR 0006 (PostgreSQL como único banco da Etapa 1, com `unaccent` e `pg_trgm` anunciados para o P-06), o ADR 0009 (a Etapa 1 inclui "busca simples por nome"), o ADR 0010 (p95 de busca ≤ 1,5 s) e o ADR 0011 (um VPS único, teto de cerca de US$ 20/mês). Duas observações do repositório:

- **O corpus buscável é pequeno.** O ADR 0005 mantém o voto individual só com o id do parlamentar, sem texto. O que se busca na Etapa 1 são pessoas e partidos (ordem de centenas de milhares de linhas, estimativa minha, não medida), não os 100 milhões de linhas do ADR 0010.
- **O índice não pode conter o nome civil.** O ADR 0005 (decisão 8) diz que o nome civil é só interno e que o nome social prevalece. Um índice com o nome civil permitiria descobri-lo por busca.

## Decisão
1. **Busca dentro do PostgreSQL**, sem serviço novo: `unaccent` (ignora acento) e `pg_trgm` (tolera erro de digitação) sobre o nome público, com índice GIN/GiST para o `pg_trgm`. Detalhes de índice e consulta ficam para a implementação, medidos no teste de carga do ADR 0010.
2. **Escopo da Etapa 1:** nome de pessoa (nome de urna, parlamentar ou social) e partido, com UF e partido como filtros. Proposições e ementas (busca de texto em português) entram quando Câmara e Senado entrarem, em decisão própria.
3. **O que entra no índice:** só o nome público (ADR 0005, decisão 8). **O nome civil, a data de nascimento e qualquer campo interno ficam fora do índice**, e um teste deve provar que a busca por um nome civil não encontra a pessoa.
4. **Módulo com interface única:** a busca fica atrás de uma função como `buscar(consulta, filtros)` em um app próprio, para que trocar o motor (busca dedicada) não toque o resto do sistema.
5. **Gatilho de reavaliação:** abrir ADR novo se (a) o teste de carga mostrar p95 de busca acima de 1,5 s com o volume real, ou (b) um conjunto de consultas de referência (nomes com acento, apelidos, homônimos, erro de digitação), definido junto com os testes, não atingir relevância aceitável.
6. **Homônimos:** a busca devolve todos, cada um com contexto (cargo, UF, partido, ano). A busca não decide que dois registros são a mesma pessoa; a ligação entre pessoas é o processo com revisão humana do ADR 0005 (decisão 2).

## Alternativas
- **PostgreSQL + busca dedicada (Meilisearch ou Typesense):** melhor relevância de fábrica, mas mais um serviço, sincronização com o banco (índice pode ficar desatualizado), mais memória no VPS único e mais um ponto de falha. Fica como saída se o gatilho da decisão 5 disparar.
- **OpenSearch/Elasticsearch:** desproporcional e fora do teto de custo do ADR 0011.
- **Incluir proposições e ementas já na Etapa 1:** descartado por escopo; não há ainda dados da Câmara e do Senado carregados.

## Consequências
- Nenhum serviço novo e nenhum custo adicional de infraestrutura; a busca divide CPU e memória com o banco no mesmo VPS.
- Relevância mais básica que a de um motor dedicado: ranking por similaridade de trigramas, sem sinônimos nem peso por popularidade. Aceito para a Etapa 1.
- Exige instalar as extensões `unaccent` e `pg_trgm` no banco (o ADR 0006 as previa); a imagem `postgres:18` do Compose as inclui nas extensões padrão, o que **não foi verificado nesta sessão**.
- Nomes de candidatos são dado pessoal público; expor a busca ao público segue condicionado ao P-16 (PRD §11).
- A "pesquisa avançada" da Etapa 2 reavalia este ADR.
