# 0003: Repositório público, na conta pessoal

**Data:** 2026-10-31

## Contexto
Os outros cinco projetos do autor vivem na organização `Arven-Labs`. O PRD ainda é um documento inicial, com muitas decisões em aberto (§18), e o produto trata de transparência.

## Decisão
O repositório é **`masterlxz/polis`**, **público desde o primeiro commit**. Segue o padrão de fluxo do workspace: PR obrigatório, job `guard` obrigatório, sem force push, secret scanning e push protection ligados.

## Alternativas
- **`Arven-Labs/polis` privado:** protegeria o PRD e as decisões em aberto até o modelo de dados e a análise jurídica das fontes estarem firmes. Abrir depois é fácil; fechar não é.
- **`Arven-Labs/polis` público:** coerente com os outros projetos e com o produto, mas o dono preferiu a conta pessoal.

## Consequências
- O PRD e a lista de decisões em aberto ficam públicos e indexáveis. Nada de dado pessoal, segredo ou credencial entra no repo (o `guard` barra o que for rastreado).
- Foge do padrão de organização dos outros cinco projetos.
- Mudar para uma organização depois é uma transferência de repositório (o GitHub mantém o redirecionamento); reversível.
- Rulesets e secret scanning funcionam em repositório público de conta pessoal sem plano pago.
