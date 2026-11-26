"""API interna das votações da Câmara (ADR 0031; formato no ADR 0032).

`GET /internal/v1/camara/votacoes/` (lista paginada) e `GET /internal/v1/camara/votacoes/<id>/`
(detalhe com os votos). Dados sintéticos. O que mais importa: o id da votação é TEXTO (`2641546-7`)
e a rota o recusa sem consultar o banco; `voto` vazio sai `null` (é "sem posição", nunca string
vazia nem chave ausente); só 1,9% das votações têm voto nominal, e a lista diz quais; o nome do
deputado vem de `Deputy`, pela junção (legislatura, id da Câmara) na leitura, e só para quem tem
perfil. Só saem campos de listas explícitas, com a atribuição da fonte. Os testes de 404, 400 e 405
pedem antes um 200 de controle: sem isso, uma rota que não existe passaria por "erro esperado".

Valores de referência lidos do código: 50 por página (`VOTINGS_PER_PAGE` em `apps/legislature/
views.py`) e `varchar(20)` do `camara_voting_id` (`CamaraVoting` em `apps/legislature/models.py`).
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from apps.legislature.models import (
    CamaraProposition,
    CamaraVote,
    CamaraVoting,
    CamaraVotingProposition,
    Deputy,
)
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LISTA = "/internal/v1/camara/votacoes/"
NOMINAL = "2641546-7"
SEM_VOTOS = "2641546-8"
LEGISLATURA = 57
COLETADO_EM = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
URL_ORIGEM = "https://example.org/arquivos/votacoes/csv/votacoes-2026.csv"
URL_ORIGEM_DOS_VOTOS = "https://example.org/arquivos/votacoesVotos/csv/votacoesVotos-2026.csv"
COLETADO_EM_DOS_VOTOS = datetime(2026, 11, 24, 15, 30, tzinfo=UTC)

CHAVES_LISTA = {"votacoes", "pagina", "total_paginas", "atribuicao"}
CHAVES_ITEM_DA_LISTA = {
    "id",
    "data",
    "orgao",
    "aprovacao",
    "totais_da_fonte",
    "descricao",
    "id_proposicao",
    "tem_votos_nominais",
}
CHAVES_DETALHE = {
    "votacao",
    "votos",
    "contagem_por_voto",
    "proposicoes",
    "atribuicao",
    "atribuicao_dos_votos",
    "atribuicao_das_proposicoes",
}
CHAVES_PROPOSICAO = {"id_camara", "titulo", "tipo", "numero", "ano", "ementa", "origem"}
CHAVES_VOTACAO = CHAVES_ITEM_DA_LISTA - {"tem_votos_nominais"}
CHAVES_TOTAIS = {"sim", "nao", "outros"}
CHAVES_VOTO = {"legislatura", "id_camara", "partido", "voto", "tem_perfil", "nome"}
CHAVES_CONTAGEM = {"voto", "quantidade"}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}


def _criar_run(
    started_at=COLETADO_EM,
    slug="votacoes-2026",
    nome="Votações da Câmara em 2026",
    url=URL_ORIGEM,
):
    source, _ = Source.objects.get_or_create(
        slug="camara",
        defaults={
            "name": "Câmara dos Deputados: Dados Abertos",
            "institution": "Câmara dos Deputados",
            "official_url": "https://example.org",
            "access_type": Source.AccessType.FILE,
        },
    )
    dataset, _ = Dataset.objects.get_or_create(
        source=source,
        slug=slug,
        defaults={
            "name": nome,
            "url": url,
            "format": Dataset.Format.CSV,
            "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
            "license_justification": "Decisão do dono de teste.",
        },
    )
    return IngestionRun.objects.create(
        dataset=dataset, source_url=dataset.url, started_at=started_at
    )


def _criar_run_dos_votos(started_at=COLETADO_EM_DOS_VOTOS):
    """Execução do conjunto de votos (`camara/votos-2026`), outro `Dataset` que o das votações."""
    return _criar_run(
        started_at,
        slug="votos-2026",
        nome="Votos da Câmara em 2026",
        url=URL_ORIGEM_DOS_VOTOS,
    )


@pytest.fixture
def run():
    return _criar_run()


def _votacao(run, codigo, **extra):
    campos = {
        "camara_voting_id": codigo,
        "voted_on": date(2026, 3, 10),
        "organ_acronym": "PLEN",
        "approval": "1",
        "total_yes": 300,
        "total_no": 150,
        "total_other": 2,
        "description": "Aprovada a Emenda nº 1.",
        "proposition_id": 2651254,
        "ingestion_run": run,
        **extra,
    }
    return CamaraVoting.objects.create(**campos)


def _voto(votacao, camara_id, texto, legislatura=LEGISLATURA, **extra):
    campos = {
        "voting": votacao,
        "camara_id": camara_id,
        "legislature_id": legislatura,
        "party_acronym": "XYZ",
        "vote": texto,
        "ingestion_run": votacao.ingestion_run,
        **extra,
    }
    return CamaraVote.objects.create(**campos)


def _deputado(run, camara_id, legislatura=LEGISLATURA, **extra):
    campos = {
        "legislature_id": legislatura,
        "camara_id": camara_id,
        "name": f"Deputado {legislatura}-{camara_id}",
        "party_acronym": "XYZ",
        "state": "SP",
        "ingestion_run": run,
        **extra,
    }
    return Deputy.objects.create(**campos)


@pytest.fixture
def nominal(run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 3, "Não")
    _voto(votacao, 1, "Sim")
    _voto(votacao, 4, "Abstenção")
    _voto(votacao, 2, "Sim")
    return votacao


@pytest.fixture
def sem_votos(run):
    return _votacao(run, SEM_VOTOS, voted_on=date(2026, 3, 11))


def _ok(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def _detalhe(client, codigo):
    return _ok(client, f"{LISTA}{codigo}/")


def _todas_as_chaves(valor):
    if isinstance(valor, dict):
        for chave, filho in valor.items():
            yield chave
            yield from _todas_as_chaves(filho)
    elif isinstance(valor, list):
        for filho in valor:
            yield from _todas_as_chaves(filho)


# --- Detalhe -------------------------------------------------------------------------------------


def test_detalhe_so_com_as_chaves_das_listas_explicitas(client, nominal):
    corpo = _detalhe(client, NOMINAL)

    assert set(corpo) == CHAVES_DETALHE
    assert set(corpo["votacao"]) == CHAVES_VOTACAO
    assert set(corpo["votacao"]["totais_da_fonte"]) == CHAVES_TOTAIS
    assert all(set(item) == CHAVES_VOTO for item in corpo["votos"])
    assert all(set(item) == CHAVES_CONTAGEM for item in corpo["contagem_por_voto"])
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO
    assert set(corpo["atribuicao_dos_votos"]) == CHAVES_ATRIBUICAO


def test_votacao_com_os_campos_da_fonte(client, nominal):
    assert _detalhe(client, NOMINAL)["votacao"] == {
        "id": NOMINAL,
        "data": "2026-03-10",
        "orgao": "PLEN",
        "aprovacao": "1",
        "totais_da_fonte": {"sim": 300, "nao": 150, "outros": 2},
        "descricao": "Aprovada a Emenda nº 1.",
        "id_proposicao": 2651254,
    }


def test_aprovacao_vazia_sai_null_e_zeros_saem_como_vem(client, run):
    _votacao(run, "10-1", approval="")
    _votacao(run, "10-2", approval="0", total_yes=0, total_no=0, total_other=0, proposition_id=0)

    vazia = _detalhe(client, "10-1")["votacao"]
    zero = _detalhe(client, "10-2")["votacao"]

    assert vazia["aprovacao"] is None
    assert zero["aprovacao"] == "0"
    # 0/0/0 numa votação sem voto nominal NÃO é uma contagem (a fonte não informou; ADR 0031) e o
    # `0` da proposição é "sem proposição": a API não interpreta, devolve como vêm (ADR 0032)
    assert zero["totais_da_fonte"] == {"sim": 0, "nao": 0, "outros": 0}
    assert zero["id_proposicao"] == 0


def test_votos_saem_ordenados_por_legislatura_e_id_da_camara(client, run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 5, "Sim")
    _voto(votacao, 9, "Sim", legislatura=56)
    _voto(votacao, 2, "Não")

    votos = _detalhe(client, NOMINAL)["votos"]

    assert [(v["legislatura"], v["id_camara"]) for v in votos] == [(56, 9), (57, 2), (57, 5)]
    assert votos[1] == {
        "legislatura": 57,
        "id_camara": 2,
        "partido": "XYZ",
        "voto": "Não",
        "tem_perfil": False,
        "nome": None,
    }


def _nomes_na_ordem(corpo):
    return [v["nome"] for v in corpo["votos"]]


def test_votos_de_quem_tem_perfil_saem_em_ordem_alfabetica_de_nome(client, run):
    votacao = _votacao(run, NOMINAL)
    for camara_id, nome in ((1, "Carla"), (2, "Ana"), (3, "Bia")):
        _deputado(run, camara_id, name=nome)
        _voto(votacao, camara_id, "Sim")

    assert _nomes_na_ordem(_detalhe(client, NOMINAL)) == ["Ana", "Bia", "Carla"]


def test_ordem_de_nome_ignora_acento_e_caixa(client, run):
    votacao = _votacao(run, NOMINAL)
    for camara_id, nome in ((1, "Zeca"), (2, "Átila Lins"), (3, "bruno"), (4, "Érika")):
        _deputado(run, camara_id, name=nome)
        _voto(votacao, camara_id, "Sim")

    # Comparar o texto cru poria "Átila" e "Érika" depois de "Zeca" (o acento vale mais que o Z).
    assert _nomes_na_ordem(_detalhe(client, NOMINAL)) == ["Átila Lins", "bruno", "Érika", "Zeca"]


def test_acento_dentro_do_nome_nao_desloca_a_ordem(client, run):
    votacao = _votacao(run, NOMINAL)
    for camara_id, nome in ((1, "Alzira"), (2, "Álvaro"), (3, "Alberto")):
        _deputado(run, camara_id, name=nome)
        _voto(votacao, camara_id, "Sim")

    # O acento fica no meio do nome: "Álvaro" tem de cair entre "Alberto" e "Alzira", como "Alvaro".
    assert _nomes_na_ordem(_detalhe(client, NOMINAL)) == ["Alberto", "Álvaro", "Alzira"]


def test_quem_nao_tem_perfil_vem_depois_de_quem_tem_nome_por_legislatura_e_id(client, run):
    votacao = _votacao(run, NOMINAL)
    _deputado(run, 2, name="Zeca")
    for camara_id, legislatura in ((3, 57), (2, 57), (1, 57), (9, 56)):
        _voto(votacao, camara_id, "Sim", legislatura=legislatura)

    votos = _detalhe(client, NOMINAL)["votos"]

    pares = [(v["legislatura"], v["id_camara"]) for v in votos]
    assert pares == [(57, 2), (56, 9), (57, 1), (57, 3)]
    assert [v["tem_perfil"] for v in votos] == [True, False, False, False]


def test_mesmo_nome_desempata_por_legislatura_e_id_mesmo_gravado_fora_de_ordem(client, run):
    votacao = _votacao(run, NOMINAL)
    _deputado(run, 2, name="Ana", legislatura=57)
    _deputado(run, 9, name="Ana", legislatura=56)
    _deputado(run, 1, name="Zeca", legislatura=57)
    # Sem ordenar, o banco devolve os votos na ordem da gravação ou na inversa (visto no CI): com a
    # 56 gravada antes da 57, uma das duas põe os dois "Ana" trocados se o desempate faltar.
    _voto(votacao, 9, "Sim", legislatura=56)
    _voto(votacao, 2, "Sim", legislatura=57)
    _voto(votacao, 1, "Sim", legislatura=57)

    votos = _detalhe(client, NOMINAL)["votos"]

    pares = [(v["nome"], v["legislatura"], v["id_camara"]) for v in votos]
    assert pares == [("Ana", 56, 9), ("Ana", 57, 2), ("Zeca", 57, 1)]


def test_voto_vazio_sai_null_nunca_string_vazia_nem_chave_ausente(client, run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 1, "Sim")
    _voto(votacao, 2, "")

    resposta = client.get(f"{LISTA}{NOMINAL}/")
    votos = resposta.json()["votos"]

    assert [v["voto"] for v in votos] == ["Sim", None]
    assert all("voto" in v for v in votos)
    assert '"voto": ""' not in resposta.content.decode()


def test_partido_vazio_sai_null_e_s_partido_sai_como_vem(client, run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 1, "Sim", party_acronym="")
    _voto(votacao, 2, "Sim", party_acronym="S/Partido")

    votos = _detalhe(client, NOMINAL)["votos"]

    assert [v["partido"] for v in votos] == [None, "S/Partido"]


def test_contagem_por_voto_soma_certo_e_separa_o_vazio(client, run):
    votacao = _votacao(run, NOMINAL)
    for camara_id, texto in enumerate(
        ["Sim", "Sim", "Sim", "Não", "Não", "", "", "Obstrução", "Abstenção"], start=1
    ):
        _voto(votacao, camara_id, texto)

    contagem = _detalhe(client, NOMINAL)["contagem_por_voto"]

    # Quantidade desc; no empate, o voto em ordem de texto e o vazio (`null`) por último.
    assert contagem == [
        {"voto": "Sim", "quantidade": 3},
        {"voto": "Não", "quantidade": 2},
        {"voto": None, "quantidade": 2},
        {"voto": "Abstenção", "quantidade": 1},
        {"voto": "Obstrução", "quantidade": 1},
    ]
    assert sum(item["quantidade"] for item in contagem) == 9


def test_contagem_vem_dos_votos_e_nao_dos_totais_da_fonte(client, nominal):
    # Totais da fonte: 300, 150 e 2. A contagem é do que o polis tem: 2 "Sim", 1 "Não" e 1
    # "Abstenção".
    corpo = _detalhe(client, NOMINAL)

    assert corpo["votacao"]["totais_da_fonte"] == {"sim": 300, "nao": 150, "outros": 2}
    assert corpo["contagem_por_voto"] == [
        {"voto": "Sim", "quantidade": 2},
        {"voto": "Abstenção", "quantidade": 1},
        {"voto": "Não", "quantidade": 1},
    ]


def test_votacao_sem_votos_nominais_devolve_votos_vazio(client, sem_votos):
    corpo = _detalhe(client, SEM_VOTOS)

    assert corpo["votos"] == []
    assert corpo["contagem_por_voto"] == []
    assert corpo["votacao"]["totais_da_fonte"] == {"sim": 300, "nao": 150, "outros": 2}


def test_nada_de_id_interno_nem_execucao_no_detalhe(client, nominal):
    corpo = _detalhe(client, NOMINAL)
    # `atribuicao.licenca.id` é o id da licença (contrato de todas as APIs), não id interno; por
    # isso a busca é fora das atribuições.
    resto = {k: v for k, v in corpo.items() if not k.startswith("atribuicao")}
    chaves = set(_todas_as_chaves(resto))

    assert not chaves & {"pk", "voting", "voting_id", "ingestion_run", "uri", "foto", "uf"}
    assert set(corpo["votacao"]) == CHAVES_VOTACAO  # o conjunto exato de chaves, sem `pk`


def test_atribuicao_do_detalhe_traz_fonte_conjunto_data_origem_e_licenca_nula(client, nominal):
    atribuicao = _detalhe(client, NOMINAL)["atribuicao"]

    assert atribuicao["fonte"] == "Câmara dos Deputados: Dados Abertos"
    assert atribuicao["conjunto"] == "Votações da Câmara em 2026"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM
    assert atribuicao["url_origem"] == URL_ORIGEM
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_votos_citam_o_conjunto_de_votos_e_nao_o_das_votacoes(client, run):
    # Os votos foram vistos por uma coleta de OUTRO conjunto (`camara/votos-2026`): a atribuição dos
    # votos tem de ser a dele, e a da votação continua sendo a do conjunto de votações.
    votos_run = _criar_run_dos_votos()
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 1, "Sim", ingestion_run=votos_run)
    _voto(votacao, 2, "Não", ingestion_run=votos_run)

    corpo = _detalhe(client, NOMINAL)

    assert corpo["atribuicao"]["conjunto"] == "Votações da Câmara em 2026"
    assert corpo["atribuicao"]["url_origem"] == URL_ORIGEM
    assert datetime.fromisoformat(corpo["atribuicao"]["coletado_em"]) == COLETADO_EM
    dos_votos = corpo["atribuicao_dos_votos"]
    assert dos_votos["fonte"] == "Câmara dos Deputados: Dados Abertos"
    assert dos_votos["conjunto"] == "Votos da Câmara em 2026"
    assert dos_votos["url_origem"] == URL_ORIGEM_DOS_VOTOS
    assert datetime.fromisoformat(dos_votos["coletado_em"]) == COLETADO_EM_DOS_VOTOS
    assert dos_votos["licenca"] == {"id": None, "url": None}


def test_atribuicao_dos_votos_e_a_da_coleta_mais_recente_entre_eles(client, run):
    antiga = _criar_run_dos_votos(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    nova = _criar_run_dos_votos(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 1, "Sim", ingestion_run=nova)
    _voto(votacao, 2, "Não", ingestion_run=antiga)
    _voto(votacao, 3, "Sim", ingestion_run=antiga)

    dos_votos = _detalhe(client, NOMINAL)["atribuicao_dos_votos"]

    assert datetime.fromisoformat(dos_votos["coletado_em"]) == nova.started_at


def test_sem_votos_a_atribuicao_dos_votos_e_null(client, sem_votos):
    corpo = _detalhe(client, SEM_VOTOS)

    assert corpo["atribuicao_dos_votos"] is None
    assert corpo["atribuicao"]["conjunto"] == "Votações da Câmara em 2026"


def test_votacao_inexistente_da_404(client, nominal):
    _detalhe(client, NOMINAL)  # controle

    # o formato é válido e não coincide com a fixture: o 404 vem da view, depois da consulta
    for codigo in ("999-1", "2641546-70", "01-2", "0-1", "0999-1"):
        assert client.get(f"{LISTA}{codigo}/").status_code == 404, codigo


@pytest.mark.parametrize(
    "codigo",
    [
        "abc",
        "2641546",
        "2641546-",
        "-7",
        "2641546--7",
        "2641546-7-8",
        "2641546-a",
        "2641546_7",
        "2641546-7%0A",  # `\n` no fim do id
        "2641546-7%20",
        "1234567890-1234567890",  # 21 caracteres: o varchar(20) do banco é o limite
        "12345678901-1",  # 11 dígitos antes do hífen: o parser aceita até 10
        "1-12345678901",  # 11 dígitos depois do hífen
        "1" * 50 + "-1",
        "٢٦٤١٥٤٦-٧",  # dígitos árabe-índicos: o int() do Python os lê como 2641546-7
        "2641546-٧",
    ],
)
def test_id_malformado_da_404_sem_consultar_o_banco(
    client, nominal, codigo, django_assert_num_queries
):
    _detalhe(client, NOMINAL)  # controle

    with django_assert_num_queries(0):
        resposta = client.get(f"{LISTA}{codigo}/")

    assert resposta.status_code == 404


def test_quebra_de_linha_depois_da_barra_final_da_404_sem_consultar_o_banco(
    client, nominal, django_assert_num_queries
):
    _detalhe(client, NOMINAL)  # controle

    with django_assert_num_queries(0):
        resposta = client.get(f"{LISTA}{NOMINAL}/%0A")

    # Premissa: o `\n` chegou à requisição (não foi descartado pelo client nem por middleware).
    assert resposta.wsgi_request.path_info == f"{LISTA}{NOMINAL}/\n"
    assert resposta.status_code == 404


@pytest.mark.parametrize(
    "codigo",
    [
        "1234567890-123456789",  # 20 caracteres, o máximo do varchar(20)
        "123456789-1234567890",  # 20 caracteres, com 10 dígitos depois do hífen
        "1-0",
        "2641546-07",  # zero à esquerda depois do hífen: o parser o aceita
        "01-2",  # zero à esquerda antes do hífen: o parser também o aceita e grava
        "0-1",
    ],
)
def test_id_no_formato_do_parser_resolve(client, run, codigo):
    assert len(codigo) <= 20
    _votacao(run, codigo)

    assert _detalhe(client, codigo)["votacao"]["id"] == codigo


def test_id_com_zero_a_esquerda_e_o_id_sem_zero_sao_registros_distintos(client, run):
    # O id é texto: `01-2` e `1-2` não são o mesmo registro, e cada URL devolve o seu.
    _votacao(run, "01-2", description="Com zero.")
    _votacao(run, "1-2", description="Sem zero.")

    assert _detalhe(client, "01-2")["votacao"]["descricao"] == "Com zero."
    assert _detalhe(client, "1-2")["votacao"]["descricao"] == "Sem zero."


def test_o_detalhe_custa_quatro_consultas_mesmo_com_muitos_votos(
    client, run, django_assert_num_queries
):
    votacao = _votacao(run, NOMINAL)
    for camara_id in range(1, 82):
        _voto(votacao, camara_id, "Sim")
        if camara_id % 2:
            _deputado(run, camara_id)
    _detalhe(client, NOMINAL)  # controle (e aquece o que o Django guarda em cache)

    # votação com a atribuição, votos, os deputados dos pares (uma consulta só, sem N+1) e as
    # proposições (uma consulta só, com a proposição e a atribuição num JOIN)
    with django_assert_num_queries(4):
        client.get(f"{LISTA}{NOMINAL}/")


def test_o_detalhe_sem_votos_nao_consulta_deputados(client, sem_votos, django_assert_num_queries):
    _detalhe(client, SEM_VOTOS)  # controle

    # votação com a atribuição e as proposições; sem votos não há consulta de deputados
    with django_assert_num_queries(3):
        client.get(f"{LISTA}{SEM_VOTOS}/")


# --- Proposições da votação (ADR 0033; emenda 5 do ADR 0032) -------------------------------------

URL_ORIGEM_DAS_PROPOSICOES = (
    "https://example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes-2026.csv"
)
URL_ORIGEM_DOS_OBJETOS = "https://example.org/arquivos/votacoesObjetos/csv/votacoesObjetos-2026.csv"
COLETADO_EM_DAS_PROPOSICOES = datetime(2026, 11, 26, 8, 0, tzinfo=UTC)
COLETADO_EM_DOS_OBJETOS = datetime(2026, 11, 26, 9, 30, tzinfo=UTC)
# Ementa de `votacoesProposicoes-2026` (proposição 104333, "PL 11/2003"), lida da fonte em
# 2026-11-26; o resto dos dados das proposições é sintético no formato medido.
EMENTA_REAL = (
    "Proíbe a veiculação de peças publicitárias, em qualquer meio de comunicação, "
    "que utilizem imagens sexuais como atrativo."
)


def _criar_run_das_proposicoes(started_at=COLETADO_EM_DAS_PROPOSICOES):
    return _criar_run(
        started_at,
        slug="votacoes-proposicoes-2026",
        nome="Proposições das votações da Câmara (2026)",
        url=URL_ORIGEM_DAS_PROPOSICOES,
    )


def _criar_run_dos_objetos(started_at=COLETADO_EM_DOS_OBJETOS):
    return _criar_run(
        started_at,
        slug="votacoes-objetos-2026",
        nome="Objetos das votações da Câmara (2026)",
        url=URL_ORIGEM_DOS_OBJETOS,
    )


def _proposicao(run, camara_id, **extra):
    campos = {
        "camara_id": camara_id,
        "title": f"PL {camara_id}/2026",
        "type_acronym": "PL",
        "number": camara_id,
        "year": 2026,
        "ementa": "Ementa de teste.",
        "ingestion_run": run,
        **extra,
    }
    return CamaraProposition.objects.create(**campos)


def _ligar(codigo, proposicao, origem="proposicoes", run=None):
    return CamaraVotingProposition.objects.create(
        camara_voting_id=codigo,
        proposition=proposicao,
        origin=origem,
        ingestion_run=run or proposicao.ingestion_run,
    )


def _ids_das_proposicoes(corpo):
    return [item["id_camara"] for item in corpo["proposicoes"]]


def test_proposicoes_so_com_as_chaves_das_listas_explicitas(client, nominal):
    run_proposicoes = _criar_run_das_proposicoes()
    run_objetos = _criar_run_dos_objetos()
    _ligar(NOMINAL, _proposicao(run_proposicoes, 1), "proposicoes")
    _ligar(NOMINAL, _proposicao(run_objetos, 2), "objetos")

    corpo = _detalhe(client, NOMINAL)

    assert set(corpo) == CHAVES_DETALHE
    assert len(corpo["proposicoes"]) == 2
    assert all(set(item) == CHAVES_PROPOSICAO for item in corpo["proposicoes"])
    assert set(corpo["atribuicao_das_proposicoes"]) == CHAVES_ATRIBUICAO
    chaves = set(_todas_as_chaves(corpo["proposicoes"]))
    assert not chaves & {"pk", "proposition", "proposition_id", "ingestion_run", "uri", "camara_id"}


def test_proposicao_com_os_campos_da_fonte(client, nominal):
    run_proposicoes = _criar_run_das_proposicoes()
    proposicao = _proposicao(
        run_proposicoes,
        104333,
        title="PL 11/2003",
        number=11,
        year=2003,
        ementa=EMENTA_REAL,
    )
    _ligar(NOMINAL, proposicao, "proposicoes")

    assert _detalhe(client, NOMINAL)["proposicoes"] == [
        {
            "id_camara": 104333,
            "titulo": "PL 11/2003",
            "tipo": "PL",
            "numero": 11,
            "ano": 2003,
            "ementa": EMENTA_REAL,
            "origem": "proposicoes",
        }
    ]


def test_ano_nulo_e_ementa_vazia_saem_null_nunca_zero_nem_string_vazia(client, nominal):
    run_objetos = _criar_run_dos_objetos()
    _ligar(NOMINAL, _proposicao(run_objetos, 7, year=None, ementa=""), "objetos")

    [item] = _detalhe(client, NOMINAL)["proposicoes"]

    assert "ano" in item and item["ano"] is None
    assert "ementa" in item and item["ementa"] is None


def test_proposicoes_saem_em_ordem_numerica_de_id_e_nao_de_texto(client, nominal):
    run_proposicoes = _criar_run_das_proposicoes()
    for camara_id in (100, 9, 10):
        _ligar(NOMINAL, _proposicao(run_proposicoes, camara_id), "proposicoes")

    assert _ids_das_proposicoes(_detalhe(client, NOMINAL)) == [9, 10, 100]


def test_proposicoes_vem_antes_de_objetos_mesmo_com_id_maior(client, nominal):
    run_proposicoes = _criar_run_das_proposicoes()
    run_objetos = _criar_run_dos_objetos()
    _ligar(NOMINAL, _proposicao(run_objetos, 5), "objetos")
    _ligar(NOMINAL, _proposicao(run_proposicoes, 50), "proposicoes")
    _ligar(NOMINAL, _proposicao(run_objetos, 3), "objetos")

    corpo = _detalhe(client, NOMINAL)

    assert [(i["origem"], i["id_camara"]) for i in corpo["proposicoes"]] == [
        ("proposicoes", 50),
        ("objetos", 3),
        ("objetos", 5),
    ]


def test_proposicoes_de_outra_votacao_nao_aparecem(client, nominal, sem_votos):
    run_proposicoes = _criar_run_das_proposicoes()
    _ligar(NOMINAL, _proposicao(run_proposicoes, 1))
    _ligar(SEM_VOTOS, _proposicao(run_proposicoes, 2))

    assert _ids_das_proposicoes(_detalhe(client, NOMINAL)) == [1]
    assert _ids_das_proposicoes(_detalhe(client, SEM_VOTOS)) == [2]


def test_votacao_sem_proposicao_devolve_lista_vazia_e_atribuicao_nula(client, nominal):
    corpo = _detalhe(client, NOMINAL)

    assert corpo["proposicoes"] == []
    assert corpo["atribuicao_das_proposicoes"] is None


def test_o_sentinela_zero_da_votacao_nao_esconde_as_proposicoes(client, run):
    _votacao(run, NOMINAL, proposition_id=0)
    _ligar(NOMINAL, _proposicao(_criar_run_dos_objetos(), 8), "objetos")

    corpo = _detalhe(client, NOMINAL)

    assert corpo["votacao"]["id_proposicao"] == 0
    assert _ids_das_proposicoes(corpo) == [8]


def test_atribuicao_das_proposicoes_e_a_da_coleta_mais_recente_entre_elas(client, nominal):
    run_proposicoes = _criar_run_das_proposicoes()
    run_objetos = _criar_run_dos_objetos()
    _ligar(NOMINAL, _proposicao(run_proposicoes, 1), "proposicoes")
    _ligar(NOMINAL, _proposicao(run_objetos, 2), "objetos")

    atribuicao = _detalhe(client, NOMINAL)["atribuicao_das_proposicoes"]

    assert atribuicao["conjunto"] == "Objetos das votações da Câmara (2026)"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM_DOS_OBJETOS
    assert atribuicao["url_origem"] == URL_ORIGEM_DOS_OBJETOS
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_a_atribuicao_das_proposicoes_nao_e_a_da_votacao_nem_a_dos_votos(client, nominal):
    _ligar(NOMINAL, _proposicao(_criar_run_das_proposicoes(), 1))

    corpo = _detalhe(client, NOMINAL)

    assert corpo["atribuicao_das_proposicoes"]["conjunto"] == (
        "Proposições das votações da Câmara (2026)"
    )
    assert corpo["atribuicao"]["conjunto"] == "Votações da Câmara em 2026"


def test_todas_as_213_proposicoes_saem_com_custo_constante_de_consultas(
    client, nominal, django_assert_num_queries
):
    run_objetos = _criar_run_dos_objetos()
    for camara_id in range(1, 214):
        _ligar(NOMINAL, _proposicao(run_objetos, camara_id), "objetos")
    corpo = _detalhe(client, NOMINAL)  # controle
    assert len(corpo["proposicoes"]) == 213

    # votação, votos, deputados dos pares e as 213 proposições numa consulta só (sem N+1)
    with django_assert_num_queries(4):
        client.get(f"{LISTA}{NOMINAL}/")


def test_votacao_inexistente_nao_consulta_proposicoes(client, nominal, django_assert_num_queries):
    _ligar(NOMINAL, _proposicao(_criar_run_das_proposicoes(), 1))
    _detalhe(client, NOMINAL)  # controle

    with django_assert_num_queries(1):  # só a busca da votação
        assert client.get(f"{LISTA}999-1/").status_code == 404


# --- Junção com o perfil do deputado (`tem_perfil` e `nome`) -------------------------------------


def _perfis(corpo):
    return {
        (v["legislatura"], v["id_camara"]): (v["tem_perfil"], v["nome"]) for v in corpo["votos"]
    }


def test_tem_perfil_e_nome_so_para_quem_esta_em_deputy(client, run, nominal):
    _deputado(run, 1, name="Ana")
    _deputado(run, 3, name="Carla")

    assert _perfis(_detalhe(client, NOMINAL)) == {
        (57, 1): (True, "Ana"),
        (57, 2): (False, None),
        (57, 3): (True, "Carla"),
        (57, 4): (False, None),
    }


def test_mesmo_id_da_camara_em_outra_legislatura_nao_casa(client, run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 3, "Sim", legislatura=57)
    _voto(votacao, 1, "Sim", legislatura=56)
    _voto(votacao, 2, "Sim", legislatura=56)
    # Existem, mas em outra legislatura que a do voto (ou numa que não votou): outro deputado.
    _deputado(run, 3, legislatura=56, name="Outro Deputado")
    _deputado(run, 1, legislatura=57, name="Outra Ana")
    _deputado(run, 2, legislatura=56, name="Bruno")

    assert _perfis(_detalhe(client, NOMINAL)) == {
        (57, 3): (False, None),
        (56, 1): (False, None),
        (56, 2): (True, "Bruno"),
    }


def test_deputado_fora_da_lista_de_exercicio_ainda_tem_perfil(client, run, nominal):
    _deputado(run, 1, name="Ana", in_office=False, left_list_at=COLETADO_EM)

    assert _perfis(_detalhe(client, NOMINAL))[(57, 1)] == (True, "Ana")


def test_sem_nenhum_deputy_ninguem_tem_perfil_e_nenhum_nome(client, nominal):
    perfis = _perfis(_detalhe(client, NOMINAL))

    assert set(perfis.values()) == {(False, None)}


def test_voto_vazio_de_quem_tem_perfil_sai_null_com_o_nome(client, run):
    votacao = _votacao(run, NOMINAL)
    _voto(votacao, 1, "")
    _deputado(run, 1, name="Ana")

    voto = _detalhe(client, NOMINAL)["votos"][0]

    assert (voto["voto"], voto["tem_perfil"], voto["nome"]) == (None, True, "Ana")


# --- Lista ---------------------------------------------------------------------------------------


def test_lista_mais_recente_primeiro_e_id_da_votacao_desempata(client, run):
    _votacao(run, "100-5", voted_on=date(2026, 1, 5))
    _votacao(run, "100-1", voted_on=date(2026, 3, 1))
    _votacao(run, "100-2", voted_on=date(2026, 3, 1))
    _votacao(run, "100-4", voted_on=date(2025, 12, 1))

    corpo = _ok(client, LISTA)

    assert [v["id"] for v in corpo["votacoes"]] == ["100-2", "100-1", "100-5", "100-4"]


def test_lista_so_com_as_chaves_explicitas(client, nominal, sem_votos):
    corpo = _ok(client, LISTA)

    assert set(corpo) == CHAVES_LISTA
    assert all(set(item) == CHAVES_ITEM_DA_LISTA for item in corpo["votacoes"])
    assert all(set(item["totais_da_fonte"]) == CHAVES_TOTAIS for item in corpo["votacoes"])
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO


def test_item_da_lista_com_os_campos_da_fonte(client, nominal):
    assert _ok(client, LISTA)["votacoes"] == [
        {
            "id": NOMINAL,
            "data": "2026-03-10",
            "orgao": "PLEN",
            "aprovacao": "1",
            "totais_da_fonte": {"sim": 300, "nao": 150, "outros": 2},
            "descricao": "Aprovada a Emenda nº 1.",
            "id_proposicao": 2651254,
            "tem_votos_nominais": True,
        }
    ]


def test_tem_votos_nominais_so_para_quem_tem_algum_voto(client, nominal, sem_votos):
    itens = {v["id"]: v["tem_votos_nominais"] for v in _ok(client, LISTA)["votacoes"]}

    assert itens == {NOMINAL: True, SEM_VOTOS: False}


def test_votacao_com_so_um_voto_vazio_tem_votos_nominais(client, run):
    # a fonte publica a presença: 466 votos sem posição na votação real `2645346-18`
    _voto(_votacao(run, "2645346-18"), 1, "")

    assert _ok(client, LISTA)["votacoes"][0]["tem_votos_nominais"] is True


def test_aprovacao_vazia_sai_null_na_lista(client, run):
    _votacao(run, "10-1", approval="")
    _votacao(run, "10-2", approval="0", voted_on=date(2026, 3, 9))

    itens = {v["id"]: v["aprovacao"] for v in _ok(client, LISTA)["votacoes"]}

    assert itens == {"10-1": None, "10-2": "0"}


def test_lista_pagina_de_50_em_50(client, run):
    for numero in range(1, 52):  # 51 votações, uma por dia
        _votacao(run, f"{numero}-1", voted_on=date(2026, 1, 1) + timedelta(days=numero))

    primeira = _ok(client, LISTA)
    segunda = _ok(client, f"{LISTA}?pagina=2")

    assert (primeira["pagina"], primeira["total_paginas"]) == (1, 2)
    assert len(primeira["votacoes"]) == 50
    assert primeira["votacoes"][0]["id"] == "51-1"  # a mais recente
    assert [v["id"] for v in segunda["votacoes"]] == ["1-1"]  # a mais antiga
    assert segunda["pagina"] == 2


def test_pagina_alem_da_ultima_devolve_lista_vazia(client, nominal):
    corpo = _ok(client, f"{LISTA}?pagina=9")

    assert corpo["votacoes"] == []
    assert (corpo["pagina"], corpo["total_paginas"]) == (9, 1)


def test_sem_nenhuma_votacao_lista_vazia_e_sem_atribuicao(client, run):
    corpo = _ok(client, LISTA)

    assert corpo == {"votacoes": [], "pagina": 1, "total_paginas": 0, "atribuicao": None}


@pytest.mark.parametrize(
    "pagina", ["0", "-1", "abc", "1.5", "12345", "", " 2", "00", "01", "0001", "09", "007"]
)
def test_pagina_malformada_da_400(client, nominal, pagina):
    _ok(client, LISTA)  # controle

    resposta = client.get(LISTA, {"pagina": pagina})

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "página inválida"}


@pytest.mark.parametrize("pagina", ["1", "2", "9999"])
def test_pagina_na_forma_canonica_segue_valida(client, nominal, pagina):
    corpo = _ok(client, f"{LISTA}?pagina={pagina}")

    assert corpo["pagina"] == int(pagina)


def test_atribuicao_da_lista_e_a_da_coleta_mais_recente_da_pagina(client, run):
    nova = _criar_run(started_at=datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    _votacao(run, "1-1", voted_on=date(2026, 1, 1))
    _votacao(nova, "2-1", voted_on=date(2025, 1, 1))  # mais antiga, mas vista pela coleta mais nova

    atribuicao = _ok(client, LISTA)["atribuicao"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == nova.started_at


def test_a_lista_custa_duas_consultas_mesmo_com_votos(client, run, django_assert_num_queries):
    for numero in range(1, 30):
        votacao = _votacao(run, f"{numero}-1")
        if numero % 2:
            _voto(votacao, 1, "Sim")
            _voto(votacao, 2, "Não")
    _ok(client, LISTA)  # controle

    # a contagem e a página (a marca `tem_votos_nominais` vem na mesma consulta, sem N+1)
    with django_assert_num_queries(2):
        client.get(LISTA)


# --- As duas rotas -------------------------------------------------------------------------------


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, nominal, metodo):
    for url in (LISTA, f"{LISTA}{NOMINAL}/"):
        _ok(client, url)  # controle

        assert getattr(client, metodo)(url).status_code == 405
