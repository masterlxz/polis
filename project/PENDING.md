# polis: Pendências

Decisões em aberto, vindas do PRD §18 (nome e licença já decididos: ADR 0001 e 0002). Marque como resolvida citando o ADR.

## Em aberto

| ID | Pendência | Observação |
|---|---|---|
| P-07 | Estratégia de armazenamento de documentos | |
| P-08 | Provedores e modelos de IA, RAG, embeddings e custos | |
| P-09 | Estratégia de autenticação | |
| P-10 | Necessidade e formato da API pública, política de uso e limites | |
| P-11 | Modelo de financiamento e sustentabilidade | |
| P-16 | Interpretações jurídicas que exijam validação especializada | LGPD e dados de processos judiciais. Pesquisa de apoio (sem parecer) em `lgpd-lai.md`, Sessão 27; as 6 perguntas seguem abertas e o dono decidiu não levar a advogado por ora. Pergunta sobre o CPF de 2026 enviada ao TSE em 2026-11-07, aguardando resposta |
| P-17 | Identidade visual, linguagem da marca e domínio | O nome polis tem homônimo conhecido (`pol.is`), ver ADR 0001 |

## Resolvidas

| ID | Pendência | Resolução |
|---|---|---|
| (nome) | Nome definitivo do projeto | polis, ADR 0001 |
| (licença) | Licença e estratégia de código aberto | AGPL-3.0, ADR 0002 |
| (repo) | Dono e visibilidade do repositório | masterlxz, público, ADR 0003 |
| P-04 | Arquitetura de implantação e hospedagem | ADR 0011 (2026-11-08): VPS único com Docker Compose (Django, PostgreSQL 18, proxy), servidor e backups no Brasil, teto de cerca de US$ 20/mês. Provedor e plano ficam para a implantação, com preço conferido na página oficial. Risco aberto: o volume-alvo pode não caber no teto; o teste de carga do ADR 0010 decide |
| P-06 | Estratégia de busca | ADR 0012 (2026-11-08): só PostgreSQL (`unaccent` + `pg_trgm`) atrás de um módulo com interface única; Etapa 1 busca nome público de pessoa e partido; nome civil fora do índice. Gatilho de reavaliação: p95 > 1,5 s ou relevância insuficiente |
| P-18 | Design e navegação definitivos | ADR 0015 (2026-11-08): navegação da Etapa 1 só com o que tem conteúdo; origem e data em todo dado; WCAG 2.2 AA; front-end em Next.js separado (escolha do dono contra a recomendação, substitui parcialmente o ADR 0006) com API interna. **Condição aberta:** spike de memória e latência no VPS único antes de implementar; se não couber, volta a Django templates |
| P-13 | Priorização final dos módulos | ADR 0009 (2026-11-08): ordem das etapas do PRD §15 mantida; Etapa 1 fatiada na vertical, TSE de ponta a ponta (normalização, pessoa e candidatura, página de candidato, busca simples) antes de Câmara e Senado. Reavaliar da Etapa 2 em diante ao fim da Etapa 1 |
| P-14 | Metas quantitativas de desempenho e disponibilidade | ADR 0010 (2026-11-08), metas da Etapa 1 a validar: leitura pública 99,5%/mês, RPO e RTO de 24 h, p95 de página ≤ 800 ms e de busca ≤ 1,5 s, 50 req/s, 100 milhões de linhas (estimativa, não medida). Reavaliar com a primeira medição real |
| P-02 | Stack e versões definitivas | Python 3.14 + Django 6.1 (migrar para o 6.2 LTS em abril de 2027), ADR 0006. Spike de ingestão atendeu o critério com folga de cerca de 6 vezes; versões conferidas em 2026-11-05 |
| P-03 | Estrutura final do repositório | Monorepo (o próprio `polis`), ADR 0006 |
| P-05 | Banco de dados e tecnologias complementares | PostgreSQL 18, único banco da Etapa 1, ADR 0006. Busca textual segue no P-06 |
| P-12 | Política de retenção e minimização de dados pessoais | ADR 0005: allowlist de colunas por fonte, sem CPF nem título, nome civil e data completa só internos, lápide para retirada pela fonte, bruto filtrado com 3 cargas. Validação jurídica segue no P-16 |
| P-19 | CI de testes e `dependabot.yml` | Job `tests` (PR #14) exigido no ruleset (Sessão 10); `dependabot.yml` (PR #16) com security updates já ligados (Sessão 2). Conferido em 2026-11-06 que o Dependabot leu o arquivo: os runs `uv` e `github_actions` terminaram com sucesso e abriram o PR #17. Exceção ao ADR 0006 do workspace, confirmada pelo dono. Docker Compose não era parte do P-19 |
| P-15 | Regras específicas para cada fonte de dados | ADR 0008 (Sessão 20): portão de licença por conjunto, atribuição uniforme, etiqueta de rede, agendamento. Fechado na Sessão 22 (2026-11-07) depois da leitura das Portarias TSE 93 e 525/2021 e da Política de Privacidade do TSE (texto colado pelo dono, nenhuma contradiz o ADR). Fontes em `fontes/camara.md`, `senado.md`, `tse.md`. **Fica fora:** o Anexo da Portaria 525/2021 (Plano de Dados Abertos 2021-2023, vigência encerrada, dispensado); o CPF de 2026 do TSE, que contradiz o `leiame` (perguntar ao TSE no P-16); uso comercial e redistribuição (P-16) |
| P-01 | Política de contribuição: CLA ou DCO | DCO, ADR 0004. `CONTRIBUTING.md` e job `dco` no CI feitos e `dco` exigido no ruleset (Sessão 2, partes 3 e 4). PR externo de código já pode ser aceito do ponto de vista da política |
