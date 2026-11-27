"""Enche o banco com o VOLUME medido das proposições, votações e tramitações da Câmara em 2026, para
a medição de carga ver os índices e as tabelas do tamanho real (ADR 0033 e 0034). Roda SÓ no CI,
depois de `.github/ci/semear_camara.py` (que cria as execuções de coleta e os piores casos):
`uv run python manage.py shell < scripts/carga_camara/semear_volume.py`.

Sintético: o que importa é o tamanho das tabelas e dos índices, não o conteúdo.
- proposições: 26.745 no total (as 215 do `semear_camara.py` mais as de enchimento, ids 100001+);
- votações: 9.153, com cerca de 46,8 mil ligações a proposições (5 por votação, 6 nas 811
  primeiras, mais as 215 do `semear_camara.py`; a fonte tem 46.576);
- tramitações: ~118,7 mil em 46.295 proposições, com média de 2,5 e mediana 2 (as 10 mil primeiras
  de enchimento existem como proposição; as outras 36.295 só têm tramitação, como na fonte, onde
  cerca de 36 mil das 46 mil proposições do arquivo não estão no conjunto das votações).
Termina com `ANALYZE` (sem estatísticas o planner escolhe plano de tabela vazia) e imprime as
contagens.
"""

from datetime import UTC, date, datetime, timedelta

from django.db import connection

from apps.legislature.models import (
    CamaraProposition,
    CamaraPropositionStep,
    CamaraVoting,
    CamaraVotingProposition,
)
from apps.sources.models import IngestionRun

run_votacao = IngestionRun.objects.filter(dataset__slug="votacoes-2026").latest("started_at")
run_proposicao = IngestionRun.objects.filter(dataset__slug="votacoes-proposicoes-2026").latest(
    "started_at"
)
run_tramitacao = IngestionRun.objects.filter(dataset__slug="proposicoes-tramitacoes-2026").latest(
    "started_at"
)

PROPOSICOES_TOTAIS = 26_745
VOTACOES_TOTAIS = 9_153
LIGACOES_TOTAIS = 46_576
PROPOSICOES_COM_TRAMITACAO = 46_295
COM_PROPOSICAO_CADASTRADA = 10_000
# Tramitações por proposição, em ciclo de 20: média 2,5 e mediana 2.
CICLO = [1] * 9 + [2] * 5 + [3] * 3 + [4, 6, 12]
ORGAOS = ["PLEN", "MESA", "CCJC", "CFT"]
LOTE = 5_000
BASE = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)

ja_existentes = CamaraProposition.objects.count()
novas = PROPOSICOES_TOTAIS - ja_existentes
CamaraProposition.objects.bulk_create(
    (
        CamaraProposition(
            camara_id=100_000 + i,
            title=f"PL {i}/2025",
            type_acronym="PL",
            number=i,
            year=2025,
            ementa=f"Ementa sintética de volume número {i}.",
            ingestion_run=run_proposicao,
        )
        for i in range(1, novas + 1)
    ),
    batch_size=LOTE,
)

ja_votacoes = CamaraVoting.objects.count()
CamaraVoting.objects.bulk_create(
    (
        CamaraVoting(
            camara_voting_id=f"{8_000_000 + j}-1",
            voted_on=date(2026, 2, 1) + timedelta(days=j % 300),
            organ_acronym="PLEN",
            approval="1",
            total_yes=0,
            total_no=0,
            total_other=0,
            description=f"Votação sintética de volume {j}.",
            proposition_id=100_001 + (j % novas),
            ingestion_run=run_votacao,
        )
        for j in range(VOTACOES_TOTAIS - ja_votacoes)
    ),
    batch_size=LOTE,
)

ids_das_novas = list(
    CamaraProposition.objects.filter(camara_id__gt=100_000).values_list("id", flat=True)
)
CamaraVotingProposition.objects.bulk_create(
    (
        CamaraVotingProposition(
            camara_voting_id=f"{8_000_000 + j}-1",
            proposition_id=ids_das_novas[(j * 5 + t) % len(ids_das_novas)],
            origin="proposicoes",
            ingestion_run=run_proposicao,
        )
        for j in range(VOTACOES_TOTAIS - ja_votacoes)
        for t in range(6 if j < 811 else 5)
    ),
    batch_size=LOTE,
)


def passos():
    ids = [100_000 + i for i in range(1, COM_PROPOSICAO_CADASTRADA + 1)]
    ids += [
        300_000 + i for i in range(1, PROPOSICOES_COM_TRAMITACAO - COM_PROPOSICAO_CADASTRADA + 1)
    ]
    for k, proposicao in enumerate(ids):
        for sequencia in range(1, CICLO[k % len(CICLO)] + 1):
            yield CamaraPropositionStep(
                camara_proposition_id=str(proposicao),
                sequence=sequencia,
                occurred_at=BASE + timedelta(hours=sequencia + k % 1000),
                organ_code=ORGAOS[(k + sequencia) % len(ORGAOS)],
                description=f"Tramitação sintética {sequencia}",
                ingestion_run=run_tramitacao,
            )


CamaraPropositionStep.objects.bulk_create(passos(), batch_size=LOTE)

with connection.cursor() as cursor:
    cursor.execute("ANALYZE")

print(
    "volume ok:",
    f"{CamaraProposition.objects.count()} proposições,",
    f"{CamaraVoting.objects.count()} votações,",
    f"{CamaraVotingProposition.objects.count()} ligações,",
    f"{CamaraPropositionStep.objects.count()} tramitações",
)
