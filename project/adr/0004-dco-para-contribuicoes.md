# 0004: Política de contribuição: DCO

**Data:** 2026-11-05

## Contexto
O ADR 0002 licenciou o código sob AGPL-3.0 e deixou em aberto (P-01) se as contribuições externas de código seguiriam CLA ou DCO, bloqueando qualquer PR externo até a decisão. Hoje não há contribuidor externo, então a escolha ainda não custa nada a ninguém.

## Decisão
Contribuições de código seguem o **DCO** (*Developer Certificate of Origin*): cada commit leva `Signed-off-by:` (`git commit -s`), declarando que a pessoa tem o direito de enviar aquele código sob a licença do projeto. Cada contribuidor mantém o copyright do que enviou, sob a mesma AGPL-3.0 (licença de entrada igual à de saída).

A aplicação (`CONTRIBUTING.md` e checagem do sign-off no CI) entra em PR separado. Até lá, PR externo de código continua não aceito.

## Alternativas
- **CLA:** o contribuidor assina um contrato com licença ampla ao projeto, o que permitiria relicenciar ou vender licença comercial (dual license). Descartado porque: aumenta o atrito para contribuir; exige texto jurídico e bot de assinaturas; um CLA de *cessão* é frágil no Brasil, onde os direitos morais de autor são inalienáveis (Lei 9.610), e um de *licença* pede revisão jurídica (P-16); e não há hoje sinal de que dual license seja um caminho de financiamento (P-11 em aberto).
- **Não aceitar contribuição de código:** mantém tudo simples e deixa a opção de relicenciar, mas contraria a ideia de plataforma aberta. Continua valendo como estado transitório até a aplicação do DCO.

## Consequências
- Baixo atrito para contribuir; padrão conhecido (kernel Linux e outros).
- **Relicenciar exige o consentimento de todos os contribuidores.** Se o modelo de financiamento passar a incluir dual license, trocar para CLA depois exige o aceite de quem já contribuiu. Trocar de CLA para DCO seria mais fácil, por isso a escolha é assimétrica; aceitamos esse custo.
- A AGPL já obriga quem hospeda versão modificada a abrir o código, com ou sem CLA.
- Precisa de uma checagem automática de `Signed-off-by` e de um `CONTRIBUTING.md` explicando o `-s`.
- Interpretação jurídica não validada por especialista (P-16).
