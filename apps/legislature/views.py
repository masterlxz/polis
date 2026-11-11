"""API interna de leitura do perfil do deputado (ADR 0015, decisão 2; ADR 0021, decisão 4).

Não é a API pública do ADR 0013: não é contrato, não é documentada e só deve ser alcançável pela
rede privada do Compose. O que sai é montado campo a campo, numa lista explícita: campo novo em
`Deputy` nunca vaza sem alguém decidir (ADR 0005). `uri` e ids internos não estão na lista. Toda
resposta leva a atribuição da fonte (ADR 0008, decisão 3).

A Câmara não declara licença (ADR 0021): `licenca` sai com `id` e `url` nulos, sem inventar uma.
`coletado_em` é o início da última execução que viu o deputado.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_safe

from .models import Deputy


def _or_none(value):
    return value or None


def _attribution(run):
    dataset = run.dataset
    return {
        "fonte": dataset.source.name,
        "conjunto": dataset.name,
        "coletado_em": run.started_at.isoformat(),
        "url_origem": run.source_url,
        "licenca": {"id": _or_none(dataset.license_id), "url": _or_none(dataset.license_url)},
    }


@require_safe
def deputy_profile(request, legislature, camara_id):
    deputy = (
        Deputy.objects.filter(legislature_id=legislature, camara_id=camara_id)
        .select_related("ingestion_run__dataset__source")
        .first()
    )
    if deputy is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)
    return JsonResponse(
        {
            "deputado": {
                "legislatura": deputy.legislature_id,
                "id_camara": deputy.camara_id,
                "nome": deputy.name,
                "partido": _or_none(deputy.party_acronym),
                "uf": deputy.state,
            },
            "atribuicao": _attribution(deputy.ingestion_run),
        },
        json_dumps_params={"ensure_ascii": False},
    )
