"""API interna de leitura do perfil da pessoa (ADR 0015, decisão 2; ADR 0009, fatia 3).

Não é a API pública do ADR 0013: não é contrato, não é documentada e só deve ser alcançável pela
rede privada do Compose. O que sai é montado campo a campo, numa lista explícita: campo novo
em um modelo nunca vaza sem alguém decidir (ADR 0005). O nome social e os ids internos não
estão na lista. Toda candidatura leva a atribuição da fonte (ADR 0008, decisão 3).
"""

from django.http import JsonResponse
from django.views.decorators.http import require_safe

from .models import Person
from .search import buscar


def _or_none(value):
    return value or None


def _attribution(candidacy):
    run = candidacy.ingestion_run
    dataset = run.dataset
    return {
        "fonte": dataset.source.name,
        "conjunto": dataset.name,
        "coletado_em": run.started_at.isoformat(),
        "gerado_pela_fonte_em": candidacy.source_generated_at.isoformat(),
        "url_origem": run.source_url,
        "licenca": {"id": dataset.license_id, "url": _or_none(dataset.license_url)},
    }


def _candidacy(candidacy):
    election = candidacy.election
    federation = None
    if candidacy.federation_acronym or candidacy.federation_name:
        federation = {"sigla": candidacy.federation_acronym, "nome": candidacy.federation_name}
    coalition = None
    if candidacy.coalition_name or candidacy.coalition_composition:
        coalition = {
            "nome": candidacy.coalition_name,
            "composicao": candidacy.coalition_composition,
        }
    return {
        "eleicao": {
            "codigo": election.tse_code,
            "turno": election.round,
            "ano": election.year,
            "descricao": election.description,
            "data": election.date.isoformat(),
        },
        "cargo": candidacy.office_name,
        "abrangencia": candidacy.scope,
        "uf": candidacy.state,
        "unidade_eleitoral": {
            "codigo": candidacy.electoral_unit_code,
            "nome": candidacy.electoral_unit_name,
        },
        "numero_urna": candidacy.ballot_number,
        "partido": {
            "numero": candidacy.party_number,
            "sigla": candidacy.party_acronym,
            "nome": candidacy.party_name,
        },
        "federacao": federation,
        "coligacao": coalition,
        "situacao": _or_none(candidacy.status_name),
        "resultado": _or_none(candidacy.result_name),
        "atribuicao": _attribution(candidacy),
    }


@require_safe
def person_search(request):
    return JsonResponse(
        {"resultados": buscar(request.GET.get("q", ""))},
        json_dumps_params={"ensure_ascii": False},
    )


@require_safe
def person_profile(request, cycle, candidate_id):
    person = Person.objects.filter(cycle_year=cycle, tse_candidate_id=candidate_id).first()
    if person is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)
    candidacies = person.candidacies.select_related(
        "election", "ingestion_run__dataset__source"
    ).order_by("election__round", "election__tse_code")
    return JsonResponse(
        {
            "pessoa": {
                "ciclo": person.cycle_year,
                "id_tse": person.tse_candidate_id,
                "nome": person.public_name,
            },
            "candidaturas": [_candidacy(candidacy) for candidacy in candidacies],
        },
        json_dumps_params={"ensure_ascii": False},
    )
