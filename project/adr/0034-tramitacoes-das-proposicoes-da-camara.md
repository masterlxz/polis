# 0034: Tramitações das proposições da Câmara: chave composta, sem `despacho`, só 2026

**Data:** 2026-11-27

## Contexto
O ADR 0033 trouxe as proposições das votações da Câmara e adiou as tramitações (PRD §15, Etapa 1: "Proposições e tramitações"). A Rodada 5 de `project/fontes/camara.md` (Sessão 113, 2026-11-27) mediu `proposicoesTramitacoes-2026.csv` (38,5 MB, 118.724 linhas, 14 colunas, todas com `dataHora` de 2026):

- **`idTramitacao` não é chave**: 400 valores distintos em 118.724 linhas; é a posição dentro da proposição, e 285 valores aparecem em mais de uma proposição.
- **(proposição, `sequencia`) também não é chave**: 51 pares repetidos, dos quais 38 são iguais nas colunas candidatas e **13 são eventos diferentes** com o mesmo número. Há 1 linha com `sequencia` vazia.
- **Chave por (proposição, `sequencia`, `dataHora`, `siglaOrgao`, `descricaoTramitacao`)**: 118.684 chaves; as 40 linhas perdidas são os 38 pares idênticos. Sem a `sequencia` na chave, 1.290 linhas se perderiam (999 chaves com `sequencia` diferente).
- **46.295 proposições distintas**, das quais só 9.869 estão entre as 26.754 ids dos dois arquivos de votações (os 26.745 do ADR 0033 podem ter mudado no dia seguinte; não verificado). **A maioria das proposições do arquivo não existe em `CamaraProposition`.**
- Sem caractere de controle nas colunas candidatas; `siglaOrgao` até 10 caracteres e `descricaoTramitacao` até 57 (112 valores distintos). `despacho` chega a 3.426 caracteres e cita agentes públicos pelo nome (ADR 0005 não avaliado).

## Decisão
1. **Fonte:** `proposicoesTramitacoes-2026`, um conjunto de `camara`, formato `csv` (o leitor do ADR 0031), por decisão do dono (`owner_decision`), **desabilitado ao nascer**, 24 h, depois das 08:00 GMT, ano fixo no cadastro. **Só 2026 nesta fatia** (decisão do dono); anos anteriores viram conjuntos novos, sem mudar o modelo.
2. **Allowlist de 5 colunas:** `uriProposicao` (só para extrair o id; a URI não é gravada), `sequencia`, `dataHora`, `siglaOrgao` e `descricaoTramitacao`. **`despacho` não é ingerido** (decisão do dono, ADR 0005); volta só com ADR próprio. Descartadas na leitura: `idTramitacao` (não é chave e não tem uso), `siglaTipo`, `numero`, `ano`, `uriOrgao`, `regime`, `codSituacao` e `url`.
3. **Modelo:** `CamaraPropositionStep` (implementado na Sessão 113), com o id da proposição **em texto, sem chave estrangeira para `CamaraProposition`**, `sequence` (inteiro **nulo** quando vazio), `occurred_at` (data e hora), `organ_code`, `description` e a execução de coleta que a viu. **Único em (proposição, `sequence`, `occurred_at`, `organ_code`, `description`) com `nulls_distinct=False`**, para a linha sem `sequencia` não duplicar a cada coleta. Migração `legislature/0008`, aditiva.
4. **Sem FK para `CamaraProposition`:** a maioria das proposições do arquivo (cerca de 36 mil de 46 mil) não existe lá, e uma FK faria a normalização esperar a coleta das proposições (a espera e a recusa do ADR 0031). A junção é na leitura, como as ligações do ADR 0033. A tramitação pode apontar para proposição que não está no polis.
5. **Normalização própria**, a partir da carga mais recente do conjunto, no padrão do ADR 0033: uma só transação, upsert pela chave em lotes de 1.000, falha fechada, nunca apaga, erros só com nomes de coluna e contagens. **Duplicata exata na chave dentro da carga vale uma linha** (38 chaves em 2026), e não recusa. Recusa: coluna da allowlist ausente, id da proposição ilegível em `uriProposicao`, `dataHora` inválida, caractere de controle ou texto acima do teto. `sequencia` vazia **não** recusa (vira nula); `sequencia` não numérica recusa.
6. **Tetos:** `siglaOrgao` 30 e `descricaoTramitacao` 200 caracteres (o medido é 10 e 57), 500.000 linhas por carga (o real é 118.724).
7. **Fuso de `dataHora`:** a fonte não declara. Gravar como horário de Brasília e **registrar como não verificado**; a exibição futura não deve converter.
8. **Fora desta fatia:** API e página, `despacho`, autores, temas, anos anteriores, generalizar o código copiado (ADR 0022, 0031, 0033: ainda sem terceira implementação além deste).

## Alternativas
- **`idTramitacao` como chave:** descartada; 400 valores em 118.724 linhas (medido).
- **(proposição, `sequencia`) com recusa em conflito:** descartada; os 13 conflitos reais e a linha vazia parariam a coleta todo dia (como o TAB na ementa, ADR 0033).
- **Chave sem `sequencia`:** descartada; perde 1.290 linhas em 2026 contra 40 com ela.
- **Hash da linha como chave:** descartada; esconde a regra num contrato implícito e não mostra o que é chave no esquema.
- **FK para `CamaraProposition`:** descartada; a maioria das proposições do arquivo não está lá (item 4).
- **Ingerir `despacho` como a `ementa`:** descartada pelo dono; texto livre com nomes de agentes públicos, sem avaliação do ADR 0005 e do P-16.
- **API `/proposicoes/{id}/tramitacoes`:** descartada; uma chamada por proposição e a lentidão medida da API (ADR 0031).
- **2025 e 2026 juntos:** descartado nesta fatia; mais 52 MB por dia sem a cobertura medida.

## Consequências
- Sexto conjunto da Câmara **sem licença declarada**, por decisão do dono; redistribuição e uso comercial ficam no P-16, e nada vai a público antes.
- **Download diário** de 38,5 MB (teto de 100 MB do `PlainCsvReader`) e cerca de 118 mil linhas gravadas por carga.
- Cobertura: 9.869 das 26.754 proposições das votações têm tramitação em 2026; as 16.885 restantes só terão com anos anteriores (**não medido**). A página futura deve dizer "tramitação em 2026".
- **40 linhas se perdem** pela chave (duplicatas idênticas); se a fonte passar a repetir mais, a coleta não para e o número aparece nas contagens.
- Reversível: desabilitar o conjunto no admin. A migração `0008` é aditiva (uma tabela nova); área do AGENTS §4, com confirmação do dono antes de gerá-la.
- **Não validado por mim:** o fuso de `dataHora`; o significado de `codSituacao` e `regime`; a estabilidade das chaves entre cargas; a coleta real (volume, tempo, memória do leitor com 38 MB); a interpretação jurídica (P-16).
