# polis

Plataforma aberta de transparência e inteligência cívica: reúne, organiza e apresenta informações públicas sobre o Brasil (representantes, instituições, votações, gastos, decisões e políticas públicas), sempre com rastreabilidade até a fonte original.

**Status:** pré-código. Há o [PRD](project/PRD.md), as decisões iniciais, a medição das fontes e a stack escolhida (Python, Django e PostgreSQL, [ADR 0006](project/adr/0006-stack-do-nucleo.md)). O projeto ainda não foi criado.

## Princípios

Neutralidade, rastreabilidade, separação entre dado e análise, privacidade e verificabilidade. A IA é camada de pesquisa, nunca fonte primária. Detalhes no [PRD](project/PRD.md), seção 4 e 10.

## Documentação

- [`project/INDEX.md`](project/INDEX.md): ponto de entrada e histórico de decisões.
- [`project/PRD.md`](project/PRD.md): requisitos do produto.
- [`project/adr/`](project/adr/): registros de decisão de arquitetura.

## Licença

- **Código:** [GNU AGPL-3.0](LICENSE). Quem rodar uma versão modificada como serviço de rede precisa disponibilizar o código-fonte aos usuários desse serviço.
- **Dados:** a licença acima **não** cobre os dados das fontes públicas. Cada fonte tem termos próprios de uso e redistribuição, avaliados caso a caso antes de qualquer integração (PRD, seção 8.2).

Copyright (C) 2026 Fabio Anjos Junior.

## Contribuições

Ainda não aceitamos contribuições de código. Antes disso é preciso decidir a política de contribuição (CLA ou DCO). Issues com sugestões e correções de documentação são bem-vindas.
