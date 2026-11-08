# polis: Pendências

Decisões em aberto, vindas do PRD §18 (nome e licença já decididos: ADR 0001 e 0002). Marque como resolvida citando o ADR.

## Em aberto

| ID | Pendência | Observação |
|---|---|---|
| P-09 | Estratégia de autenticação | |
| P-11 | Modelo de financiamento e sustentabilidade | |
| P-16 | Interpretações jurídicas que exijam validação especializada | LGPD e dados de processos judiciais. Pesquisa de apoio (sem parecer) em `lgpd-lai.md`, Sessão 27; as 6 perguntas seguem abertas e o dono decidiu não levar a advogado por ora. Pergunta sobre o CPF de 2026 enviada ao TSE em 2026-11-07, aguardando resposta |

## Resolvidas

| ID | Pendência | Resolução |
|---|---|---|
| (nome) | Nome definitivo do projeto | polis, ADR 0001 |
| (licença) | Licença e estratégia de código aberto | AGPL-3.0, ADR 0002 |
| (repo) | Dono e visibilidade do repositório | masterlxz, público, ADR 0003 |
| P-08 | Provedores e modelos de IA, RAG, embeddings e custos | ADR 0018 (2026-11-08), só princípios: IA só na Etapa 4; regras do PRD §10.1 como requisitos; citação verificada por código; sem SQL livre; conteúdo externo como dado; API externa só com dado público (exceção ao "tudo no Brasil", a confirmar no P-16); interface única de provedor; limite de custo antes de abrir. **Fica aberto:** provedor, modelo, embeddings, RAG, orçamento e qualidade em português. Nada foi medido |
| P-07 | Estratégia de armazenamento de documentos | ADR 0017 (2026-11-08), só princípios: Etapa 1 sem arquivos de terceiros; padrão link + SHA-256 sem cópia; cópia só por fonte, com licença que permita e motivo concreto; interface única de armazenamento; conteúdo externo não confiável. **Fica aberto:** backend concreto (disco ou objetos S3-compatível no Brasil, ADR próprio na primeira fonte que exigir cópia), modelo de dados, extração de texto e limites. Nenhuma fonte de documentos foi medida |
| P-04 | Arquitetura de implantação e hospedagem | ADR 0011 (2026-11-08): VPS único com Docker Compose (Django, PostgreSQL 18, proxy), servidor e backups no Brasil, teto de cerca de US$ 20/mês. Provedor e plano ficam para a implantação, com preço conferido na página oficial. Risco aberto: o volume-alvo pode não caber no teto; o teste de carga do ADR 0010 decide |
| P-06 | Estratégia de busca | ADR 0012 (2026-11-08) depois revisto pelo ADR 0016 (mesmo dia): busca por tokens no PostgreSQL (`tsvector` 'simple' com prefixo) com `pg_trgm` 0,5 só como reserva; medida em 2 vCPU emulados: p95 de 154 ms a 10 buscas/s, relevância de 99% com um erro de digitação. Sem cache e sem busca dedicada (Meilisearch reprovou a relevância: 64% com erro). Nome civil fora do índice e módulo com interface única continuam. **Fica aberto:** nada medido fora de dados sintéticos e de uma máquina de desenvolvimento; reavaliar com consultas reais |
| P-10 | Necessidade e formato da API pública, política de uso e limites | ADR 0013 (2026-11-08): sem API pública na Etapa 1; lançamento previsto na Etapa 2 como leitura anônima com limite por IP, depois do P-16. Política: somente leitura, `/api/v1`, atribuição em toda resposta, mesmo filtro de dados da interface. **Fica aberto:** os números de limite (saem do teste de carga), a biblioteca da API e, se o limite por IP não bastar, a API com chave (depende do P-09) |
| P-17 | Identidade visual, linguagem da marca e domínio | ADR 0014 (2026-11-08): "polis" sempre com descritor; linguagem simples e neutra; sem cores ou símbolos partidários ou da bandeira como identidade; critérios de domínio (`.br`, sem confundir com `pol.is`). **Fica aberto:** logotipo e paleta concretos, e a verificação e compra do domínio na implantação (do dono); registro de marca não avaliado |
| P-18 | Design e navegação definitivos | ADR 0015 (2026-11-08): navegação da Etapa 1 só com o que tem conteúdo; origem e data em todo dado; WCAG 2.2 AA; front-end em Next.js separado (escolha do dono contra a recomendação, substitui parcialmente o ADR 0006) com API interna. **Spike feito em 2026-11-08 (resultado no ADR 0015):** o Next.js acrescentou cerca de 340 MiB e a página ficou em p95 de ~13 ms a 50 req/s em 2 vCPU emulados; a condição está atendida para o Next.js. O que falhou foi a busca (ver P-06), não o front-end. Nada foi medido fora de uma máquina de desenvolvimento |
| P-13 | Priorização final dos módulos | ADR 0009 (2026-11-08): ordem das etapas do PRD §15 mantida; Etapa 1 fatiada na vertical, TSE de ponta a ponta (normalização, pessoa e candidatura, página de candidato, busca simples) antes de Câmara e Senado. Reavaliar da Etapa 2 em diante ao fim da Etapa 1 |
| P-14 | Metas quantitativas de desempenho e disponibilidade | ADR 0010 (2026-11-08), metas da Etapa 1 a validar: leitura pública 99,5%/mês, RPO e RTO de 24 h, p95 de página ≤ 800 ms e de busca ≤ 1,5 s, 50 req/s, 100 milhões de linhas (estimativa, não medida). Reavaliar com a primeira medição real |
| P-02 | Stack e versões definitivas | Python 3.14 + Django 6.1 (migrar para o 6.2 LTS em abril de 2027), ADR 0006. Spike de ingestão atendeu o critério com folga de cerca de 6 vezes; versões conferidas em 2026-11-05 |
| P-03 | Estrutura final do repositório | Monorepo (o próprio `polis`), ADR 0006 |
| P-05 | Banco de dados e tecnologias complementares | PostgreSQL 18, único banco da Etapa 1, ADR 0006. Busca textual segue no P-06 |
| P-12 | Política de retenção e minimização de dados pessoais | ADR 0005: allowlist de colunas por fonte, sem CPF nem título, nome civil e data completa só internos, lápide para retirada pela fonte, bruto filtrado com 3 cargas. Validação jurídica segue no P-16 |
| P-19 | CI de testes e `dependabot.yml` | Job `tests` (PR #14) exigido no ruleset (Sessão 10); `dependabot.yml` (PR #16) com security updates já ligados (Sessão 2). Conferido em 2026-11-06 que o Dependabot leu o arquivo: os runs `uv` e `github_actions` terminaram com sucesso e abriram o PR #17. Exceção ao ADR 0006 do workspace, confirmada pelo dono. Docker Compose não era parte do P-19 |
| P-15 | Regras específicas para cada fonte de dados | ADR 0008 (Sessão 20): portão de licença por conjunto, atribuição uniforme, etiqueta de rede, agendamento. Fechado na Sessão 22 (2026-11-07) depois da leitura das Portarias TSE 93 e 525/2021 e da Política de Privacidade do TSE (texto colado pelo dono, nenhuma contradiz o ADR). Fontes em `fontes/camara.md`, `senado.md`, `tse.md`. **Fica fora:** o Anexo da Portaria 525/2021 (Plano de Dados Abertos 2021-2023, vigência encerrada, dispensado); o CPF de 2026 do TSE, que contradiz o `leiame` (perguntar ao TSE no P-16); uso comercial e redistribuição (P-16) |
| P-01 | Política de contribuição: CLA ou DCO | DCO, ADR 0004. `CONTRIBUTING.md` e job `dco` no CI feitos e `dco` exigido no ruleset (Sessão 2, partes 3 e 4). PR externo de código já pode ser aceito do ponto de vista da política |
