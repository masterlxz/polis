# polis: Log de sessões

Mais recente no topo.

### 2026-10-31 — Sessão 1 (criação do repositório e decisões iniciais)

- **Pedido**: estruturar o projeto novo a partir do PRD: repositório, GitHub, licença e o padrão do workspace.
- **Decisão do dono**: nome polis (entre 5 candidatos, ADR 0001); `masterlxz/polis` público (ADR 0003); AGPL-3.0 (ADR 0002); só governança e docs, sem código nem stack.
- **Feito** (commit inicial direto na `main`, depois branch `docs/estrutura-inicial`, PR #1): repo criado; `LICENSE` oficial, `README`, `.gitignore`; PRD em `project/PRD.md`; `INDEX`, `OVERVIEW`, `PENDING`, `SESSIONS`; ADRs 0001 a 0003; template de PR e job `guard` copiados de `padrao/` do workspace.
- **CI**: `guard` passou no PR #1 (visto com `gh pr checks 1`, 4s). Na `main` ainda não rodou; conferir depois do merge, antes de ligar o ruleset.
- **Não verificado**: ruleset e segurança ainda não aplicados (dependem do merge e do `guard` verde na `main`); push direto na `main` bloqueado e push protection com segredo real não testados.
- **Fica**: mesclar o PR #1; ligar ruleset, secret scanning, push protection, alertas do Dependabot e `delete_branch_on_merge`; decidir P-01 (CLA/DCO) antes de qualquer contribuição de código; medir as fontes (TSE, Câmara, Senado) para escolher a stack.
