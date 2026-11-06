# polis: Visão geral

## O que é
Plataforma aberta de transparência e inteligência cívica: unifica informações públicas sobre o Brasil (pessoas, instituições, eleições, legislativo, executivo, judiciário, finanças públicas, fiscalização, políticas públicas) com rastreabilidade até a fonte. A IA é camada de pesquisa, nunca fonte primária. Detalhes no `PRD.md`.

## Stack
Decidida no ADR 0006 (2026-11-05): **Python 3.14 + Django 6.1** (migrar para o 6.2 LTS em abril de 2027), **PostgreSQL 18**, monorepo, páginas renderizadas no servidor, ingestão como comandos do projeto. Ainda em aberto, cada um com ADR próprio: hospedagem, busca, documentos, IA, autenticação, API pública, fila e agendamento. O esqueleto do projeto Django existe desde a Sessão 9 (`config/`, `tests/`, job `tests` no CI). Desde a Sessão 15 há o app `apps/sources` (`Source`, `Dataset` com a allowlist do ADR 0005 e `IngestionRun` imutável); ainda não há conectores, ingestão nem modelos de pessoa ou votação. Nomes de modelos e campos em inglês no código, em português na interface.

## Licença
Código: AGPL-3.0 (ADR 0002). Dados: conforme os termos de cada fonte.

## Status das etapas do PRD (§15)

| Etapa | Descrição | Status |
|---|---|---|
| 0 | Fundação (repo, docs, ambiente, banco, cadastro de fontes, pipeline, CI) | Em andamento: repo, licença, docs, padrão de fluxo e proteção da `main` e esqueleto Django com CI de testes feitos; `dependabot.yml` ativo e conferido (Sessão 12) e Docker Compose de desenvolvimento com job `compose` no CI (Sessão 13); cadastro de fontes e registro de execuções de coleta modelados (Sessão 15, `apps/sources`); falta o restante do banco modelado, o pipeline e o monitoramento |
| 1 | Legislativo e eleições | Não iniciada |
| 2 | Experiência pública | Não iniciada |
| 3 | Finanças públicas | Não iniciada |
| 4 | Inteligência artificial | Não iniciada |
| 5 | Judiciário e fiscalização | Não iniciada |
| 6 | Expansão nacional | Não iniciada |

## Repositório
`masterlxz/polis`, público. Proteção da `main` pelo `padrao/` do workspace (ADR 0005 do workspace), ligada e conferida na Sessão 2: ruleset `protect-main` (PR + `guard` + `dco` obrigatórios, e `tests` desde a Sessão 10, sem force push nem exclusão; bypass só do Admin e só via PR), secret scanning, push protection, alertas e security updates do Dependabot, `delete_branch_on_merge`. Push direto na `main` testado e recusado. Version updates pelo `.github/dependabot.yml` (Sessão 11, P-19): semanal, um PR agrupado por ecossistema (`uv` e `github-actions`), sem auto-merge, Django só em patches.
