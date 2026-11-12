# polis: Estado do Projeto

> Última atualização: 2026-11-06 (Sessão 17: leitor de ZIP de CSV)

## Como usar este arquivo

Leia o arquivo relevante para o que você precisa:

| Para saber sobre | Leia |
|---|---|
| O que é o produto, escopo e etapas | `PRD.md` |
| Visão geral, stack e status | `OVERVIEW.md` |
| Decisões em aberto | `PENDING.md` |
| Decisões tomadas e seus motivos | `adr/` |
| LGPD e LAI (pesquisa de apoio ao P-16, sem parecer) | `lgpd-lai.md` |
| Subir, migrar e atualizar a produção (fechada por padrão) | `runbook.md` |
| Log de sessões de trabalho (mais recente no topo) | `SESSIONS.md` |

**Ao começar uma sessão:** use `/projeto polis` na raiz do workspace.
**Ao terminar uma sessão:** adicione a entrada no topo de `SESSIONS.md` e atualize `PENDING.md`.
**Ao tomar uma decisão não óbvia:** registre um ADR em `adr/` (pergunte antes de criar).
**Fluxo:** branch por tarefa, PR por intenção, `guard` verde antes de mesclar. Regras gerais em `AGENTS.md` do workspace.
