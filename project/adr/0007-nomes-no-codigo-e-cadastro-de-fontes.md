# 0007: Nomes em inglês no código e modelo do cadastro de fontes

**Data:** 2026-11-06

## Contexto
O primeiro app de domínio (`apps/sources`, PR #21) fixou duas coisas que valem para todo o código seguinte e que não eram óbvias: em que idioma ficam os nomes de modelos e campos, e como o cadastro de fontes (PRD §8.1) e o registro de coletas (PRD §9.1) se relacionam com a allowlist do ADR 0005. O PRD, os ADRs e os documentos de `project/fontes/` estão em português; o código ainda não tinha convenção.

## Decisão
1. **Identificadores de código em inglês** (apps, modelos, campos, funções): `Source`, `Dataset`, `IngestionRun`, `allowed_columns`. **Interface em português do Brasil**: `verbose_name`, `help_text`, rótulos de `choices` e textos do admin. Quem escolheu foi o dono, entre "português no domínio" e "inglês no código".
2. **Correspondência dos termos do domínio** (para o código não derivar):

   | Documentos (português) | Código |
   |---|---|
   | fonte | `Source` |
   | conjunto de dados (um arquivo ou endpoint de uma fonte) | `Dataset` |
   | execução de coleta | `IngestionRun` |
   | allowlist / colunas permitidas | `Dataset.allowed_columns` |
   | colunas internas (nunca expostas) | `Dataset.internal_columns` |
   | estado da integração | `Source.status` |

   Termos novos (proposição, votação, lápide) ganham o nome em inglês quando o modelo correspondente for criado, e entram nesta tabela ou no `GLOSSARY.md`.
3. **Estrutura do cadastro:** `Source` 1—N `Dataset` 1—N `IngestionRun`. A **allowlist mora no `Dataset`**, porque as colunas mudam por arquivo, e um `Dataset` só pode ser `enabled` com `allowed_columns` não vazia (`CheckConstraint` no banco, ADR 0005, decisão 1). As colunas internas são um subconjunto das permitidas (validado em `clean()`). `on_delete=PROTECT` nas duas chaves estrangeiras: apagar fonte ou conjunto com histórico é recusado (PRD §9.1).
4. **`IngestionRun` guarda só o que o ADR 0005 permite:** nomes de colunas descartadas, contagens, URL, `ETag`, datas e o SHA-256 do arquivo original. **Sem texto livre de erro:** só `error_code`, de um conjunto fechado (`download`, `schema`, `malformed_row`, `hash`, `other`), para que nenhum valor de linha chegue ao banco ou aos logs. Restrições no banco: sucesso exige SHA-256 hexadecimal minúsculo de 64 caracteres e data de fim; falha exige `error_code` e data de fim; em andamento não tem fim; `rows_loaded ≤ rows_read`.
5. **Execução concluída é imutável**, barrada no `save()` e no admin (só leitura, sem adicionar nem apagar).
6. **PostgreSQL específico:** `ArrayField` (`django.contrib.postgres`) para as listas de colunas, coerente com o ADR 0006 (PostgreSQL é o único banco).

Não decidido aqui: o idioma de docstrings, comentários e nomes de teste (até agora em português, por prática, sem discussão); a lista final de estados da integração e de códigos de erro (pode crescer por migração).

## Alternativas
- **Português no código** (`Fonte`, `ConjuntoDeDados`): combina com os documentos e com termos sem boa tradução, mas foge do padrão da maioria dos projetos abertos e aumenta a barreira para contribuidores que não leem português. Descartado pelo dono.
- **Só `Source`, com a allowlist em JSON por nome de arquivo:** menos tabelas, mas a execução não teria chave estrangeira para o arquivo e a validação ficaria só no código. Descartado.
- **Campo livre `error_message` na execução:** mais útil para depurar, mas a exceção de um parser costuma citar a linha, onde estão nome civil, data de nascimento e CPF. Descartado; o detalhe vai para log estruturado sem valores.
- **Imutabilidade por trigger no banco:** protege também `QuerySet.update()` e SQL direto, mas é mais código e mais difícil de testar. Fica para quando houver necessidade.

## Consequências
- Todo código novo de domínio usa nomes em inglês; a tabela acima evita que "fonte" vire `Source` num lugar e `Origin` em outro.
- Documentação e interface continuam em português; quem lê o código precisa mapear termos (custo aceito).
- A imutabilidade vale só na aplicação: `QuerySet.update()`, SQL direto e uma corrida entre duas gravações da mesma execução a contornam (não verificado). Se a rastreabilidade virar requisito de auditoria, adicionar trigger.
- Estados da integração e códigos de erro novos exigem migração, o que também documenta a mudança.
- Habilita o conector do TSE: o leitor passa a gravar `IngestionRun` e a consultar `Dataset.allowed_columns`.
