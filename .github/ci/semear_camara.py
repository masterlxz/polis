"""Semente do teste de ponta a ponta das tramitações da Câmara (job `ponta-a-ponta`).

Roda SÓ no CI, dentro do contêiner `web` do Compose de desenvolvimento, pelo stdin:
`docker compose exec -T web python manage.py shell < .github/ci/semear_camara.py`.
Dados todos sintéticos, no formato do `tests/test_camara_proposition_api.py` (de onde vêm os
valores). Grava com o ORM, sem passar pelo normalizador (esse é provado pelos testes dele).

O que cada linha prepara para o teste `web/e2e/camara.e2e.test.mjs`:
- proposição 14666 com 4 tramitações gravadas fora de ordem: três no mesmo instante (duas com
  `sequencia` 152 que só se separam pelo órgão, e uma sem `sequencia`, que sai depois) e uma
  posterior com HTML na descrição;
- proposição 14667 sem tramitação;
- tramitação da proposição 99999, que o polis não conhece como proposição (a rota deve dar 404);
- votação 9000001-1 ligada às duas proposições, para o link "Ver tramitação (N)".
"""

from datetime import UTC, date, datetime

from apps.legislature.models import (
    CamaraProposition,
    CamaraPropositionStep,
    CamaraVoting,
    CamaraVotingProposition,
)
from apps.sources.models import Dataset, IngestionRun, Source

fonte, _ = Source.objects.get_or_create(
    slug="camara",
    defaults={
        "name": "Câmara dos Deputados: Dados Abertos",
        "institution": "Câmara dos Deputados",
        "official_url": "https://example.org",
        "access_type": Source.AccessType.FILE,
    },
)


def criar_run(slug, nome, url, started_at):
    conjunto, _ = Dataset.objects.get_or_create(
        source=fonte,
        slug=slug,
        defaults={
            "name": nome,
            "url": url,
            "format": Dataset.Format.CSV,
            "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
            "license_justification": "Semente descartável do CI.",
        },
    )
    return IngestionRun.objects.create(
        dataset=conjunto, source_url=conjunto.url, started_at=started_at
    )


run_votacao = criar_run(
    "votacoes-2026",
    "Votações da Câmara (2026)",
    "https://example.org/arquivos/votacoes/csv/votacoes-2026.csv",
    datetime(2026, 11, 26, 7, 0, tzinfo=UTC),
)
run_proposicao = criar_run(
    "votacoes-proposicoes-2026",
    "Proposições das votações da Câmara (2026)",
    "https://example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes.csv",
    datetime(2026, 11, 26, 8, 0, tzinfo=UTC),
)
run_tramitacao = criar_run(
    "proposicoes-tramitacoes-2026",
    "Tramitações das proposições da Câmara (2026)",
    "https://example.org/arquivos/proposicoesTramitacoes/csv/proposicoesTramitacoes-2026.csv",
    datetime(2026, 11, 27, 12, 53, tzinfo=UTC),
)

com_tramitacao = CamaraProposition.objects.create(
    camara_id=14666,
    title="PL 11/2003",
    type_acronym="PL",
    number=11,
    year=2003,
    ementa="Proíbe a veiculação de peças publicitárias.",
    ingestion_run=run_proposicao,
)
sem_tramitacao = CamaraProposition.objects.create(
    camara_id=14667,
    title="PL 12/2003",
    type_acronym="PL",
    number=12,
    year=2003,
    ementa="Dispõe sobre a rotulagem de alimentos.",
    ingestion_run=run_proposicao,
)

# 2026-05-07 16:58 em Brasília = 19:58 UTC; 2026-05-08 09:00 em Brasília = 12:00 UTC.
PRIMEIRO_INSTANTE = datetime(2026, 5, 7, 19, 58, tzinfo=UTC)
SEGUNDO_INSTANTE = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
# Gravadas fora da ordem em que devem sair. A ordem é a do Python (ADR 0035, decisão 5): hora,
# `sequencia` (nula por último), órgão, descrição. As duas de `sequencia` 152 empatam na hora e na
# sequência e só se separam pelo órgão: "MESA" vem antes de "mesa" em Python (maiúscula primeiro),
# mas depois dela na collation `en_US` do PostgreSQL, então nem o índice único nem a ordem de
# gravação devolvem a ordem certa (sem isso, uma ordenação só por hora passou: o índice por
# acaso já entregava as linhas na ordem esperada).
for proposicao, sequencia, quando, orgao, descricao in [
    ("14666", 153, SEGUNDO_INSTANTE, "PLEN", "Despacho <b>negrito</b> da Mesa"),
    ("14666", None, PRIMEIRO_INSTANTE, "MESA", "Registro sem sequência na fonte"),
    ("14666", 152, PRIMEIRO_INSTANTE, "mesa", "Mesma hora e sequência, órgão em minúsculas"),
    ("14666", 152, PRIMEIRO_INSTANTE, "MESA", "Apresentação de Requerimento"),
    ("99999", 1, PRIMEIRO_INSTANTE, "MESA", "Tramitação de proposição desconhecida"),
]:
    CamaraPropositionStep.objects.create(
        camara_proposition_id=proposicao,
        sequence=sequencia,
        occurred_at=quando,
        organ_code=orgao,
        description=descricao,
        ingestion_run=run_tramitacao,
    )

CamaraVoting.objects.create(
    camara_voting_id="9000001-1",
    voted_on=date(2026, 5, 8),
    organ_acronym="PLEN",
    approval="1",
    total_yes=0,
    total_no=0,
    total_other=0,
    description="Votação sintética do CI.",
    proposition_id=14666,
    ingestion_run=run_votacao,
)
for proposicao in (com_tramitacao, sem_tramitacao):
    CamaraVotingProposition.objects.create(
        camara_voting_id="9000001-1",
        proposition=proposicao,
        origin="proposicoes",
        ingestion_run=run_proposicao,
    )

print("semente ok: 2 proposições, 5 tramitações, 1 votação")
