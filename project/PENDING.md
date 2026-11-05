# polis: Pendências

Decisões em aberto, vindas do PRD §18 (nome e licença já decididos: ADR 0001 e 0002). Marque como resolvida citando o ADR.

## Em aberto

| ID | Pendência | Observação |
|---|---|---|
| P-02 | Stack e versões definitivas | Depois de medir as fontes. Insumos da Câmara e do Senado em `fontes/`; falta o TSE. As duas fontes diferem (arquivos anuais e API paginada na Câmara; API sem paginação, limite de 10 req/s e depreciação em curso no Senado) |
| P-03 | Estrutura final do repositório | Monorepo ou separado; depende de P-02 |
| P-04 | Arquitetura de implantação e hospedagem | |
| P-05 | Banco de dados e tecnologias complementares | |
| P-06 | Estratégia de busca | |
| P-07 | Estratégia de armazenamento de documentos | |
| P-08 | Provedores e modelos de IA, RAG, embeddings e custos | |
| P-09 | Estratégia de autenticação | |
| P-10 | Necessidade e formato da API pública, política de uso e limites | |
| P-11 | Modelo de financiamento e sustentabilidade | |
| P-12 | Política definitiva de retenção de dados | LGPD |
| P-13 | Priorização final dos módulos | |
| P-14 | Metas quantitativas de desempenho e disponibilidade | |
| P-15 | Regras específicas para cada fonte de dados | Termos, licenças, limites; primeiro TSE, Câmara e Senado. Câmara e Senado medidos em 2026-11-05 (`fontes/camara.md`, `fontes/senado.md`); falta o TSE. Pendente da Câmara: licença explícita e leitura do Ato da Mesa 45/2012. Pendente do Senado: confirmar se a política de uso do portal (citar a fonte) vale para a API, e o uso comercial, que ele não declara |
| P-16 | Interpretações jurídicas que exijam validação especializada | LGPD e dados de processos judiciais |
| P-17 | Identidade visual, linguagem da marca e domínio | O nome polis tem homônimo conhecido (`pol.is`), ver ADR 0001 |
| P-18 | Design e navegação definitivos | |
| P-19 | CI de testes e `dependabot.yml` | Só depois da stack; hoje só o `guard` e o `dco` rodam. Security updates já ligados (Sessão 2) |

## Resolvidas

| ID | Pendência | Resolução |
|---|---|---|
| (nome) | Nome definitivo do projeto | polis, ADR 0001 |
| (licença) | Licença e estratégia de código aberto | AGPL-3.0, ADR 0002 |
| (repo) | Dono e visibilidade do repositório | masterlxz, público, ADR 0003 |
| P-01 | Política de contribuição: CLA ou DCO | DCO, ADR 0004. `CONTRIBUTING.md` e job `dco` no CI feitos e `dco` exigido no ruleset (Sessão 2, partes 3 e 4). PR externo de código já pode ser aceito do ponto de vista da política |
