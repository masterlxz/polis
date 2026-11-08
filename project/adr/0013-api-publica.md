# 0013: API pública: política agora, lançamento na Etapa 2 (P-10)

**Data:** 2026-11-08

## Contexto
O P-10 pede a necessidade e o formato da API pública e a política de uso e limites. O PRD §14 diz que a plataforma "poderá" ter API para dados que "puderem ser legalmente redistribuídos" e lista rotas conceituais, sem decidir endpoints, autenticação, limites ou versionamento. Entradas:

- **Redistribuição é pergunta jurídica aberta** (ADR 0008; P-16). Uma API é redistribuição em massa e mais fácil de raspar que páginas.
- **Capacidade compartilhada** (ADR 0010 e 0011): 50 req/s sustentadas em um VPS único, divididos entre páginas, busca e API.
- **Atribuição obrigatória em toda resposta da API** (ADR 0008, decisão 3).
- **Nome civil e campos internos nunca são expostos** (ADR 0005, decisão 8).
- Não há consumidor externo identificado.

## Decisão
1. **Sem API pública na Etapa 1.** A interface é renderizada no servidor (ADR 0006); se alguma tela precisar de JSON, é interno, não documentado e não faz parte de contrato público.
2. **Lançamento previsto na Etapa 2**, depois do parecer do P-16 sobre redistribuição, como API de **leitura anônima com limite por IP**. Se o limite por IP não bastar, uma API com chave é decidida em ADR próprio e depende do P-09.
3. **Política que valerá quando existir:**
   - **Somente leitura** e **versionada** em `/api/v1/`; mudança que quebra contrato vira `/api/v2/`, sem alterar a anterior sem aviso.
   - **Atribuição em toda resposta:** fonte, data da coleta, link do original e, quando aplicável, licença (ADR 0008).
   - **Mesmo filtro de dados da interface:** o que a tela não mostra, a API também não; nunca campo interno nem nome civil (ADR 0005).
   - **Limites numéricos só depois de medir:** nenhum valor de req/min é fixado aqui; saem do teste de carga do ADR 0010, para que a API não degrade as páginas.
   - Documentação em OpenAPI (PRD §12, "API documentada").
4. **As rotas do PRD §14 são ilustrativas.** Nenhuma é compromisso; em especial, `judicial/cases` depende do P-16 e da Etapa 5.
5. **Biblioteca da API** (DRF, django-ninja ou outra) **não é decidida aqui**: é dependência nova e pede aprovação própria na implementação.

## Alternativas
- **API anônima com limite por IP já na Etapa 1:** expõe dado em massa antes do parecer do P-16 e divide a capacidade do VPS único, sem consumidor conhecido. Descartada.
- **API com chave desde o início:** depende do P-09 (fora desta rodada) e adiciona código de conta sem necessidade demonstrada. Descartada por ora.

## Consequências
- A Etapa 1 fica menor e sem superfície pública extra de dado pessoal.
- O modelo de dados e as telas já nascem sob as regras de atribuição e de filtro; assim a API, quando vier, é uma segunda visão do mesmo conteúdo, não um segundo caminho de exposição.
- Pesquisadores e parceiros não têm API até a Etapa 2; a atribuição e a licença por conjunto (ADR 0008) podem permitir, antes disso, um download em lote por decisão própria, **não prevista aqui**.
- **Não verificado:** nenhuma demanda externa por API foi medida; a escolha da biblioteca e dos limites segue em aberto.
