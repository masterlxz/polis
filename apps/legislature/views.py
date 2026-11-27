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
import unicodedata
from collections import Counter
from zoneinfo import ZoneInfo

from django.db.models import Count, Exists, OuterRef
from django.http import JsonResponse
from django.views.decorators.http import require_safe

from .models import (
    CamaraProposition,
    CamaraPropositionStep,
    CamaraVote,
    CamaraVoting,
    CamaraVotingProposition,
    Deputy,
    SenateVote,
    SenateVoting,
    Senator,
)

VOTINGS_PER_PAGE = 50
# Ordem das proposições do detalhe: primeiro as do arquivo `votacoesProposicoes`, depois as de
# `votacoesObjetos` (a ordem dos arquivos no catálogo; o significado de cada um não foi verificado,
# ADR 0033). Feita em Python: o banco ordenaria o texto de `origin` pela collation.
_PROPOSITION_ORIGIN_ORDER = ("proposicoes", "objetos")
# A fonte das tramitações não declara o fuso (ADR 0034, decisão 7): Brasília é o palpite, e a API
# diz a hora com o deslocamento (`-03:00`). Maior id que o banco guarda (`PositiveIntegerField`).
_BRASILIA = ZoneInfo("America/Sao_Paulo")
_INT32_MAX = 2**31 - 1
# Só a forma canônica, de 1 a 9999: sem zero à esquerda (nem `0`) e só dígitos ASCII (`\d`
# aceitaria dígitos de outras escritas). Mesma regra das rotas (`[1-9][0-9]{0,N}`).
_PAGE_PATTERN = re.compile(r"[1-9][0-9]{0,3}")


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
    if not _PAGE_PATTERN.fullmatch(page_text):
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


@require_safe
def senator_votes(request, senate_id):
    """Histórico de votos de um senador, mais recente primeiro, 50 por página (ADR 0030, emenda 7).

    Cada item é uma votação com o voto dele. Na votação secreta a sigla sai como `participacao` e
    a chave `voto` não existe; na aberta sai `voto` e não existe `participacao` (decisão 2 do ADR
    0030, por item). Partido e UF são os do momento do voto, não os do perfil. Senador fora de
    `Senator` dá 404, como o perfil, mesmo que tenha votado.
    """
    page_text = request.GET.get("pagina", "1")
    if not _PAGE_PATTERN.fullmatch(page_text):
        return JsonResponse(
            {"erro": "página inválida"}, status=400, json_dumps_params={"ensure_ascii": False}
        )
    page = int(page_text)

    senator = Senator.objects.filter(senate_id=senate_id).first()
    if senator is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)

    votes_of_senator = SenateVote.objects.filter(senate_id=senate_id)
    total = votes_of_senator.count()
    start = (page - 1) * VOTINGS_PER_PAGE
    votes = list(
        votes_of_senator.select_related("voting__ingestion_run__dataset__source").order_by(
            "-voting__voted_on", "-voting__session_voting_code"
        )[start : start + VOTINGS_PER_PAGE]
    )
    newest_run = max(
        (v.voting.ingestion_run for v in votes), key=lambda r: r.started_at, default=None
    )
    return JsonResponse(
        {
            "senador": {"id_senado": senator.senate_id, "nome": senator.name},
            "votos": [_senator_vote_item(v) for v in votes],
            "pagina": page,
            "total_paginas": (total + VOTINGS_PER_PAGE - 1) // VOTINGS_PER_PAGE,
            "atribuicao": _attribution(newest_run) if newest_run else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _senator_vote_item(vote):
    voting = vote.voting
    item = {
        "codigo": voting.session_voting_code,
        "data": voting.voted_on.isoformat(),
        "identificacao": voting.identification,
        "ementa": voting.summary,
        "resultado": voting.result,
        "secreta": voting.secret,
        "partido": _or_none(vote.party_acronym),
        "uf": vote.state,
    }
    item["participacao" if voting.secret else "voto"] = vote.vote_code
    return item


def _camara_voting_fields(voting):
    """Campos da votação da Câmara que a lista e o detalhe têm em comum (ADR 0032)."""
    return {
        "id": voting.camara_voting_id,
        "data": voting.voted_on.isoformat(),
        "orgao": voting.organ_acronym,
        "aprovacao": _or_none(voting.approval),
        "totais_da_fonte": {
            "sim": voting.total_yes,
            "nao": voting.total_no,
            "outros": voting.total_other,
        },
        "descricao": voting.description,
        "id_proposicao": voting.proposition_id,
    }


@require_safe
def camara_voting_list(request):
    """Votações da Câmara, mais recente primeiro, 50 por página (ADR 0032).

    Mesmas regras de página do Senado (ADR 0030, decisão 4). `tem_votos_nominais` vem de um
    `EXISTS` na própria consulta da página: só 1,9% das votações têm voto nominal (ADR 0031), e as
    outras só têm os totais da fonte. A ordem é determinística: o id da votação é único (mas é
    ordenado como texto, não como número).
    """
    page_text = request.GET.get("pagina", "1")
    if not _PAGE_PATTERN.fullmatch(page_text):
        return JsonResponse(
            {"erro": "página inválida"}, status=400, json_dumps_params={"ensure_ascii": False}
        )
    page = int(page_text)

    total = CamaraVoting.objects.count()
    start = (page - 1) * VOTINGS_PER_PAGE
    votings = list(
        CamaraVoting.objects.select_related("ingestion_run__dataset__source")
        .annotate(has_votes=Exists(CamaraVote.objects.filter(voting=OuterRef("pk"))))
        .order_by("-voted_on", "-camara_voting_id")[start : start + VOTINGS_PER_PAGE]
    )
    newest_run = max((v.ingestion_run for v in votings), key=lambda r: r.started_at, default=None)
    return JsonResponse(
        {
            "votacoes": [
                {**_camara_voting_fields(v), "tem_votos_nominais": v.has_votes} for v in votings
            ],
            "pagina": page,
            "total_paginas": (total + VOTINGS_PER_PAGE - 1) // VOTINGS_PER_PAGE,
            "atribuicao": _attribution(newest_run) if newest_run else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _deputy_names_by_pair(pairs):
    """Nome do `Deputy` de cada par (legislatura, id da Câmara) de `pairs` que tem perfil.

    Uma consulta só para todos os pares: filtra pelas legislaturas e pelos ids (o produto cartesiano
    pode trazer pares que ninguém votou) e confere o par em Python. Só o par inteiro casa: o mesmo
    id da Câmara em outra legislatura é outro deputado.
    """
    if not pairs:
        return {}
    rows = Deputy.objects.filter(
        legislature_id__in={legislature for legislature, _ in pairs},
        camara_id__in={camara_id for _, camara_id in pairs},
    ).values_list("legislature_id", "camara_id", "name")
    return {
        (legislature, camara_id): name
        for legislature, camara_id, name in rows
        if (legislature, camara_id) in pairs
    }


def _vote_count_order(item):
    vote, quantity = item
    return (-quantity, vote is None, vote or "")


def _alphabetical_key(name):
    """Chave de ordem alfabética de um nome: sem acento e sem diferença de caixa; sem nome, no fim.

    Comparar o texto cru poria "Átila" e "Érika" depois de "Zeca" (o acento vale mais que o Z). A
    ordem não depende da collation do banco, que o ADR 0032 já registra como variável. O desempate
    (legislatura e id) vem de quem chama, na mesma chave; o banco não ordena nada.
    """
    if name is None:
        return (True, "")
    decomposed = unicodedata.normalize("NFKD", name)
    return (False, "".join(c for c in decomposed if not unicodedata.combining(c)).casefold())


def _camara_proposition_order(link):
    origin = link.origin
    rank = (
        _PROPOSITION_ORIGIN_ORDER.index(origin)
        if origin in _PROPOSITION_ORIGIN_ORDER
        else len(_PROPOSITION_ORIGIN_ORDER)
    )
    return (rank, link.proposition.camara_id)


def _camara_proposition_fields(proposition):
    """Os campos da proposição que a API mostra, um a um (ADR 0033): sem `uri` nem id interno."""
    return {
        "id_camara": proposition.camara_id,
        "titulo": proposition.title,
        "tipo": proposition.type_acronym,
        "numero": proposition.number,
        "ano": proposition.year,
        "ementa": _or_none(proposition.ementa),
    }


def _camara_proposition_item(link, step_totals):
    """Uma proposição da votação (ADR 0033), com quantas tramitações de 2026 ela tem (ADR 0035)."""
    proposition = link.proposition
    return {
        **_camara_proposition_fields(proposition),
        "origem": link.origin,
        "total_tramitacoes": step_totals.get(str(proposition.camara_id), 0),
    }


def _step_totals(proposition_ids):
    """Tramitações por id de proposição, numa consulta só (ADR 0035, decisão 8).

    A tramitação guarda o id em TEXTO e sem chave para a proposição (ADR 0034): a junção é aqui, e
    `IN` compara o texto inteiro, nunca um prefixo. Sem proposição na votação, nenhuma consulta.
    """
    ids = [str(proposition_id) for proposition_id in proposition_ids]
    if not ids:
        return {}
    rows = (
        CamaraPropositionStep.objects.filter(camara_proposition_id__in=ids)
        .values("camara_proposition_id")
        .annotate(total=Count("id"))
        .order_by()
    )
    return {row["camara_proposition_id"]: row["total"] for row in rows}


@require_safe
def camara_voting_detail(request, voting_id):
    """Uma votação da Câmara com os votos nominais, se houver (ADR 0031 e 0032).

    `voto` vazio é "sem posição registrada": sai `null`, nunca string vazia nem chave ausente.
    `nome` só sai para quem tem `Deputy` (junção por legislatura e id na leitura; o voto não guarda
    nome, ADR 0005). `contagem_por_voto` é calculada pelo polis a partir dos itens, separada de
    `totais_da_fonte`, que ficam como a fonte os mandou (0/0/0 numa votação sem voto nominal não é
    uma contagem: a fonte não informou). `atribuicao` é a do conjunto de votações e
    `atribuicao_dos_votos` a do conjunto de votos (nula se não há votos). Os votos saem em ordem
    alfabética de nome (sem acento nem caixa), quem não tem perfil por último, e o empate fica por
    legislatura e id (ADR 0032, emenda 4). `proposicoes` são TODAS as da votação (até 213 medidas),
    por origem e depois por id numérico, com `ano` e `ementa` vazios como `null`;
    `atribuicao_das_proposicoes` é a da coleta mais recente entre elas, nula se não há (emenda 5).
    """
    voting = (
        CamaraVoting.objects.select_related("ingestion_run__dataset__source")
        .filter(camara_voting_id=voting_id)
        .first()
    )
    if voting is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)

    votes = list(voting.votes.select_related("ingestion_run__dataset__source"))
    names = _deputy_names_by_pair({(v.legislature_id, v.camara_id) for v in votes})
    votes.sort(
        key=lambda v: (
            _alphabetical_key(names.get((v.legislature_id, v.camara_id))),
            v.legislature_id,
            v.camara_id,
        )
    )
    counts = Counter(_or_none(v.vote) for v in votes)
    # Os votos vêm de outro conjunto (`camara/votos-2026`) que a votação (`camara/votacoes-2026`):
    # a fonte dos votos é citada à parte, pela coleta mais recente entre eles (ADR 0008, decisão 3).
    newest_votes_run = max(
        (v.ingestion_run for v in votes), key=lambda r: r.started_at, default=None
    )
    # As proposições vêm de mais dois conjuntos; a ligação guarda o id da votação em texto, sem
    # chave (ADR 0033), e a atribuição é a da coleta mais recente entre elas.
    links = sorted(
        CamaraVotingProposition.objects.filter(
            camara_voting_id=voting.camara_voting_id
        ).select_related("proposition", "ingestion_run__dataset__source"),
        key=_camara_proposition_order,
    )
    newest_propositions_run = max(
        (link.ingestion_run for link in links), key=_started, default=None
    )
    step_totals = _step_totals(link.proposition.camara_id for link in links)
    return JsonResponse(
        {
            "votacao": _camara_voting_fields(voting),
            "votos": [
                {
                    "legislatura": v.legislature_id,
                    "id_camara": v.camara_id,
                    "partido": _or_none(v.party_acronym),
                    "voto": _or_none(v.vote),
                    "tem_perfil": (v.legislature_id, v.camara_id) in names,
                    "nome": names.get((v.legislature_id, v.camara_id)),
                }
                for v in votes
            ],
            "contagem_por_voto": [
                {"voto": vote, "quantidade": quantity}
                for vote, quantity in sorted(counts.items(), key=_vote_count_order)
            ],
            "proposicoes": [_camara_proposition_item(link, step_totals) for link in links],
            "atribuicao": _attribution(voting.ingestion_run),
            "atribuicao_dos_votos": _attribution(newest_votes_run) if newest_votes_run else None,
            "atribuicao_das_proposicoes": (
                _attribution(newest_propositions_run) if newest_propositions_run else None
            ),
        },
        json_dumps_params={"ensure_ascii": False},
    )


@require_safe
def deputy_votes(request, legislature, camara_id):
    """Histórico de votos de um deputado da Câmara, mais recente primeiro, 50 por página.

    O inverso de `camara_voting_detail`: cada item é uma votação com o voto dele. Mesmas regras de
    página do Senado (ADR 0030, decisão 4) e a mesma ordem da lista da Câmara (ADR 0032). O voto
    não tem chave para `Deputy` (ADR 0031): o histórico é o das linhas com o par (legislatura, id
    da Câmara), e deputado sem `Deputy` para o par dá 404, como o perfil, mesmo que tenha votado.
    `voto` vazio sai `null` e `partido` é o do momento do voto. Duas atribuições, como o detalhe da
    votação (ADR 0008, decisão 3; ADR 0032, emenda 2): `atribuicao_dos_votos` é a da coleta de
    VOTOS mais recente entre os itens da página e `atribuicao_das_votacoes` a da coleta de
    VOTAÇÕES mais recente entre as votações da página (de onde vêm data, órgão, descrição e
    aprovação). Ambas são nulas numa página sem votos. O nome do deputado vem de outro conjunto,
    citado no perfil.
    """
    page_text = request.GET.get("pagina", "1")
    if not _PAGE_PATTERN.fullmatch(page_text):
        return JsonResponse(
            {"erro": "página inválida"}, status=400, json_dumps_params={"ensure_ascii": False}
        )
    page = int(page_text)

    deputy = Deputy.objects.filter(legislature_id=legislature, camara_id=camara_id).first()
    if deputy is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)

    votes_of_deputy = CamaraVote.objects.filter(legislature_id=legislature, camara_id=camara_id)
    total = votes_of_deputy.count()
    start = (page - 1) * VOTINGS_PER_PAGE
    newest_first = votes_of_deputy.select_related(
        "ingestion_run__dataset__source", "voting__ingestion_run__dataset__source"
    ).order_by("-voting__voted_on", "-voting__camara_voting_id")
    votes = list(newest_first[start : start + VOTINGS_PER_PAGE])
    newest_votes_run = max((v.ingestion_run for v in votes), key=_started, default=None)
    newest_votings_run = max((v.voting.ingestion_run for v in votes), key=_started, default=None)
    return JsonResponse(
        {
            "deputado": {
                "legislatura": deputy.legislature_id,
                "id_camara": deputy.camara_id,
                "nome": deputy.name,
            },
            "votos": [_deputy_vote_item(v) for v in votes],
            "pagina": page,
            "total_paginas": (total + VOTINGS_PER_PAGE - 1) // VOTINGS_PER_PAGE,
            "atribuicao_das_votacoes": (
                _attribution(newest_votings_run) if newest_votings_run else None
            ),
            "atribuicao_dos_votos": _attribution(newest_votes_run) if newest_votes_run else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _started(run):
    return run.started_at


def _camara_step_order(step):
    """Hora, depois `sequencia` (nula por último), órgão e descrição: tudo em Python, para não
    depender da collation do banco (ADR 0035, decisão 5)."""
    return (
        step.occurred_at,
        step.sequence or 0,
        step.organ_code,
        step.description,
    )


def _camara_step_item(step):
    return {
        "sequencia": step.sequence,
        "data_hora": step.occurred_at.astimezone(_BRASILIA).isoformat(),
        "orgao": step.organ_code,
        "descricao": step.description,
    }


@require_safe
def camara_proposition_detail(request, proposition_id):
    """Uma proposição da Câmara com as tramitações de 2026 (ADR 0035).

    404 se o polis não conhece a proposição, mesmo havendo tramitações: a tramitação não tem chave
    para ela (ADR 0034) e a rota é quem decide o que existe. Proposição conhecida sem tramitação é
    200 com `tramitacoes: []` e `atribuicao_das_tramitacoes: null`. `data_hora` sai com `-03:00`.
    São todas as tramitações (até 98 medidas), sem paginação; duas consultas no 200.
    """
    camara_id = int(proposition_id)
    if camara_id > _INT32_MAX:
        return JsonResponse({"erro": "não encontrado"}, status=404)
    proposition = (
        CamaraProposition.objects.select_related("ingestion_run__dataset__source")
        .filter(camara_id=camara_id)
        .first()
    )
    if proposition is None:
        return JsonResponse({"erro": "não encontrado"}, status=404)

    steps = sorted(
        CamaraPropositionStep.objects.filter(camara_proposition_id=str(camara_id)).select_related(
            "ingestion_run__dataset__source"
        ),
        key=_camara_step_order,
    )
    newest_run = max((step.ingestion_run for step in steps), key=_started, default=None)
    return JsonResponse(
        {
            "proposicao": _camara_proposition_fields(proposition),
            "tramitacoes": [_camara_step_item(step) for step in steps],
            "atribuicao_da_proposicao": _attribution(proposition.ingestion_run),
            "atribuicao_das_tramitacoes": _attribution(newest_run) if newest_run else None,
        },
        json_dumps_params={"ensure_ascii": False},
    )


def _deputy_vote_item(vote):
    voting = vote.voting
    return {
        "id": voting.camara_voting_id,
        "data": voting.voted_on.isoformat(),
        "orgao": voting.organ_acronym,
        "descricao": voting.description,
        "aprovacao": _or_none(voting.approval),
        "id_proposicao": voting.proposition_id,
        "partido": _or_none(vote.party_acronym),
        "voto": _or_none(vote.vote),
    }
