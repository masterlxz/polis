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
- **Não verificado:** nenhuma medição de memória, latência ou build; nenhuma versão conferida; a proteção da API interna.
