# 0015: Design, navegação e front-end com Next.js (P-18)

**Data:** 2026-11-08

## Contexto
O P-18 pede design e navegação definitivos. O PRD §7 lista 11 seções de navegação, mas a Etapa 1 (ADR 0009) só terá dados de Pessoas, Eleições e Legislativo, mais a busca (ADR 0012). Ao decidir o front-end, o dono preferiu **Next.js separado desde a Etapa 1**, contra a recomendação deste assistente (Django templates na Etapa 1, com gatilho de reavaliação na Etapa 2). Essa escolha **substitui parcialmente a decisão 1 do ADR 0006** ("páginas públicas renderizadas no servidor, JavaScript mínimo, sem SPA na Etapa 1"); o restante do ADR 0006 (Django, PostgreSQL, monólito de dados e ingestão) continua valendo. A decisão é do dono e está registrada com as consequências abaixo.

## Decisão
1. **Front-end público em Next.js**, como aplicação separada do Django, com **renderização no servidor** das páginas públicas (indexáveis por buscadores, PRD §12). O Django continua dono dos dados, da ingestão, da administração e das regras (ADR 0006).
2. **Interface entre os dois:** uma API **interna**, acessível só pela rede privada do Compose, não pública e não documentada como contrato. Ela segue as regras do ADR 0013 desde o primeiro dia: **mesmo filtro de dados** (nunca campo interno nem nome civil, ADR 0005) e **atribuição** (fonte, data de coleta, link do original, licença; ADR 0008). A busca (ADR 0012) fica no Django, atrás do módulo `buscar(consulta, filtros)`. Isso **não** abre a API pública do ADR 0013.
3. **Condição de validação antes de implementar:** um spike curto, como o da ingestão (ADR 0006), mede no ambiente de teste do ADR 0011 (1 VPS, teto de cerca de US$ 20/mês): memória somada de Django, PostgreSQL e Next.js; p95 de página e de busca (metas do ADR 0010); tempo de build e de deploy. Se não couber, o ADR é revisto, **nunca em silêncio**, e a alternativa é Django templates (ADR 0006). O dono pode retirar esta condição ao revisar o ADR.
4. **Navegação da Etapa 1: só o que tem conteúdo.** Início, Pessoas, Eleições, Legislativo (quando Câmara e Senado entrarem), Busca e uma página "Fontes e metodologia". As demais seções do PRD §7 entram quando tiverem dado; nenhuma aparece vazia ou como "em breve".
5. **Origem e data em todo dado:** um componente padrão mostra, junto de cada informação, a fonte, a data de coleta e o link do original (PRD §7.3, ADR 0008 decisão 3).
6. **Acessibilidade: WCAG 2.2 nível AA como meta**, verificada por checagem automatizada **e** manual (teclado, leitor de tela, zoom), não só automatizada.
7. **Linha visual** conforme o ADR 0014 (neutra, sem cores ou símbolos partidários ou da bandeira).
8. **Versões e bibliotecas** (Next.js, React, Node, CSS) **não são fixadas aqui**: conferem-se na página oficial na hora do spike, como no ADR 0006, e cada dependência nova pede aprovação (AGENTS §3, Etapa E).

## Alternativas
- **Django templates na Etapa 1, com gatilho na Etapa 2 (recomendação do assistente):** um serviço a menos, sem API interna obrigatória, menos dependências e menor barreira para contribuidores. Descartada pelo dono por preferir um framework de front.
- **Django templates + htmx:** interatividade pontual sem segundo serviço; não escolhida.
- **Menu completo do PRD §7 com seções "em breve":** descartada; promete cobertura que não existe e contraria a precisão do PRD §4.

## Consequências
- **Mais peças no VPS único (ADR 0011):** um processo Node a mais, mais RAM, dois deploys e uma rede interna entre os serviços. O teto de cerca de US$ 20 fica mais apertado; o spike da decisão 3 mede.
- **Mais superfície de segurança:** cadeia de dependências npm para vigiar (Dependabot já cobre `uv` e `github-actions`; precisaria incluir `npm`) e a API interna precisa ficar inacessível de fora (verificar na implantação).
- **Duas stacks para quem contribui** no projeto aberto (ADR 0006): Python e TypeScript.
- **Melhor base para a interatividade da Etapa 2** (filtros, comparações, alertas), que é o ganho esperado.
- O `OVERVIEW.md` e o job de CI mudam quando o spike confirmar a decisão; até lá, nada é implementado.
- **Não verificado:** nenhuma medição de memória, latência ou build; nenhuma versão conferida; a proteção da API interna. *(Atualizado pelo spike, abaixo.)*

## Resultado do spike (2026-11-08)

Código, dados sintéticos, script de carga e resultados brutos estão na branch `spike/nextjs` (`spikes/nextjs/`), que **nunca vai para a `main`** (ADR 0006, decisão 3). Dados 100% sintéticos (300 mil nomes inventados, sem CPF). Versões do teste, todas com mais de 14 dias na data: Next.js 16.4.3 (2026-10-23), React 19.3.1 (2026-10-14), Node 24.22.2, Django 6.1.3, psycopg 3.3.8, gunicorn 26.2.0, `postgres:18`.

**Como mediu:** Docker Compose na máquina de desenvolvimento (8 núcleos, 15 GB), `cpuset` emulando 2 vCPU com todos os contêineres dividindo os mesmos 2 núcleos; gerador de carga em outros núcleos; taxa fixa, 10 s de aquecimento e 60 s medidos, `trailingSlash` ligado no Next.js para as URLs serem iguais às do Django. Dois cenários, porque a primeira tentativa (80% perfil, 20% busca, 50 req/s) saturou a máquina **na pilha base**, antes de o Next.js entrar.

**1. Página de perfil, 50 req/s, 5 repetições, 2 vCPU (load do host entre 0,7 e 3,8):**

| Pilha | p50 | p95 (mediana; máx.) | p99 | RAM total sob carga (mediana) | Erros |
|---|---|---|---|---|---|
| Base: Django templates | 3,1 ms | 3,9 ms; 4,4 ms | 5 a 44 ms | 188 MiB | 0 |
| Alvo: Django JSON + Next.js | 9,1 ms | 13,4 ms; 15,9 ms | 38 a 56 ms | 527 MiB | 0 |

O Next.js multiplica a latência de página por cerca de 3 (de poucos ms para poucas dezenas de ms) e acrescenta cerca de **340 MiB** (o contêiner do Next.js chegou a 351 MiB), muito abaixo do teto de ~1 GB e longe da meta de 800 ms. Imagens: Next.js 384 MB, Django 288 MB.

**2. Busca por nome (pg_trgm, ADR 0012), só buscas, 2 vCPU, 3 repetições:**

| Taxa | Pilha | p50 | p95 | Erros |
|---|---|---|---|---|
| 3 buscas/s | Base | 0,7 a 8,6 s | 2,4 a 13,8 s | 45 (timeouts) |
| 3 buscas/s | Alvo | 0,6 a 1,7 s | 1,7 a 5,9 s | 1 |
| 6 buscas/s | Base | 14,9 a 16,6 s | 25,7 a 29,5 s | 20 |
| 6 buscas/s | Alvo | 14,6 a 17,7 s | 23,2 a 29,9 s | 19 |

A meta do ADR 0010 (50 req/s com 20% de busca = 10 buscas/s, p95 ≤ 1,5 s) **não foi atingida**, e a causa **não é o Next.js**: base e alvo ficam parecidos, o tempo está no PostgreSQL. Uma consulta de nome comum ("Maria da Silva") custou cerca de 1,6 s com o limiar padrão do `pg_trgm` (0,3) em um só núcleo, 0,94 s com 0,5 e 0,2 s com 0,7 (que, porém, devolveu 0 resultados para "Maira da Silva", um erro de digitação). Sem o índice de trigramas, uma consulta rara passou de cerca de 0,2 s para 3,2 s, o que prova que o teste enxerga o índice. O load alto dessas rodadas é a fila nos 2 núcleos causada pela própria busca, não ruído externo.

**Conclusão sobre esta decisão:**
- O que cabe ao **Next.js** (decisão 3) **passou**: memória extra de ~340 MiB, página muito abaixo de 800 ms, sem erros. Pelo que foi medido, a condição do spike está atendida **para o Next.js**, e a decisão 1 (Next.js separado) pode seguir.
- O critério global do spike (busca p95 ≤ 1,5 s a 50 req/s) **não passou**, por causa da busca. Isso aciona o gatilho (a) do ADR 0012 e precisa de uma revisão da busca, que é outro assunto (ver P-06 no `PENDING.md`).

**O que o spike não prova:**
- Dados sintéticos e **enviesados** (nomes comuns repetem muito, de propósito); a consulta mais cara é a de nome comum, e a distribuição real pode ser melhor ou pior. A primeira versão do gerador estava defeituosa (só 180 nomes distintos) e foi descartada.
- Uma máquina de desenvolvimento, não um VPS: `cpuset` emula CPU, mas não a E/S de disco nem o vizinho ruidoso; os 2 vCPU/4 GB e 1 vCPU/2 GB são hipóteses minhas (nenhum plano foi verificado). O perfil de 1 vCPU/2 GB foi medido só na rodada ruidosa (host com load de 14 a 17), por isso **não é reportado**; os números ficam nos arquivos brutos da branch.
- Não mediu o tráfego misto (perfil e busca juntos) com o Next.js em condições limpas; não mediu tempo de build isolado nem a proteção da API interna; sem tráfego real.
- Uma mitigação da busca (token, prefixo, pré-filtro por UF, cache, busca dedicada) é **hipótese não testada**.

## Primeira rota da API interna (Sessão 43, 2026-11-09)

Implementada a primeira rota da decisão 2: `GET /internal/v1/pessoas/<ciclo>-<sq>/` (`apps/elections/views.py`), perfil de uma pessoa com suas candidaturas, a pedido do dono (só a API agora; o Next.js fica para um PR seguinte). Pontos que o ADR não fixava:

- **Identificador:** ciclo (4 dígitos) mais `SQ_CANDIDATO` (1 a 12 dígitos), a chave natural do TSE, que sobrevive a uma recarga do banco; o pk interno não é usado. Qualquer outro formato cai no 404 padrão.
- **Saída por lista explícita de campos**, montada campo a campo (sem DRF nem biblioteca nova, ADR 0013 decisão 5): o nome social, o pk e o `IngestionRun` nunca saem, e um campo novo no modelo não vaza sem decisão. Campos sem valor (federação, coligação, situação, resultado) saem `null`.
- **Atribuição em cada candidatura** (decisão 2 e ADR 0008, decisão 3): fonte, conjunto, `coletado_em` (início da execução), `gerado_pela_fonte_em` (da linha), link do original e licença do conjunto.
- **Só leitura:** outros métodos dão 405; pessoa inexistente dá 404 sem repetir o valor pedido.
- **Sem autenticação.** "Interna" é propriedade de rede (Compose), não do código: o Django não distingue o Next.js da internet. Em desenvolvimento a porta 8000 só escuta em `127.0.0.1`. **A proteção na implantação continua não verificada** (consequência já listada acima); se a rede sozinha não bastar, um token compartilhado é decisão de segurança própria.
- **Não verificado:** o JSON contra os 21.017 registros reais (conferência por `curl` no Compose, do dono); desempenho em volume (a consulta é por chave única, 2 consultas por pedido); a ordem das candidaturas só foi testada com turnos 1 e 2. *(Atualização da Sessão 44: o dono conferiu o JSON de uma pessoa com 2 candidaturas no banco real; o restante segue não verificado.)*

## Infraestrutura do front (Sessão 44, 2026-11-09)

Primeira metade da implementação da decisão 1, a pedido do dono (2 PRs: infra agora, página de candidato depois). Existe o serviço `front` em `web/`, sem nenhuma página de dado, só a rota `/saude/`. Pontos que o ADR não fixava:

- **Versões (decisão 8), conferidas em 2026-11-09 com `npm view` e GitHub Advisories:** Next.js **16.4.3** (2026-10-23, 17 dias; a 16.4.5, a mais nova, tinha 6 dias e a 16.4.4 tinha 7, abaixo do critério de 14 dias do spike), React e React DOM **19.3.1**, imagem `node:24-slim`, `actions/setup-node@v7`. Nenhum aviso aberto para `next@16.4.3` nem `react@19.3.1`. Fixadas exatas em `web/package.json` e no `package-lock.json` (54 pacotes, todos do `registry.npmjs.org`, com integridade e sem script de instalação).
- **Instalação sem scripts:** `npm ci --ignore-scripts` no CI e na imagem; nenhum pacote roda código na instalação.
- **CI:** job `web` (`.github/workflows/web.yml`): `npm ci`, `npm run build`, testes com `node --test` contra o servidor de produção (`.next/standalone/server.js`) e `docker build` da imagem. **Ainda não é exigido no ruleset `protect-main`** (mudança de ruleset, decisão à parte). Sem ferramenta de teste nova (Vitest e Playwright ficam para quando houver mais páginas).
- **Dependabot `npm` em `/web`:** semanal, um PR agrupado, **major de `next`, `react` e `react-dom` ignorado** (decisão manual, como o Django).
- **Compose:** serviço `front` com a porta só em `127.0.0.1:3000`, `API_URL=http://web:8000` e healthcheck; o `web` passou a aceitar o host `web` em `DJANGO_ALLOWED_HOSTS` (sem isso o Django recusa o pedido do front com 400). O Django continua com a porta 8000 em `127.0.0.1` em desenvolvimento, para o admin.
- **Conferência real (dono, Compose):** `front` saudável, `/saude/` responde `ok` e, de dentro do contêiner `front`, a API interna do Django responde 200.
- **Não verificado:** a proteção real da rede interna na implantação (o Django ainda não tem autenticação, e a porta 8000 segue publicada em `127.0.0.1` em desenvolvimento); imagem base por tag móvel, não por digest; o consumo de memória do `front` no ambiente de teste do ADR 0011 (o spike mediu ~340 MiB com outra aplicação); a primeira página só vem no PR seguinte.
