# 0009: Prioridade dos módulos e fatiamento da Etapa 1 (P-13)

**Data:** 2026-11-08

## Contexto
O PRD §15 propõe seis etapas depois da fundação e diz que a ordem "poderá ser alterada conforme a avaliação técnica". O P-13 pede a priorização final. O que existe hoje: três fontes medidas e com regras (TSE, Câmara, Senado; ADR 0008), o conector de carga pronto (`apps/sources`) e o conjunto `consulta-cand-2026` do TSE carregado só em banco de desenvolvimento. Não há ainda modelo de pessoa, de candidatura ou de votação, nem página pública.

## Decisão
1. **A ordem das etapas do PRD §15 fica como está:** 1 legislativo e eleições, 2 experiência pública, 3 finanças públicas, 4 inteligência artificial, 5 judiciário e fiscalização, 6 expansão nacional.
2. **A Etapa 1 é fatiada na vertical, começando pelo TSE:** normalização do TSE → pessoa e candidatura → página pública de candidato → busca simples por nome. Só depois entram Câmara e Senado, reaproveitando o modelo já validado com uma fonte.
3. **Esta decisão não abre exceção ao fluxo:** cada fatia continua sendo um PR por intenção, com testes primeiro (AGENTS §3, Etapa D).

## Alternativas
- **Finanças antes da experiência pública:** dinheiro público tem alto valor cívico, mas exige medir fontes novas (Portal da Transparência, PNCP, sem medição hoje) e adia o produto visível. Descartada por ora; reavaliar ao fim da Etapa 1.
- **Cobertura territorial (Etapa 6) antes de IA e judiciário:** descartada; amplia a superfície de fontes antes de existir um produto estável, e o judiciário depende do P-16.
- **Fatia horizontal na Etapa 1 (ingerir as três fontes, depois modelo, depois interface):** evita retrabalho de modelo, mas o modelo unificado seria desenhado sem uso real e o produto só apareceria no fim.

## Consequências
- O modelo unificado (PRD §9.3) nasce do TSE e será generalizado quando Câmara e Senado entrarem; aceitamos algum retrabalho de modelo em troca de validar com dados e interface reais.
- A "Busca inicial" do PRD §15 (Etapa 1) passa a significar busca simples por nome sobre o que já existe; a estratégia definitiva é o P-06.
- Ao fim da Etapa 1, a ordem das Etapas 2 em diante é reavaliada, com o que tiver sido medido.
- Etapas 4 e 5 continuam dependendo de decisões em aberto (P-08, P-16), que não são pré-requisito da Etapa 1.
