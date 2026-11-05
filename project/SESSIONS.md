# polis: Log de sessões

Mais recente no topo.

### 2026-11-05 — Sessão 4 (medição da fonte Senado Federal)

- **Pedido**: repetir a medição para o Senado, no formato da Câmara (sem plan mode, por repetir receita já aprovada).
- **Feito**: `project/fontes/senado.md`, linha no índice `fontes/README.md`, P-02 e P-15 atualizados. Cerca de 20 requisições em série (mais 4 de reprodução no fim), sem autenticação, `User-Agent` genérico; respostas brutas só na pasta temporária da sessão.
- **Achados principais**: limite documentado de 10 req/s (429), com 503 sob demanda; API sem paginação nas listagens principais, com filtro obrigatório em `/processo` e `/votacao`; 42 de 157 endpoints depreciados, e o `Sunset` de `/materia/*` (2026-02-01) já passou com o serviço ainda no ar; código inexistente devolve 200 com dados vazios, não 404; dois estilos de JSON e dois sistemas de ids (processo e matéria legada); política de uso do portal exige citar a fonte, sem licença nomeada, e nada sobre uso comercial.
- **Verificado de novo** ao final: 157 caminhos e 42 depreciados, cabeçalhos de depreciação de `/materia/172391`, 200 para senador inexistente e 81 senadores.
- **Não verificado**: comportamento real do 429 (não testei o limite); se a política do portal vale para a API; dados pessoais dos endpoints de senadores (não olhei o conteúdo); volume de `/processo` sem filtro de ano; Plano de Dados Abertos 2026/2028; interpretação jurídica (P-16). Medição de um único dia.
- **Fica**: TSE; depois das três fontes, decidir se alguma medição pede ADR e, só então, escolher a stack (P-02).

### 2026-11-05 — Sessão 3 (medição da fonte Câmara dos Deputados)

- **Pedido**: medir as fontes para P-02 e P-15, uma por vez, começando pela Câmara (plan mode; plano aprovado).
- **Feito**: `project/fontes/README.md` (índice e rótulos de origem: medido, documentação, inferência, não verificado) e `project/fontes/camara.md` (campos do PRD §8.1). Medi com 22 requisições (mais 3 de reprodução no fim) em série, sem autenticação, `User-Agent` genérico; respostas brutas ficaram só na pasta temporária da sessão, fora do repo.
- **Achados principais**: API REST + arquivos em massa (CSV, JSON, XLSX); sem autenticação; limite documentado de 100 itens por página (`itens=101` deu 504 em 15 s); `retry-after: 30` em toda resposta, sem significado documentado; arquivos regenerados de madrugada, inclusive de anos encerrados; `cpf` existe no CSV de deputados mas vem vazio nas 7.889 linhas; 62 de 100 proposições recentes têm `ano = 0`; FAQ diz que se pode cobrar pelo uso e não declara restrição, mas não achei licença explícita.
- **Verificado de novo** ao final: 3 comandos de reprodução do doc (513 deputados, 42.340.873 bytes no arquivo de proposições 2026, 78 caminhos na especificação).
- **Não verificado**: limite de taxa e bloqueio (não testei de propósito); XML e ODS; despesas, discursos e votos por deputado; consistência API versus arquivos; ids estáveis; uma única data de medição (a regeneração diária dos arquivos é inferência). Licença e Ato da Mesa 45/2012 não lidos; interpretação jurídica é P-16.
- **Fica**: Senado e TSE (uma por vez); decidir depois das três se alguma medição pede ADR.

### 2026-11-05 — Sessão 2, parte 4 (`dco` exigido no ruleset)

- **Alterado** (confirmado pelo dono): `protect-main` passou a exigir `guard` e `dco`. Comparei o ruleset antes e depois via API: só a lista de checks mudou (bypass, condições e demais regras iguais). Os JSONs antes/depois ficaram na pasta temporária da sessão, não no repo.
- **Testado**: PR #5 descartável com commit sem sign-off: `dco` falhou ("Commit dc45e27 sem Signed-off-by…"), `guard` passou, o estado do merge ficou `BLOCKED`. PR fechado sem mesclar e branch apagada.
- **Não verificado**: PR do Dependabot sob a nova regra; squash e rebase merge; o bypass do Admin sobre o `dco` (existe via PR, não exercitado).
- **Fica**: medir as fontes (TSE, Câmara, Senado) para P-02 e P-15.

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
