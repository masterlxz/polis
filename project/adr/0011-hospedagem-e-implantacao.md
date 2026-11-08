# 0011: Hospedagem e implantação: VPS único no Brasil (P-04)

**Data:** 2026-11-08

## Contexto
O P-04 pede a arquitetura de implantação e a hospedagem. As entradas são o ADR 0006 (monólito Django + PostgreSQL 18, Docker Compose de desenvolvimento já existente, projeto aberto e self-hostable), o ADR 0010 (leitura pública 99,5%/mês, RPO e RTO de 24 h, sem alta disponibilidade multi-zona; 100 milhões de linhas como estimativa) e três respostas do dono: opção A (VPS único), dados **no Brasil** e teto de cerca de **US$ 20/mês** nesta fase. O financiamento (P-11) segue aberto.

## Decisão
1. **Arquitetura:** um único servidor virtual (VPS) rodando, com o Docker Compose, o Django, o PostgreSQL 18 e um proxy reverso com TLS. Um só ambiente de produção; o de teste (para o teste de carga do ADR 0010, decisão 6) pode ser o mesmo tipo de máquina, criado sob demanda.
2. **Região:** servidor **e backups no Brasil**. Dados de fonte pública são hoje o grosso do banco, mas a transferência internacional de dados pessoais é pergunta jurídica ainda sem parecer (P-16); manter tudo no Brasil evita abri-la.
3. **Backup:** diário e automático, **fora da máquina do banco** e também no Brasil (armazenamento de objetos ou outro servidor), com teste de restauração periódico (ADR 0010, decisão 2). A restauração é testada de verdade, não presumida.
4. **Teto de custo:** cerca de US$ 20/mês de infraestrutura nesta fase. É um teto de partida, não uma estimativa: o custo real depende do provedor e do tamanho da máquina e **não foi verificado**.
5. **Provedor e plano ficam para a hora de implantar**, escolhidos entre os que têm datacenter em São Paulo e cabem no teto, com preço e região conferidos na página oficial de cada um no dia da contratação. A busca desta sessão apontou Vultr, Linode/Akamai e LightNode como candidatos, mas só em fontes de terceiros, desatualizadas e conflitantes; **nenhum preço foi aceito como fato**.
6. **Portabilidade:** nada no projeto pode depender de um recurso exclusivo de provedor. O Compose de produção deve rodar em qualquer VPS com Docker (requisito do projeto aberto, ADR 0006).

## Alternativas
- **VPS + PostgreSQL gerenciado:** backup e restauração a cargo do provedor, menos operação, mas custo maior e provavelmente acima do teto; descartada pelo orçamento.
- **PaaS completo (Fly.io, Render e similares):** menos operação, mas lock-in, custo variável e menos aderência ao projeto self-hostable; descartada.
- **Provedor no exterior (mais barato e com mais opções):** descartada pela decisão do dono de exigir Brasil, enquanto o P-16 não tiver parecer.
- **Servidor dedicado ou Kubernetes:** desproporcional para 99,5% e 50 req/s.

## Consequências
- **Ponto único de falha:** uma máquina só. É coerente com 99,5% e RTO de 24 h, mas uma falha de hardware ou do provedor significa restaurar em outra máquina a partir do backup; o RTO de 24 h só vale se a restauração tiver sido ensaiada.
- **Operação por conta do dono:** atualização do sistema, do Postgres, do Docker, monitoramento e backup. Isso exige um runbook curto (a escrever na implantação) e monitoramento de disponibilidade e de erros (PRD §12).
- **Risco de dimensionamento (importante):** 100 milhões de linhas com índices de busca (P-06) e 50 req/s podem **não caber** em uma máquina que respeite o teto de US$ 20. Não há medição que diga. O teste de carga do ADR 0010 decide: se falhar, ou o teto sobe (P-11), ou as metas caem, por ADR novo, nunca em silêncio.
- **Disco:** o bruto filtrado guarda 3 cargas por conjunto (ADR 0005); o espaço em disco precisa ser dimensionado com isso e ainda não foi calculado.
- Habilita o P-06 (busca): como o banco e a busca ficam na mesma máquina, uma busca dedicada separada (outro serviço) pesa no custo e na operação.
- Não resolve **autenticação** (P-09), **documentos** (P-07) nem **financiamento** (P-11).
