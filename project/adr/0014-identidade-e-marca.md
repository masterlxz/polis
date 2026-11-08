# 0014: Identidade, linguagem da marca e domínio (P-17)

**Data:** 2026-11-08

## Contexto
O ADR 0001 escolheu o nome **polis** e aceitou o risco do homônimo `pol.is` (plataforma de deliberação pública), deixando identidade visual, linguagem da marca e domínio em aberto. O PRD §4 fixa neutralidade, acessibilidade e independência como princípios; para uma plataforma de transparência sobre política, cor, símbolo e tom de texto podem sugerir lado e portanto são decisões de produto, não só estéticas.

## Decisão
1. **Nome com descritor.** "polis" aparece sempre acompanhado de uma descrição ("transparência e inteligência cívica", do título do PRD) no título das páginas, no rodapé, na página inicial e nos metadados de busca. O descritor e o domínio diferenciam do `pol.is`; o nome não muda (ADR 0001 mantido).
2. **Linguagem da marca:** português do Brasil simples, sem juridiquês e sem adjetivos valorativos sobre pessoas ou partidos. Fato, alegação, opinião e interpretação aparecem separados (PRD §4); texto gerado por IA, quando existir, é rotulado como tal.
3. **Neutralidade visual:** a marca não usa cores nem símbolos associados a partidos, campanhas ou à bandeira nacional como identidade (paleta sóbria e neutra). Nenhum partido ou candidato recebe cor própria na interface por padrão; qualquer uso da cor de um partido (por exemplo, em gráficos) é opcional, sempre acompanhado de rótulo textual, e não é o padrão.
4. **Domínio:** critérios agora, compra na implantação (ADR 0011). Preferir um domínio sob `.br` (Registro.br), que contenha "polis" e não seja confundível com `pol.is`. **Disponibilidade, elegibilidade do tipo de domínio e a compra não foram verificadas** e são do dono, no momento de implantar. Nenhum domínio é comprado por este ADR.
5. **Logotipo e paleta concretos** ficam como trabalho de design futuro, restritos por esta decisão; não bloqueiam a Etapa 1.

## Alternativas
- **Renomear agora:** evitaria a confusão com `pol.is`, mas custa ajustar repositório, documentos e links e reabre o ADR 0001; descartada.
- **Adiar a decisão de marca até abrir ao público:** descartada para a neutralidade visual e a linguagem, que orientam as telas desde o início; o que se adia é só o logotipo, a paleta e o domínio.
- **Escolher e comprar o domínio agora:** desnecessário antes da implantação e dependente de disponibilidade que não verifiquei.

## Consequências
- Telas e textos da Etapa 1 já nascem com tom e paleta neutros, o que evita retrabalho.
- Risco de confusão com `pol.is` continua; o descritor mitiga, não elimina.
- Registro de marca (INPI) e disputa de nome não foram avaliados e seriam pergunta jurídica (P-16), fora deste ADR.
- Fica aberto: logotipo e paleta concretos, e a compra do domínio na implantação.
