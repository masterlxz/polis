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
