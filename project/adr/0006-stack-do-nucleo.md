# 0006: Stack do núcleo: Python, Django e PostgreSQL (P-02, P-03, P-05)

**Data:** 2026-11-05

## Contexto
As três fontes do primeiro corte foram medidas (`project/fontes/`) e o ADR 0005 fixou como o polis trata dado pessoal (allowlist por nome de coluna, descarte na leitura, falha fechada). Falta escolher a stack para começar a Etapa 0 técnica. O que as medições exigem dela: ler ZIPs de até 1,36 GB em fluxo (ISO-8859-1, `;`, CRLF), descartar colunas na leitura, throttling abaixo de 10 req/s (Senado), timeout e retentativa para o 504 repetível (Câmara), reprocessar sem duplicar, páginas públicas indexáveis, API documentada e área administrativa (PRD §13).

O dono comparou Django e Rails, considerou o empate técnico (gosta das duas) e escolheu **Django**, sem comparar com medição.

## Decisão
1. **Python + Django**, monólito modular: páginas públicas renderizadas no servidor (templates, JavaScript mínimo, sem SPA na Etapa 1), API, área administrativa e ingestão como comandos do mesmo projeto.
2. **Versões** (conferidas em 2026-11-05 nas páginas oficiais; reconferir antes de qualquer atualização, as datas mudam):
   - **Django 6.1** (6.1.3 hoje) para começar, e migrar para o **6.2 LTS** quando sair (abril de 2027). O 6.1 tem correções até abril de 2027 e segurança estendida até dezembro de 2027; o 6.2 LTS, correções até dezembro de 2027 e segurança estendida até abril de 2030.
   - **Python 3.14** (correções até 2030-10). O Django 6.1 e o 6.2 suportam 3.12 a 3.15; o 3.15 saiu em 2026-10 e não é ponto de partida.
   - **PostgreSQL 18** (18.6; suporte até 2030-11-14). `psycopg` 3.3.x; o suporte dele ao PostgreSQL 18 **não foi verificado** (o spike rodou com `postgres:18` e `psycopg[binary]` no Python 3.14 sem erro).
   - Ferramentas: `uv` (0.13.x, **antes da 1.0**, ainda pode mudar), `ruff`, `pytest` e um verificador de tipos (AGENTS §9). Versões fixadas quando o projeto for criado.
3. **Estrutura do repositório (P-03):** monorepo, o próprio `polis`. Um projeto Django com apps por domínio e por conector; docs em `project/`. Spikes ficam em branch e nunca vão para a `main`.
4. **Banco (P-05):** PostgreSQL, único banco da Etapa 1. Busca textual (`unaccent`, `pg_trgm`) fica para o P-06.
5. **Ingestão:** comandos do próprio projeto, leitura em fluxo, aplicando o ADR 0005 (allowlist por nome, falha fechada por ZIP dentro de uma transação, rejeição de linha malformada, SHA-256 do original). Agendamento e fila **não são decididos aqui.**
6. **Desenvolvimento:** Docker Compose para ambiente reproduzível (o projeto é aberto e self-hostable); testes validados pelo CI do GitHub (convenção do workspace).

### Resultado do spike de ingestão (PR #12, não mesclado)
Dados 100% sintéticos (o CPF é um valor-canário; nenhum dado real), 3 execuções independentes no CI (Python 3.14, PostgreSQL 18 como serviço), mesmo ZIP: 0,89 GB comprimido, 12,11 GB descomprimido, 20,57 milhões de linhas, 50 colunas, 28 itens CSV mais um `leiame.pdf` falso.

| Etapa | Execução 1 | Execução 2 | Execução 3 |
|---|---|---|---|
| a: só descomprimir | 16,9 s | 17,0 s | 16,7 s |
| b: ler + allowlist (8 de 50 colunas) | 181,0 s (67 MB/s) | 184,3 s (66 MB/s) | 164,5 s (74 MB/s) |
| c: SHA-256 do ZIP | 0,6 s | 0,6 s | 0,8 s |
| d: `COPY` de 2 milhões de linhas | 21,2 s | 21,2 s | 18,7 s |
| Pico de memória (todas as etapas) | ≤ 49 MB | ≤ 49 MB | ≤ 49 MB |

Critério do plano (b + c em menos de 20 min; memória abaixo de 500 MB): **atendido nas 3**, com b + c entre 165 s e 185 s, ou seja, cerca de 6 vezes de folga. Os 11 testes passaram no CI; ao quebrar o código de propósito (vazar todas as colunas, tirar a falha fechada, tirar a rejeição de linha), falharam exatamente os 4 testes esperados, e voltaram a passar ao reverter.

**O que o spike não prova:**
- O pico de memória de 49 MB é um **limite superior**: o valor é idêntico em todas as etapas, e a explicação provável (inferência, confiança média) é que o processo filho herda o pico do pai no Linux. Nenhuma etapa passou de 49 MB, mas esse não é o pico real de cada uma.
- Os dados sintéticos comprimem mais (razão 13,6x) do que a única amostra real medida (cerca de 8,7x), e o tamanho descomprimido de 12 GB para um ZIP real de 1,36 GB é **extrapolação** dessa amostra.
- O gargalo é o `csv` em Python (cerca de 10 vezes mais lento que descomprimir); a margem de 6 vezes cobre o caso medido, não um volume maior (P-14 em aberto).
- O `COPY` foi numa tabela vazia, sem índices nem restrições, e a extrapolação para todas as linhas (cerca de 3 a 4 minutos) é só uma estimativa.
- Não mediu download pela rede, concorrência com leitura pública, nem a CPU exata do runner (não registrada).
- A codificação foi ISO-8859-1; se a fonte usar Windows-1252, isso precisa ser conferido antes de produção.

## Alternativas
- **Ruby on Rails:** viável. O Rails 8 não é ultrapassado e traz peças bem encaixadas (Solid Queue sem Redis, Kamal, Hotwire). Perde, para este projeto, em quatro pontos: não tem suporte de longo prazo (correções por 1 ano, segurança por 2), a área administrativa não vem pronta, a documentação OpenAPI da API é por gem, e o ecossistema de dados e de IA (Etapa 4) é menor. A hipótese de que o `csv` do Ruby seria mais lento **não foi medida e não foi motivo da decisão**; o spike rodou só em Python, por escolha do dono. A preferência pessoal pesou como desempate e é legítima.
- **TypeScript + Next.js:** mais peças móveis; a área administrativa e as migrações seriam feitas à mão.
- **Rust (axum + sqlx):** melhor desempenho e tipagem, mas muito mais código para CRUD, administração e páginas, e barreira maior para contribuidores de um projeto cívico aberto. O leitor do spike é a fronteira por onde um módulo em Rust poderia entrar depois, se a margem sumir.
- **Django 5.2 LTS agora:** as correções comuns dele terminaram em 2025-12-03 (só segurança até abril de 2028), então começar nele traria menos vida útil que 6.1 mais 6.2 LTS.
- **SQLite:** não serve para a escrita concorrente da ingestão com leitura pública.

## Consequências
- Atualizações do Django a cada cerca de oito meses até o 6.2 LTS (abril de 2027); depois, três anos de suporte. A migração 6.1 para 6.2 é pequena porque o 6.2 é a última versão do esquema antigo de versionamento.
- Python é mais lento que Rust no parse. A margem medida é de cerca de 6 vezes no caso estimado mais pesado; se o volume crescer, só o parse precisa mudar, atrás do contrato do leitor.
- Seguem em aberto, cada um com ADR próprio: hospedagem (P-04), busca (P-06), documentos (P-07), IA (P-08), autenticação (P-09), API pública (P-10), financiamento (P-11), metas de desempenho (P-14) e a fila e o agendamento da ingestão. Não confirmei que o `django.tasks` tenha backend de produção embutido.
- Habilita a Etapa 0 técnica: criar o projeto Django, o `docker-compose`, o CI de testes e o `dependabot.yml` (P-19), e exigir o novo check no ruleset.
- O spike (`spikes/ingestao/`) fica só na branch e no PR #12 fechado. O leitor e os 11 testes são a base dos testes de contrato dos conectores (ADR 0005, decisão 6).
