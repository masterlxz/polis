# 0002: Licença do código: AGPL-3.0

**Data:** 2026-10-31

## Contexto
O PRD lista "licença e estratégia de código aberto" como decisão em aberto (§18). O polis é uma plataforma servida pela web, com API pública prevista. Os outros projetos do autor usam MIT.

## Decisão
O **código** é licenciado sob **GNU AGPL-3.0**. O texto em `LICENSE` é o oficial, obtido da API do GitHub (`licenses/agpl-3.0`).

Os **dados** das fontes públicas **não** herdam a AGPL: cada fonte tem termos próprios de uso, armazenamento e redistribuição, avaliados antes de qualquer integração (PRD §8.2). Quando a plataforma publicar dados derivados, a licença desses dados será decidida por fonte e registrada à parte.

## Alternativas
- **MIT:** igual aos outros repos e de máxima adoção, mas qualquer um poderia fechar um fork e operá-lo como serviço sem devolver nada.
- **Apache-2.0:** permissiva, com concessão explícita de patentes; mesmo problema da MIT quanto a forks fechados.
- **Sem licença por enquanto:** adiaria a decisão, mas o repositório é público desde o início (ADR 0003) e, sem licença, ninguém teria permissão de uso.

## Consequências
- Quem rodar uma versão modificada como serviço de rede precisa oferecer o código-fonte aos usuários.
- Algumas empresas evitam AGPL, o que pode reduzir a adoção corporativa.
- **Quase irreversível:** código publicado sob AGPL não pode ser retirado; relicenciar exige o consentimento de todos os titulares. Por isso não aceitamos contribuições de código antes de decidir CLA ou DCO (`PENDING.md`).
- Dependências precisam ser compatíveis com AGPL-3.0; checar a licença de cada uma ao adotá-la.
- Titular do copyright: Fabio Anjos Junior.
