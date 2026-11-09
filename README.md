# polis

Plataforma aberta de transparência e inteligência cívica: reúne, organiza e apresenta informações públicas sobre o Brasil (representantes, instituições, votações, gastos, decisões e políticas públicas), sempre com rastreabilidade até a fonte original.

**Status:** fundação. Há o [PRD](project/PRD.md), as decisões iniciais, a medição das fontes, a stack ([ADR 0006](project/adr/0006-stack-do-nucleo.md)) e o esqueleto do projeto Django (Python 3.14, Django 6.1, PostgreSQL 18). Ainda não há modelos, conectores nem ingestão.

## Desenvolvimento

### Com Docker Compose (recomendado)

Requer Docker com o plugin Compose. Copie `.env.example` para `.env` e preencha ao menos `DJANGO_SECRET_KEY` e `POSTGRES_PASSWORD` (sem eles o Compose recusa subir).

```bash
docker compose up -d --wait db          # PostgreSQL 18, só em 127.0.0.1:5432
docker compose run --rm web python manage.py migrate
docker compose up web                   # http://127.0.0.1:8000/admin/login/
docker compose run --rm web pytest      # testes dentro do contêiner
docker compose up -d web front          # front Next.js em http://127.0.0.1:3000/saude/
```

O front (`web/`, Next.js) chama a API interna do Django pela rede do Compose (`http://web:8000`); o build e os testes dele rodam no CI (job `web`), não na sua máquina.

O `Dockerfile` e o `compose.yaml` são só de desenvolvimento; a imagem de produção depende da decisão de hospedagem (P-04).

### Sem Docker

Requer [`uv`](https://docs.astral.sh/uv/) e um PostgreSQL 18. Preencha as variáveis do `.env.example` e exporte-as (o CI em `.github/workflows/tests.yml` serve de referência).

```bash
uv sync --locked
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Os testes são validados pelo CI (jobs `tests` e `compose`).

## Princípios

Neutralidade, rastreabilidade, separação entre dado e análise, privacidade e verificabilidade. A IA é camada de pesquisa, nunca fonte primária. Detalhes no [PRD](project/PRD.md), seção 4 e 10.

## Documentação

- [`project/INDEX.md`](project/INDEX.md): ponto de entrada e histórico de decisões.
- [`project/PRD.md`](project/PRD.md): requisitos do produto.
- [`project/adr/`](project/adr/): registros de decisão de arquitetura.

## Licença

- **Código:** [GNU AGPL-3.0](LICENSE). Quem rodar uma versão modificada como serviço de rede precisa disponibilizar o código-fonte aos usuários desse serviço.
- **Dados:** a licença acima **não** cobre os dados das fontes públicas. Cada fonte tem termos próprios de uso e redistribuição, avaliados caso a caso antes de qualquer integração (PRD, seção 8.2).

Copyright (C) 2026 Fabio Anjos Junior.

## Contribuições

Contribuições de código são aceitas sob o DCO ([ADR 0004](project/adr/0004-dco-para-contribuicoes.md)): cada commit precisa de `Signed-off-by`. O passo a passo está no [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues com sugestões e correções de documentação também são bem-vindas.
