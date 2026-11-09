# 0016: Busca por tokens no PostgreSQL, com trigramas como reserva (P-06, revisão do ADR 0012)

**Data:** 2026-11-08

## Contexto
O ADR 0012 decidiu busca só em PostgreSQL com `pg_trgm`. O spike do Next.js (ADR 0015) mostrou que essa consulta satura a 3 buscas por segundo em 2 vCPU emulados (p95 de 1,7 a 13,8 s), contra a meta do ADR 0010: 10 buscas por segundo (20% de 50 req/s) com p95 ≤ 1,5 s. O P-06 voltou a "Em aberto". Um segundo spike (branch `spike/busca`, `spikes/nextjs/`, **nunca na `main`**, ADR 0006) mediu cinco variantes sobre os mesmos 300 mil nomes sintéticos: relevância (recall) e latência sob carga. Critério acordado com o dono: p95 ≤ 1,5 s a 10 buscas/s em 2 vCPU **e** a pessoa certa no top 10 em ≥ 95% das consultas exatas e sem acento e ≥ 80% com um erro de digitação (percentuais propostos por este assistente e aceitos pelo dono).

## Resultados do spike

**Relevância** (100 alvos × 4 tipos de consulta por variante, mesmos alvos; sucesso = algum dos 10 primeiros resultados tem exatamente o nome do alvo, porque há homônimos):

| Variante | exato | sem acento | 1 erro de digitação | prefixo parcial | Mediana sem carga (exato) |
|---|---|---|---|---|---|
| V0 `pg_trgm`, limiar 0,3 (ADR 0012) | 100% | 100% | 99% | 80% | 424 ms |
| V1 `pg_trgm`, limiar 0,5 | 100% | 100% | 99% | 70% | 94 ms |
| V1w `word_similarity`, 0,5 | 100% | 100% | 89% | 77% | 132 ms |
| **V2 tokens (`tsvector` 'simple', prefixo) + reserva `pg_trgm` 0,5** | 100% | 100% | **99%** | **88%** | **29 ms** |
| V4 Meilisearch v1.55.0 | 100% | 100% | **64%** (300 alvos: 64,3%) | **2%** (300 alvos: 4,3%) | 8 ms |

**Latência sob carga** (só buscas, 10/s, 60 s medidos, 3 repetições, 2 vCPU emulados, 0 erros em todas, load do host registrado por rodada):

| Caso | p95 (mediana das 3) | p99 | Memória máx. (db / Django) |
|---|---|---|---|
| **V2** | **154 ms** | 430 a 520 ms | 151 / 100 MiB |
| V1 | 1.848 ms (reprova) | 2,9 a 3,3 s | 178 / 100 MiB |
| V4 | 13,8 ms | ~16 ms | 123 / 102 MiB, mais ~200 MiB do Meilisearch |
| V2 + cache, tráfego uniforme | 156 ms | | sem ganho |
| V2 + cache, tráfego Zipf (**suposição**) | 135 ms | | ganho de ~12% |
| V1 + cache, tráfego Zipf (**suposição**) | 468 ms | | |
| V2 a 20 buscas/s | 166 a 182 ms | 359 a 462 ms | folga confirmada |

Sem o índice de tokens, uma consulta comum passou de 53 ms para 158 ms em um núcleo (o teste enxerga o índice, mas o efeito é menor que o do `pg_trgm`). O Meilisearch tem a menor latência, mas **reprova o critério de relevância** (64% com um erro de digitação, contra o mínimo de 80%); as causas prováveis são regras próprias dele (limite de tamanho de palavra para aceitar erro e prefixo só na última palavra), **não verificadas na documentação**.

## Decisão
1. **Busca por tokens no PostgreSQL (variante V2)** substitui a decisão 1 do ADR 0012: coluna `tsvector` (configuração `simple`, sem acento, gerada a partir do **nome público** apenas) com índice GIN; a consulta vira palavras com prefixo ligadas por E; ordem: nome igual à consulta primeiro, depois o mais curto. **Reserva:** se vierem menos de 5 resultados (por exemplo, erro de digitação), cai em `pg_trgm` com limiar 0,5.
2. **Sem cache e sem serviço de busca dedicado na Etapa 1.** O cache não é necessário para a meta e seu ganho depende de uma suposição sobre repetição de consultas; a busca dedicada foi mais rápida, mas reprova a relevância e acrescenta um serviço (ADR 0011).
3. **Continuam valendo do ADR 0012:** nome civil e campos internos fora do índice, com um teste que prove que buscar o nome civil não encontra a pessoa; módulo com interface única `buscar(consulta, filtros)`; escopo da Etapa 1 (nome público de pessoa e partido).
4. **Gatilhos de reavaliação** (substituem os do ADR 0012): p95 acima de 1,5 s no teste de carga com o volume real, ou relevância abaixo do critério acima num conjunto de consultas reais ou de referência. A busca dedicada (V4) volta à mesa se a relevância exigir tolerância a erro e prefixo que o PostgreSQL não dê, depois de verificar a configuração dela.

## Alternativas
- **Manter `pg_trgm` com limiar 0,3 (V0):** reprova a latência (mediana de 424 ms sem carga e saturação a 3 buscas/s).
- **`pg_trgm` com limiar 0,5 (V1) ou `word_similarity` (V1w):** V1 reprova o p95 sob carga (1,8 s); V1w perde relevância (89% com erro).
- **Meilisearch (V4):** menor latência, mas reprova a relevância com erro de digitação e prefixo, e acrescenta cerca de 200 MiB e um serviço para sincronizar. Licença conferida na fonte: MIT para a edição comunitária e BUSL 1.1 para partes Enterprise (`MIT AND BUSL-1.1`), de modo que só a edição comunitária seria usada. O Typesense (GPL-3.0, índice em memória) não foi medido.
- **Cache de consultas (V3):** sem ganho com tráfego uniforme e ganho pequeno sob Zipf; adiado até haver tráfego real.

## Consequências
- Cabe no VPS único do ADR 0011 sem serviço novo; memória medida de banco e Django somada abaixo de 300 MiB sob a carga testada.
- O caminho de reserva (consulta com erro de digitação) continua mais caro; os p99 de 430 a 520 ms vêm dele. Se o tráfego real tiver muita digitação errada, isso aparece primeiro.
- A V2 não busca no meio de uma palavra nem corrige erro no início dela; "prefixo parcial" ficou em 88%, abaixo do 99% de erro de digitação, e é o ponto fraco restante.
- Exige `unaccent` no índice (função envoltória imutável, como no ADR 0012); a imagem `postgres:18` as incluiu no spike (verificado ali).
- **Implementado na Sessão 47 (2026-11-09):** migração `apps/elections/migrations/0002_busca_por_tokens.py` (extensões `unaccent` e `pg_trgm`, função `f_busca_normaliza` declarada `IMMUTABLE` por promessa nossa, coluna gerada `public_name_tsv`, índices GIN de tokens e de trigramas; a reversão apaga só os objetos nossos e deixa as extensões), `apps/elections/search.py` e `GET /internal/v1/busca/?q=`.
  - **Índice e consulta tokenizam pela mesma regra** (tudo fora de `[a-z0-9]` vira espaço, nos dois lados). O parser do `to_tsvector` sozinho pode juntar `DR.JOAO` num token só; nos dados reais, 945 de 20.989 nomes têm ponto. Teste e mutação cobrem isso.
  - **Nome social fora do índice** (decisão do dono, 2026-11-09): corrige a frase "ou social" do ADR 0012, decisão 2.
  - **Limites da consulta:** mínimo de 2 caracteres úteis (decisão do dono), teto de 100 caracteres e 10 palavras, no máximo 20 resultados (o maior grupo de homônimos real tem 6).
  - **`buscar(consulta)` ainda sem `filtros`:** UF e partido como filtro ficam para a fatia deles.
  - **Não verificado:** a consulta tira acento em Python (`unicodedata`) e o índice no banco (`unaccent`); letras como `ø`, `æ` e `ß` o `unaccent` trata e o Python não, e não medi se existem nos nomes reais.
- **Não verificado:** dados sintéticos e enviesados de propósito (nomes comuns repetem muito); máquina de desenvolvimento, não VPS; 2 vCPU/4 GB é hipótese; recall por nome ignora a ordem entre homônimos; 100 alvos por variante (a V4 também com 300); nenhuma consulta real; os limiares 0,5 e o corte de 5 resultados da reserva não foram otimizados; tráfego Zipf é suposição.
