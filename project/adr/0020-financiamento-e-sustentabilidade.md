# 0020: Financiamento e sustentabilidade: princípios e vetos (P-11)

**Data:** 2026-11-08

## Contexto
O P-11 pede o modelo de financiamento e sustentabilidade. O PRD exige neutralidade (§3: não favorecer partidos, ideologias, candidatos ou instituições) e independência (metodologia e política editorial claras). O ADR 0011 fixou um teto de cerca de US$ 20/mês de infraestrutura, **pago pelo dono**, e deixou aberto que o volume-alvo pode não caber nesse teto (o teste de carga do ADR 0010 decide). O ADR 0002 mantém o código em AGPL-3.0 e os dados conforme as fontes. Nada foi medido: custo real de operação, público, elegibilidade a editais e exigências jurídicas de receber doações são desconhecidos. Por isso o dono escolheu **só princípios e restrições**, sem modelo concreto. Este ADR não implementa nada.

## Decisão
1. **Infraestrutura bancada pelo dono por enquanto**, dentro do teto do ADR 0011, até um gatilho de reabertura (decisão 6). Nenhuma captação é prometida nem planejada agora.
2. **Vetos de saída.** O projeto não aceita recurso, em dinheiro ou em espécie (serviço, crédito, infraestrutura), de:
   - a) partidos, candidatos e campanhas, incluindo recursos dos fundos partidário e eleitoral;
   - b) governos e órgãos públicos monitorados pela plataforma (hoje ou no escopo das etapas do PRD §15);
   - c) publicidade, rastreamento de leitores para terceiros e venda de dados de usuários (o ADR 0019 já exclui cookie de identificação de visitante);
   - d) empresas com interesse regulado que apareçam como doadoras, fornecedoras ou contratadas nos dados que a plataforma publica.
3. **Critério, não lista.** O veto d é aplicado por critério (a empresa ou seu grupo aparece nos dados publicados em papel que gere conflito com a fiscalização). A lista concreta muda a cada eleição e a cada carga, e não é mantida neste ADR; na dúvida, o recurso é recusado até decisão do dono.
4. **Independência editorial.** Financiador nenhum influencia fonte, método, ranking, busca, texto ou prioridade de módulo. Ninguém compra tratamento diferente na plataforma.
5. **Transparência do apoio.** Todo apoio recebido é público: quem, quanto e quando, com a mesma regra de rastreabilidade que o PRD pede para os dados. Detalhes de privacidade de doador pessoa física dependem do P-16.
6. **Gatilhos para reabrir** (propostos por mim; o dono pode trocar): (i) abrir a plataforma ao público; (ii) o teste de carga do ADR 0010 estourar o teto do ADR 0011; (iii) o custo real de VPS e backup divergir do teto. Quando um disparar, abre-se ADR novo com o modelo concreto.
7. **Código e dados independentes de dinheiro.** A AGPL-3.0 e a publicação de dados abertos não dependem de nenhum apoio, e nenhuma funcionalidade fica atrás de pagamento na Etapa 1.
8. **Fontes aceitáveis em tese** (sem escolha agora): doações de pessoas físicas e apoio institucional não vetado (fundações, editais). Cada uma passa pelos vetos e vira ADR próprio quando houver gatilho.

## Alternativas
- **Modelo concreto agora (doações recorrentes mais editais, com metas):** descartada; exigiria custo real, público e elegibilidade que ninguém mediu, e as metas seriam chute.
- **Só registrar como adiado:** descartada; não fixaria os vetos, que o dono já decidiu e que valem desde o primeiro apoio, inclusive um informal.
- **Aceitar qualquer apoio com divulgação:** descartada; divulgar não desfaz o conflito de interesse com quem a plataforma fiscaliza.

## Consequências
- Custo e risco financeiro ficam com o dono: se o teste de carga exigir máquina acima do teto, ou o dono sobe o teto do próprio bolso, ou as metas caem por ADR novo (ADR 0011), e isso dispara a reabertura.
- Sem receita planejada, a continuidade do projeto depende do dono. Não há plano para o caso de ele parar; registrado como risco, não resolvido.
- Os vetos limitam o universo de apoiadores (por exemplo, um fornecedor de infraestrutura que também venda ao governo precisa ser avaliado pelo veto b e d antes de aceitar crédito).
- O veto d é amplo e subjetivo; aplicá-lo exige julgamento caso a caso e pode gerar recusas discutíveis.
- Não resolve a forma jurídica para receber dinheiro (pessoa física, associação, CNPJ), tributação nem LGPD de doadores: seguem no P-16, sem parecer.
- Habilita o ADR futuro de captação, que já nasce com as restrições escritas.
