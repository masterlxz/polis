# 0021: Habilitar a coleta da lista de deputados da Câmara (decisão do dono, ADR 0008)

**Data:** 2026-11-10

## Contexto
A Câmara dos Deputados não declara licença nem regra de atribuição para os Dados Abertos (`fontes/camara.md`, leitura de 2026-11-06). O que existe é o FAQ ("totalmente de graça", sem cadastro, uso comercial permitido sem restrição) e o Art. 27 do Ato da Mesa 45/2012, que limita informações pessoais (inclusive número de documentos de identificação) e, no § 8º, trata como de interesse público o que decorre de investidura em cargo ou função pública. O ADR 0008 (decisão 1) só deixa habilitar um conjunto sem licença declarada por decisão escrita do dono, com o motivo; a decisão 9 deixa a redistribuição, a exportação em massa e o uso comercial para o P-16 e impede que algo vá a público antes.

O ADR 0009 põe a Câmara logo depois da vertical do TSE. A primeira fatia é só a coleta bruta da lista de deputados em exercício (`/deputados`, legislatura atual, 513 itens em 6 páginas, medido em 2026-11-10).

## Decisão
1. **Habilitar só `camara/deputados`**, pela API paginada (`itens=100`, em série, pausa de 3 s, `User-Agent` próprio, parada em 403: ADR 0008, decisões 4 e 5). O dono habilita no admin (`license_basis = owner_decision`, justificativa abaixo); o cadastro (`seed_sources`) nunca habilita nem copia a justificativa.
2. **Allowlist de 6 campos:** `id`, `uri`, `nome`, `siglaPartido`, `siglaUf`, `idLegislatura`. Descartados na leitura: `email`, `urlFoto`, `uriPartido`. Nunca `cpf`, nome civil nem data de nascimento (ADR 0005; a listagem nem os traz).
3. **Falha fechada com tolerância zero:** campo permitido ausente, valor que não seja texto, número ou nulo, valor longo demais, id repetido entre páginas, página fora do formato ou páginas demais param a carga inteira, sem gravar nada e sem apagar a anterior (ADR 0005, decisões 6 e 9).
4. **Nada vai a público** antes do P-16 (ADR 0008, decisão 9). A página e a API pública do deputado são fatias futuras e levam a atribuição "Câmara dos Deputados, Dados Abertos" mais a data da coleta (ADR 0008, decisão 3).
5. **Justificativa para o admin (campo `license_justification`):** "Decisão do dono em 2026-11-10: a Câmara não declara licença; o FAQ dos Dados Abertos libera uso gratuito, inclusive comercial, sem restrição; dado de parlamentar em exercício é de interesse público (Ato da Mesa 45/2012, Art. 27 § 8º); só lista de deputados com allowlist de 6 campos, sem dado pessoal; nada público antes do P-16 (ADR 0008, decisão 9; ADR 0021)."

## Alternativas
- **Não coletar a Câmara até o P-16:** descartada pelo dono. O FAQ é uma declaração de uso livre da própria fonte, a coleta é só leitura de dado público com allowlist mínima e nada vai a público antes da validação; esperar travaria a segunda fonte e o modelo unificado do ADR 0009.
- **`deputados.csv` em massa (7.889 linhas, todas as legislaturas):** descartada por ora. Não tem partido nem UF e não tem coluna de id (vem no fim da `uri`), então não sustenta uma página útil sozinho. Pode entrar depois para o histórico.
- **Habilitar já a página pública:** descartada. Depende do P-16.

## Consequências
- Primeira fonte sem licença declarada coletada. Se a Câmara passar a declarar licença ou termos, esta decisão é reconferida (o ADR 0008, decisão 2, só vigia licença por CKAN; aqui não há checagem automática).
- O pipeline ganha o formato `json` (lista paginada) com o mesmo contrato do `zip_csv`: um arquivo, um SHA-256, retenção, `IngestionRun`.
- **Não validado por mim:** a aplicação do Art. 27 aos dados que a API devolve (o detalhe `/deputados/{id}` traz CPF, que seguimos sem coletar); a interpretação jurídica é do P-16.
- Reversível: desabilitar o `Dataset` no admin; as cargas já feitas seguem a retenção de 3 execuções.
