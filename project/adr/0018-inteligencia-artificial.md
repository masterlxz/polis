# 0018: Inteligência artificial: princípios e restrições, provedor adiado (P-08)

**Data:** 2026-11-08

## Contexto
O P-08 pede provedores, modelos, RAG, embeddings e custos. A IA só entra na Etapa 4 (ADR 0009), depois de Legislativo e eleições, experiência pública e finanças. **Nenhum provedor, modelo, preço, qualidade em português ou taxa de erro foi medido**, e esses fatores mudam até lá. O PRD §10 já fixa o papel da IA (camada de pesquisa, nunca fonte primária) e as regras do §10.1. O que falta é transformá-las em restrições de projeto e decidir o que pode sair da máquina. O dono escolheu fixar só princípios e restrições agora e permitir API externa apenas com dado público.

## Decisão
1. **Quando:** IA só na Etapa 4. Nenhuma funcionalidade de IA nas Etapas 1 a 3.
2. **Regras do PRD §10.1 como requisitos de aceite:** resposta factual só com fonte verificável (link e hash, ADR 0017), identificada como análise automatizada, com "sem evidência suficiente" como resposta válida; sem ranking de qualidade política e sem recomendar candidato.
3. **Citação verificada por código, não pelo modelo:** toda citação, número ou data da resposta precisa casar com um registro ou documento realmente recuperado na consulta; o que não casar é descartado ou a resposta é recusada.
4. **Sem acesso direto ao banco** (PRD §10.1): a IA só chama funções de leitura fixas e parametrizadas, como o módulo `buscar` do ADR 0012. Nunca SQL livre, nunca escrita.
5. **Conteúdo externo é dado, nunca instrução** (ADR 0017, decisão 6): vem delimitado e a IA não executa ação a partir dele.
6. **Provedor externo permitido só com dado público já exibível:** nunca campos internos (nome civil, data completa de nascimento, ADR 0005), nunca dado identificável de usuário; consultas sem identificador. É **exceção explícita** à regra "tudo no Brasil" do ADR 0011, só para esse tráfego. **Confirmar no P-16 antes de lançar.**
7. **Interface única de provedor**, sem recurso exclusivo de um fornecedor (ADR 0011, decisão 6), para trocar de modelo ou usar modelo aberto depois.
8. **Custo:** limite mensal de gasto e limite por IP (ADR 0013) antes de abrir ao público; os valores saem de um spike da Etapa 4. Uso e custo registrados (PRD §13).

## Alternativas
- **Escolher provedor e modelo agora:** sem medição, e preços e modelos mudam até a Etapa 4; descartada.
- **Tudo no Brasil ou self-hosted:** coerente com o ADR 0011, mas inferência própria exige GPU e não cabe no teto de cerca de US$ 20/mês; descartada por ora.
- **Spike de RAG agora:** depende de documentos (P-07) e de dados reais que ainda não existem; descartada.

## Consequências
- A garantia contra invenção vem da verificação em código (decisão 3), não de pedir ao modelo que não invente. Isso exige guardar o que foi recuperado por resposta.
- Provedor externo significa dado público saindo do Brasil; a legalidade disso é pergunta do P-16, sem parecer.
- O custo da IA pode estourar o teto do ADR 0011; o limite da decisão 8 é obrigatório, não opcional.
- **Fica aberto:** provedor e modelo, embeddings, desenho de RAG, orçamento, avaliação de qualidade em português e política de retenção de consultas.
