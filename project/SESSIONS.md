# polis: Log de sessões

Mais recente no topo.

### 2026-11-05 — Sessão 2, parte 3 (aplicação do DCO)

- **Decisão do dono**: workflow separado `dco` (não dentro do `guard`), vale para todos os PRs, inclusive os do mantenedor.
- **Feito**: `.github/scripts/check-dco.sh` (sign-off do autor ou do committer, merges ignorados, `dependabot[bot]` isento), `.github/scripts/test-check-dco.sh` (14 casos), `.github/workflows/dco.yml` (roda os testes e depois a checagem), `CONTRIBUTING.md`.
- **Testes**: contra um stub que sempre passa, 6 passaram e 5 falharam. Com a implementação, 14 passam. Mutações no script (maiúsculas, aceitar qualquer e-mail, incluir merges, tirar a isenção do dependabot, só autor, só committer): todas pegas por algum teste; as duas últimas só depois de eu acrescentar testes, que não distinguiam autor de committer. Um mutante equivalente (exigir `@` no regex) não é pego, porque o e-mail já tem de bater com o do autor ou do committer.
- **Não verificado**: se os PRs do Dependabot trazem `Signed-off-by` (palpite: não; a isenção cobre); comportamento em squash e rebase merge; o check ainda não é exigido no ruleset.
- **Fica**: depois do merge e do `dco` verde na `main`, incluir `dco` nos checks exigidos do `protect-main` (mexe na proteção da `main`: pedir confirmação); medir as fontes (P-02, P-15).

### 2026-11-05 — Sessão 2, parte 2 (P-01: DCO)

- **Decisão do dono**: DCO (ADR 0004), depois de comparar com CLA. Premissa registrada: sem plano de dual license hoje (P-11 em aberto).
- **Feito**: ADR 0004; P-01 movido para Resolvidas; PR #2 mesclado antes (`guard` verde na `main`, run 42114858200).
- **Não verificado**: validação jurídica (P-16).
- **Fica**: PR de aplicação (`CONTRIBUTING.md` e checagem de `Signed-off-by` no `guard`, com teste primeiro); medir as fontes (P-02, P-15).

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
