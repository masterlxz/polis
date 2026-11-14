"""API interna de leitura do perfil do deputado (ADR 0015, decisão 2; ADR 0021, decisão 4).

Não é a API pública do ADR 0013: não é contrato, não é documentada e só deve ser alcançável pela
rede privada do Compose. O que sai é montado campo a campo, numa lista explícita: campo novo em
`Deputy` nunca vaza sem alguém decidir (ADR 0005). `uri` e ids internos não estão na lista. Toda
resposta leva a atribuição da fonte (ADR 0008, decisão 3).

A Câmara não declara licença (ADR 0021): `licenca` sai com `id` e `url` nulos, sem inventar uma.
`coletado_em` é o início da última execução que viu o deputado.

`em_exercicio: false` significa só "não consta mais na lista de deputados em exercício da Câmara":
a lista não diz o motivo (licença, fim de mandato, renúncia, morte, suplente assumindo).
`saiu_da_lista_em` é o início da primeira coleta que não o trouxe (ADR 0027): a data da COLETA,
não a do fim do mandato.
"""

import re
from collections import Counter

from django.http import JsonResponse
from django.views.decorators.http import require_safe

from .models import Deputy, SenateVoting, Senator

VOTINGS_PER_PAGE = 50
# Só dígitos ASCII, de 1 a 4: `\d` aceitaria dígitos de outras escritas.
_PAGE_PATTERN = re.compile(r"[0-9]{1,4}")


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
                "em_exercicio": deputy.in_office,
                "saiu_da_lista_em": deputy.left_list_at.isoformat()
                if deputy.left_list_at
                else None,
            },
            "atribuicao": _attribution(deputy.ingestion_run),
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_safe
def senator_profile(request, senate_id):
    """Perfil do senador (ADR 0028): mesma semântica de `em_exercicio` e `saiu_da_lista_em`."""
    senator = (
        Senator.objects.filter(senate_id=senate_id)
        .select_related("ingestion_run__dataset__source")
        .first()
    )
    if senator is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)
    return JsonResponse(
        {
            "senador": {
                "id_senado": senator.senate_id,
                "nome": senator.name,
                "partido": _or_none(senator.party_acronym),
                "uf": senator.state,
                "em_exercicio": senator.in_office,
                "saiu_da_lista_em": senator.left_list_at.isoformat()
                if senator.left_list_at
                else None,
            },
            "atribuicao": _attribution(senator.ingestion_run),
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _votings_with_attribution():
    return SenateVoting.objects.select_related("ingestion_run__dataset__source")


@require_safe
def senate_voting_list(request):
    """Votações do Senado, mais recente primeiro, 50 por página (ADR 0030).

    Página além da última devolve a lista vazia (200), não 404: quem percorre as páginas num laço
    para ao ver a lista vazia. A atribuição é a da coleta mais recente entre as votações da página.
    """
    page_text = request.GET.get("pagina", "1")
    if not _PAGE_PATTERN.fullmatch(page_text) or int(page_text) == 0:
        return JsonResponse(
            {"erro": "página inválida"}, status=400, json_dumps_params={"ensure_ascii": False}
        )
    page = int(page_text)

    total = SenateVoting.objects.count()
    start = (page - 1) * VOTINGS_PER_PAGE
    votings = list(
        _votings_with_attribution().order_by("-voted_on", "-session_voting_code")[
            start : start + VOTINGS_PER_PAGE
        ]
    )
    newest_run = max((v.ingestion_run for v in votings), key=lambda r: r.started_at, default=None)
    return JsonResponse(
        {
            "votacoes": [
                {
                    "codigo": v.session_voting_code,
                    "data": v.voted_on.isoformat(),
                    "identificacao": v.identification,
                    "ementa": v.summary,
                    "resultado": v.result,
                    "secreta": v.secret,
                }
                for v in votings
            ],
            "pagina": page,
            "total_paginas": (total + VOTINGS_PER_PAGE - 1) // VOTINGS_PER_PAGE,
            "atribuicao": _attribution(newest_run) if newest_run else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_safe
def senate_voting_detail(request, code):
    """Uma votação do Senado com os votos (ADR 0029 e 0030).

    Na votação secreta a lista sai como `participacao`, nunca como `votos`: a sigla `Votou` diz que
    o senador votou, não como (ADR 0029, decisão 6). `contagem_por_sigla` é calculada pelo polis a
    partir dos itens; `totais_da_fonte` são os do Senado, como vieram (nulos nas abertas).
    """
    voting = _votings_with_attribution().filter(session_voting_code=code).first()
    if voting is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)

    votes = list(voting.votes.order_by("name", "senate_id"))
    # Junção por código na leitura (ADR 0029, decisão 5): quem votou e saiu da lista de exercício
    # pode não estar em `Senator`, e o link para o perfil só existe para quem está.
    with_profile = set(
        Senator.objects.filter(senate_id__in={v.senate_id for v in votes}).values_list(
            "senate_id", flat=True
        )
    )
    list_key = "participacao" if voting.secret else "votos"
    return JsonResponse(
        {
            "votacao": {
                "codigo": voting.session_voting_code,
                "data": voting.voted_on.isoformat(),
                "sigla": voting.type_acronym,
                "numero": voting.number,
                "ano": voting.year,
                "identificacao": voting.identification,
                "ementa": voting.summary,
                "resultado": voting.result,
                "secreta": voting.secret,
                "id_processo": voting.process_id,
                "codigo_materia": voting.matter_id,
                "totais_da_fonte": {
                    "sim": voting.total_yes,
                    "nao": voting.total_no,
                    "abstencao": voting.total_abstention,
                },
            },
            "contagem_por_sigla": dict(Counter(v.vote_code for v in votes).most_common()),
            list_key: [
                {
                    "id_senado": v.senate_id,
                    "nome": v.name,
                    "partido": _or_none(v.party_acronym),
                    "uf": v.state,
                    "sigla": v.vote_code,
                    "tem_perfil": v.senate_id in with_profile,
                }
                for v in votes
            ],
            "atribuicao": _attribution(voting.ingestion_run),
        },
        json_dumps_params={"ensure_ascii": False},
    )
