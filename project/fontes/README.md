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
| TSE | (a fazer) | | |
