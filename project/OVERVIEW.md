# polis: Visão geral

## O que é
Plataforma aberta de transparência e inteligência cívica: unifica informações públicas sobre o Brasil (pessoas, instituições, eleições, legislativo, executivo, judiciário, finanças públicas, fiscalização, políticas públicas) com rastreabilidade até a fonte. A IA é camada de pesquisa, nunca fonte primária. Detalhes no `PRD.md`.

## Stack
Decidida no ADR 0006 (2026-11-05): **Python 3.14 + Django 6.1** (migrar para o 6.2 LTS em abril de 2027), **PostgreSQL 18**, monorepo, ingestão como comandos do projeto. Desde a Sessão 30 (2026-11-08): VPS único no Brasil com Docker Compose, teto de cerca de US$ 20/mês (ADR 0011); busca só em PostgreSQL (ADR 0012); sem API pública na Etapa 1 (ADR 0013); front-end em Next.js separado (ADR 0015, que substitui parcialmente o 0006; spike de 2026-11-08: o Next.js acrescentou ~340 MiB e a página ficou em p95 de ~13 ms em 2 vCPU emulados, sem implantar nada); a busca por `pg_trgm` do ADR 0012 falhou a meta no spike e foi substituída pela busca por tokens no PostgreSQL, com `pg_trgm` só como reserva (ADR 0016, medida em dados sintéticos). Metas da Etapa 1 no ADR 0010; ordem das etapas no ADR 0009. Documentos: link e hash por padrão, sem cópia de arquivos de terceiros, backend adiado (ADR 0017). IA: só na Etapa 4, com citação verificada por código e provedor externo só para dado público, provedor e modelo adiados (ADR 0018). Autenticação: público anônimo; admin com senha e TOTP obrigatório; conta pública adiada (ADR 0019). Ainda em aberto, cada um com ADR próprio: financiamento, fila e agendamento. O esqueleto do projeto Django existe desde a Sessão 9 (`config/`, `tests/`, job `tests` no CI). Desde a Sessão 15 há o app `apps/sources` (`Source`, `Dataset` com a allowlist do ADR 0005 e `IngestionRun` imutável); desde a Sessão 17 há também o leitor de ZIP de CSV com allowlist (`apps/sources/zip_csv.py`, sem banco); desde a Sessão 23 o `Dataset` tem o portão de licença (ADR 0008, decisão 1) e o `IngestionRun` os códigos `blocked` e `license`; desde a Sessão 24 há o cliente HTTP com etiqueta de rede (`apps/sources/http_client.py`, sem banco); desde a Sessão 25 há a carga de um `Dataset` (`apps/sources/ingestion.py`, `RawRecord` como camada bruta filtrada e o comando `ingest_dataset`); desde a Sessão 26 há o cadastro inicial (`seed_sources`: TSE, Câmara e Senado, e o conjunto `consulta-cand-2026` do TSE, desabilitado); a primeira coleta real (TSE, `consulta-cand-2026`, 42.034 linhas) foi feita pelo dono em 2026-11-07 (Sessão 28), só em banco de desenvolvimento; desde a Sessão 29 cada carga compara a licença declarada no CKAN com a registrada (`license_check_url`, `apps/sources/ckan.py`); ainda não há agendamento, normalização nem modelos de pessoa ou votação. Nomes de modelos e campos em inglês no código, em português na interface.

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
