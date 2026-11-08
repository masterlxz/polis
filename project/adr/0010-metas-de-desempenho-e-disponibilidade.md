# 0010: Metas de desempenho e disponibilidade da Etapa 1 (P-14)

**Data:** 2026-11-08

## Contexto
O PRD §12 deixa "metas quantitativas de disponibilidade, latência, volume e capacidade" a decidir. Elas são insumo da hospedagem (P-04) e da busca (P-06). Hoje não existe página pública nem medição de leitura: o que foi medido é só a ingestão (ADR 0006: leitura com allowlist a 66 a 74 MB/s, pico ≤ 49 MB, com margem de cerca de 6 vezes sobre o critério de 20 minutos) e a primeira carga real do TSE (`consulta-cand-2026`, 42.034 linhas). Não há público nem tráfego medido.

## Decisão
Metas para a **Etapa 1**, a validar e reavaliar quando houver página real e dados reais. São alvos de projeto, não compromisso (SLA) com terceiros.

1. **Disponibilidade da leitura pública:** 99,5% por mês (até cerca de 3,6 h fora do ar). A ingestão e a área administrativa ficam **fora** da meta.
2. **Recuperação:** RPO de 24 h e RTO de 24 h, com backup automático diário do banco e **teste de restauração** periódico (PRD §12). O RPO de 24 h é aceitável porque o dado de fonte é reconstruível por nova carga; o que não é reconstruível (cadastro de correções, ADR 0005 e PRD §17) precisa de backup com a mesma frequência.
3. **Latência**, medida no servidor com o banco carregado no volume-alvo: p95 de página de perfil ≤ 800 ms e p95 de busca simples por nome ≤ 1,5 s.
4. **Capacidade:** 50 requisições por segundo sustentadas na leitura pública.
5. **Volume-alvo:** 100 milhões de linhas no total ao fim da Etapa 1 (TSE, Câmara e Senado), sem particionamento. Esse número é **estimativa minha, não medida**; o spike de ingestão usou 20,57 milhões de linhas sintéticas só para teste de leitura.
6. **Como valida:** teste de carga contra o ambiente de teste com o volume-alvo antes de abrir ao público; resultado registrado em `SESSIONS.md`. Se não atingir, a meta ou a arquitetura muda por ADR novo, nunca em silêncio.

## Alternativas
- **Melhor esforço, sem meta:** mais barato, mas não dá base para escolher hospedagem nem para cobrar monitoramento.
- **99,9% (cerca de 43 min/mês):** exigiria réplica, failover e hospedagem redundante; custo e operação desproporcionais antes de existir público.
- **Latências mais rígidas (p95 de 300 ms para página, 500 ms para busca):** boas para a experiência, mas obrigam cache e índices desde o início, sem medição que mostre que são alcançáveis.
- **Só medir, sem número:** adiaria o P-14 e deixaria P-04 e P-06 sem alvo.

## Consequências
- Cabe em um único servidor com PostgreSQL e backup diário; alta disponibilidade multi-zona não é requisito (insumo do P-04).
- A busca (P-06) precisa de índice que sustente p95 ≤ 1,5 s em 100 milhões de linhas; é o teste decisivo entre `pg_trgm`/`unaccent` (ADR 0006) e busca dedicada.
- Exige monitoramento de disponibilidade e de erros desde a Etapa 0 técnica (PRD §12 e §13), e um teste de restauração agendado.
- **Não verificado:** os números de capacidade e volume são hipóteses; a primeira medição real pode mudá-los.
