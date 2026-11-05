# polis: Visão geral

## O que é
Plataforma aberta de transparência e inteligência cívica: unifica informações públicas sobre o Brasil (pessoas, instituições, eleições, legislativo, executivo, judiciário, finanças públicas, fiscalização, políticas públicas) com rastreabilidade até a fonte. A IA é camada de pesquisa, nunca fonte primária. Detalhes no `PRD.md`.

## Stack
**A decidir.** A escolha depende de medir antes as fontes (TSE, Câmara, Senado): formato, volume, limites e termos de uso (PRD §8 e §19).

## Licença
Código: AGPL-3.0 (ADR 0002). Dados: conforme os termos de cada fonte.

## Status das etapas do PRD (§15)

| Etapa | Descrição | Status |
|---|---|---|
| 0 | Fundação (repo, docs, ambiente, banco, cadastro de fontes, pipeline, CI) | Em andamento: repo, licença, docs, padrão de fluxo e proteção da `main` feitos; o restante depende da stack |
| 1 | Legislativo e eleições | Não iniciada |
| 2 | Experiência pública | Não iniciada |
| 3 | Finanças públicas | Não iniciada |
| 4 | Inteligência artificial | Não iniciada |
| 5 | Judiciário e fiscalização | Não iniciada |
| 6 | Expansão nacional | Não iniciada |

## Repositório
`masterlxz/polis`, público. Proteção da `main` pelo `padrao/` do workspace (ADR 0005 do workspace), ligada e conferida na Sessão 2: ruleset `protect-main` (PR + `guard` obrigatórios, sem force push nem exclusão; bypass só do Admin e só via PR), secret scanning, push protection, alertas e security updates do Dependabot, `delete_branch_on_merge`. Push direto na `main` testado e recusado. Ainda não há `dependabot.yml` (version updates): P-19.
