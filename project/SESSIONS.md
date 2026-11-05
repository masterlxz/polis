# polis: Log de sessões

Mais recente no topo.

### 2026-11-05 — Sessão 2 (fechamento da proteção da `main`)

- **Pedido**: fechar a governança da Etapa 0 deixada em aberto na Sessão 1.
- **Conferido** (leitura via `gh api`): `guard` verde na `main` (run do merge do PR #1, 7s); ruleset `protect-main` ativo (sem exclusão, sem force push, PR com 0 aprovações, `guard` obrigatório, `strict: false`, bypass do papel Admin só via PR); secret scanning e push protection ligados; `delete_branch_on_merge` ligado; 0 alertas do Dependabot.
- **Alterado** (confirmado pelo dono): `dependabot_security_updates` ligado (estava desativado).
- **Testado**: push direto na `main` (commit vazio) recusado com "Changes must be made through a pull request" e "Required status check guard is expected"; commit local descartado, nada chegou ao remoto.
- **Não verificado**: push protection com segredo real; o bypass do Admin não foi exercitado (só se sabe que existe via PR).
- **Fica**: P-01 (CLA ou DCO); medir as fontes (TSE, Câmara, Senado) para P-02 e P-15.

### 2026-10-31 — Sessão 1 (criação do repositório e decisões iniciais)

- **Pedido**: estruturar o projeto novo a partir do PRD: repositório, GitHub, licença e o padrão do workspace.
- **Decisão do dono**: nome polis (entre 5 candidatos, ADR 0001); `masterlxz/polis` público (ADR 0003); AGPL-3.0 (ADR 0002); só governança e docs, sem código nem stack.
- **Feito** (commit inicial direto na `main`, depois branch `docs/estrutura-inicial`, PR #1): repo criado; `LICENSE` oficial, `README`, `.gitignore`; PRD em `project/PRD.md`; `INDEX`, `OVERVIEW`, `PENDING`, `SESSIONS`; ADRs 0001 a 0003; template de PR e job `guard` copiados de `padrao/` do workspace.
- **CI**: `guard` passou no PR #1 (visto com `gh pr checks 1`, 4s). Na `main` ainda não rodou; conferir depois do merge, antes de ligar o ruleset.
- **Não verificado**: ruleset e segurança ainda não aplicados (dependem do merge e do `guard` verde na `main`); push direto na `main` bloqueado e push protection com segredo real não testados.
- **Fica**: mesclar o PR #1; ligar ruleset, secret scanning, push protection, alertas do Dependabot e `delete_branch_on_merge`; decidir P-01 (CLA/DCO) antes de qualquer contribuição de código; medir as fontes (TSE, Câmara, Senado) para escolher a stack.
