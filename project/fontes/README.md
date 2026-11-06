# polis: Cadastro de fontes

Um arquivo por fonte, no formato do PRD §8.1. Serve de insumo para P-02 (stack) e P-15 (regras por fonte). **Não é aprovação de integração**: a avaliação de termos e de legislação (PRD §8.2) continua a cargo do dono e, se for jurídica, do P-16.

## Como cada fato é rotulado

| Rótulo | Significa |
|---|---|
| **medido (data)** | Observei na data indicada, com a URL ou o comando para reproduzir. Vale para aquele momento e aquela amostra. |
| **documentação (URL)** | A própria fonte afirma. Não confirmei por medição. |
| **inferência** | Conclusão minha a partir do que foi medido; pode estar errada. |
| **não verificado** | Não medi nem encontrei na documentação. |

Medições usam poucas requisições, em série, sem autenticação, com `User-Agent` genérico. Respostas brutas não são versionadas; o registro traz só estrutura, contagens e exemplos mínimos.

## Fontes

| Fonte | Arquivo | Última medição | Estado |
|---|---|---|---|
| Câmara dos Deputados (Dados Abertos) | [camara.md](camara.md) | 2026-11-05 | Medida; sem integração |
| Senado Federal (Dados Abertos Legislativos) | [senado.md](senado.md) | 2026-11-05 | Medida; sem integração |
| TSE (Portal de Dados Abertos) | [tse.md](tse.md) | 2026-11-05 | Medida (ciclos 2026 e 2024); sem integração |

## Regimes de uso lado a lado (leitura de 2026-11-06)

Cada fonte tem a seção "Regras operacionais" no próprio arquivo. São decisões de engenharia; o que pode ser armazenado e redistribuído depende do P-16.

| | Câmara | Senado | TSE |
|---|---|---|---|
| Licença nomeada | não encontrada | não encontrada | CC BY nos metadados (181 de 190 conjuntos do portal) |
| Atribuição | não exigida (FAQ pede retribuição) | "citar a fonte" (política do portal; não se liga expressamente à API) | exigida pela CC BY |
| Uso comercial | permitido pelo FAQ | não dito | CC BY não o restringe; dado pessoal fica no P-16 |
| Limite de taxa | não documentado (`retry-after: 30`) | 10 req/s documentado | não documentado |
| Texto lido na íntegra | FAQ; **Ato da Mesa 45/2012 e termos do portal não** (HTTP 429) | política do portal e Plano 2026/2028 | `/about`; **Portarias 93/2021 e 525/2021 não** (HTTP 403) |
