# 0017: Armazenamento de documentos: link e hash por padrão, backend adiado (P-07)

**Data:** 2026-11-08

## Contexto
O P-07 pede a estratégia de armazenamento de documentos. Na Etapa 1 (ADR 0009) tudo é dado estruturado de TSE, Câmara e Senado: o bruto filtrado vive no Postgres (ADR 0005) e nenhum PDF ou arquivo de terceiros é guardado. Documentos (diários oficiais, atos, textos de proposições, PRD §6.10) só aparecem a partir da Etapa 2, e a IA (P-08, Etapa 4) pode precisar do texto. **Nenhuma fonte de documentos foi medida** (volume, tamanho, licença, estabilidade das URLs). Duas forças puxam em sentidos opostos: verificabilidade (PRD §4, consultar o original) e o PRD §8.2 (disponível não significa redistribuível), mais o teto de custo e o disco de um VPS único (ADR 0011). O dono escolheu decidir só os princípios agora.

## Decisão
1. **Etapa 1:** nenhum arquivo de terceiros é armazenado. Vale só o bruto filtrado do ADR 0005.
2. **Padrão: link e hash, sem cópia.** Para um documento, guarda-se a URL de origem, o SHA-256, a data de coleta e metadados. O arquivo não é copiado.
3. **Cópia do arquivo é exceção, por fonte,** e só quando (a) o portão de licença do ADR 0008 permitir armazenar e redistribuir e (b) houver motivo concreto: URL instável ou necessidade de extrair texto para busca ou IA. A exceção é registrada no cadastro de fontes.
4. **Dado pessoal:** documento com dado fora da allowlist segue o ADR 0005 (filtrar ou não copiar). Retirada pela fonte apaga a cópia e deixa a lápide.
5. **Interface única de armazenamento** (como o módulo de busca do ADR 0012), sem recurso exclusivo de provedor (ADR 0011, decisão 6). O backend (disco do VPS ou armazenamento de objetos compatível com S3, no Brasil) é escolhido por **ADR próprio**, na primeira fonte que exigir cópia.
6. **Conteúdo externo é não confiável** (PRD §12): nunca é servido inline como página do polis; PDFs vão como link para a fonte ou download, e texto extraído passa por sanitização antes de exibir ou ir a uma IA.
7. **Backup:** cópias guardadas seguem o ADR 0011 (diário, fora da máquina do banco, no Brasil).

## Alternativas
- **Escolher o backend agora:** sem volume nem fonte medidos, seria palpite; descartada.
- **Copiar sempre:** máxima verificabilidade, mas custo de disco contra o teto de US$ 20/mês e risco de ferir termos de fonte sem licença declarada (a Câmara não declara); descartada.
- **Sem padrão, decidir por fonte:** cada fonte reabriria a questão; descartada.

## Consequências
- Sem cópia, se a fonte alterar ou remover o arquivo o hash prova que mudou, mas o polis não tem mais o original. É o custo do padrão; a decisão 3 é a válvula.
- A verificabilidade da Etapa 1 depende de a fonte manter as URLs. A premissa não foi testada.
- A interpretação jurídica de cópia e redistribuição segue no P-16, sem parecer.
- Habilita o P-08: a necessidade de texto para IA é um dos motivos que justificam cópia (decisão 3b).
- **Fica aberto:** backend concreto, modelo de dados do documento, extração de texto, limites de tamanho e retenção das cópias.
