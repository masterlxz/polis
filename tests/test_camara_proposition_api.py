"""API interna da proposição da Câmara com as tramitações (ADR 0035).

`GET /internal/v1/camara/proposicoes/<id>/`. Dados sintéticos no formato medido em 2026-11-27
(Rodada 5 de `fontes/camara.md`: no máximo 98 tramitações por proposição). O que mais importa:
a rota só existe para proposição que o polis conhece (`CamaraProposition`), mesmo havendo
tramitações (decisão do dono); a tramitação não tem chave para a proposição, então a junção é pelo
id em texto na leitura; a ordem é feita em Python (data e hora, `sequencia` com nula por último,
órgão, descrição); `data_hora` sai com `-03:00`; só saem campos de listas explícitas. Os testes de
404 e 405 pedem antes um 200 de controle: sem isso, uma rota que não existe passaria por "erro
esperado".
"""

from datetime import UTC, datetime, timedelta

import pytest

from apps.legislature.models import CamaraProposition, CamaraPropositionStep
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

BASE = "/internal/v1/camara/proposicoes/"
PROPOSICAO = 14666
COLETADO_DA_PROPOSICAO = datetime(2026, 11, 26, 8, 0, tzinfo=UTC)
COLETADO_DAS_TRAMITACOES = datetime(2026, 11, 27, 12, 53, tzinfo=UTC)
URL_DA_PROPOSICAO = "https://example.org/arquivos/votacoesProposicoes/csv/votacoesProposicoes.csv"
URL_DAS_TRAMITACOES = (
    "https://example.org/arquivos/proposicoesTramitacoes/csv/proposicoesTramitacoes-2026.csv"
)
# 2026-05-07 16:58 em Brasília (a primeira tramitação da proposição 14666 no arquivo de 2026).
QUANDO = datetime(2026, 5, 7, 19, 58, tzinfo=UTC)

CHAVES_RESPOSTA = {
    "proposicao",
    "tramitacoes",
    "atribuicao_da_proposicao",
    "atribuicao_das_tramitacoes",
}
CHAVES_PROPOSICAO = {"id_camara", "titulo", "tipo", "numero", "ano", "ementa"}
CHAVES_TRAMITACAO = {"sequencia", "data_hora", "orgao", "descricao"}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}


def _criar_run(slug, nome, url, started_at):
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


def _run_da_proposicao(started_at=COLETADO_DA_PROPOSICAO):
    return _criar_run(
        "votacoes-proposicoes-2026",
        "Proposições das votações da Câmara (2026)",
        URL_DA_PROPOSICAO,
        started_at,
    )


def _run_das_tramitacoes(started_at=COLETADO_DAS_TRAMITACOES):
    return _criar_run(
        "proposicoes-tramitacoes-2026",
        "Tramitações das proposições da Câmara (2026)",
        URL_DAS_TRAMITACOES,
        started_at,
    )


def _proposicao(camara_id=PROPOSICAO, run=None, **extra):
    campos = {
        "camara_id": camara_id,
        "title": "PL 11/2003",
        "type_acronym": "PL",
        "number": 11,
        "year": 2003,
        "ementa": "Proíbe a veiculação de peças publicitárias.",
        "ingestion_run": run or _run_da_proposicao(),
        **extra,
    }
    return CamaraProposition.objects.create(**campos)


def _passo(proposicao=PROPOSICAO, run=None, **extra):
    campos = {
        "camara_proposition_id": str(proposicao),
        "sequence": 152,
        "occurred_at": QUANDO,
        "organ_code": "MESA",
        "description": "Apresentação de Requerimento",
        "ingestion_run": run or _run_das_tramitacoes(),
        **extra,
    }
    return CamaraPropositionStep.objects.create(**campos)


@pytest.fixture
def com_tramitacao():
    run = _run_das_tramitacoes()
    _proposicao()
    _passo(run=run)
    return run


def _ok(client, id_=PROPOSICAO):
    resposta = client.get(f"{BASE}{id_}/")
    assert resposta.status_code == 200, f"controle: esperava 200 em {id_}"
    return resposta.json()


def _todas_as_chaves(valor):
    if isinstance(valor, dict):
        for chave, item in valor.items():
            yield chave
            yield from _todas_as_chaves(item)
    elif isinstance(valor, list):
        for item in valor:
            yield from _todas_as_chaves(item)


# --- forma da resposta ---------------------------------------------------------------------------


def test_so_as_chaves_das_listas_explicitas_e_nada_interno(client, com_tramitacao):
    corpo = _ok(client)

    assert set(corpo) == CHAVES_RESPOSTA
    assert set(corpo["proposicao"]) == CHAVES_PROPOSICAO
    assert [set(item) for item in corpo["tramitacoes"]] == [CHAVES_TRAMITACAO]
    assert set(corpo["atribuicao_da_proposicao"]) == CHAVES_ATRIBUICAO
    assert set(corpo["atribuicao_das_tramitacoes"]) == CHAVES_ATRIBUICAO
    proibidas = {"pk", "id", "camara_proposition_id", "ingestion_run", "origem", "despacho"}
    assert not set(_todas_as_chaves(corpo)) & proibidas


def test_a_proposicao_e_a_tramitacao_com_os_valores_da_fonte(client, com_tramitacao):
    corpo = _ok(client)

    assert corpo["proposicao"] == {
        "id_camara": 14666,
        "titulo": "PL 11/2003",
        "tipo": "PL",
        "numero": 11,
        "ano": 2003,
        "ementa": "Proíbe a veiculação de peças publicitárias.",
    }
    assert corpo["tramitacoes"] == [
        {
            "sequencia": 152,
            "data_hora": "2026-05-07T16:58:00-03:00",
            "orgao": "MESA",
            "descricao": "Apresentação de Requerimento",
        }
    ]


def test_ano_nulo_e_ementa_vazia_saem_null_nunca_zero_nem_string_vazia(client):
    _proposicao(year=None, ementa="")

    proposicao = _ok(client)["proposicao"]

    assert "ano" in proposicao and proposicao["ano"] is None
    assert "ementa" in proposicao and proposicao["ementa"] is None


def test_sequencia_vazia_sai_null_e_nao_some(client, com_tramitacao):
    CamaraPropositionStep.objects.all().delete()
    _passo(sequence=None)

    [item] = _ok(client)["tramitacoes"]

    assert "sequencia" in item and item["sequencia"] is None


def test_o_html_da_descricao_sai_como_veio_e_so_a_pagina_escapa(client, com_tramitacao):
    CamaraPropositionStep.objects.all().delete()
    _passo(description="<b>texto</b> da fonte")

    assert _ok(client)["tramitacoes"][0]["descricao"] == "<b>texto</b> da fonte"


def test_a_hora_sai_em_brasilia_com_o_deslocamento_mesmo_guardada_em_utc(client):
    _proposicao()
    _passo(occurred_at=datetime(2026, 1, 2, 3, 0, tzinfo=UTC))

    assert _ok(client)["tramitacoes"][0]["data_hora"] == "2026-01-02T00:00:00-03:00"


# --- ordem -------------------------------------------------------------------------------------


def _chave_da_ordem(corpo):
    return [
        (item["data_hora"][11:16], item["sequencia"], item["orgao"], item["descricao"])
        for item in corpo["tramitacoes"]
    ]


def test_ordem_por_hora_depois_sequencia_com_nula_por_ultimo_depois_orgao_e_descricao(client):
    _proposicao()
    run = _run_das_tramitacoes()
    dez = datetime(2026, 5, 7, 13, 0, tzinfo=UTC)  # 10:00 em Brasília
    nove = dez - timedelta(hours=1)
    _passo(run=run, occurred_at=dez, sequence=2, organ_code="MESA", description="b")
    _passo(run=run, occurred_at=dez, sequence=None, organ_code="MESA", description="a")
    _passo(run=run, occurred_at=nove, sequence=5, organ_code="MESA", description="a")
    _passo(run=run, occurred_at=dez, sequence=1, organ_code="PLEN", description="a")
    _passo(run=run, occurred_at=dez, sequence=1, organ_code="MESA", description="z")
    _passo(run=run, occurred_at=dez, sequence=1, organ_code="MESA", description="y")

    assert _chave_da_ordem(_ok(client)) == [
        ("09:00", 5, "MESA", "a"),
        ("10:00", 1, "MESA", "y"),
        ("10:00", 1, "MESA", "z"),
        ("10:00", 1, "PLEN", "a"),
        ("10:00", 2, "MESA", "b"),
        ("10:00", None, "MESA", "a"),
    ]


def test_a_sequencia_ordena_como_numero_e_nao_como_texto(client):
    _proposicao()
    run = _run_das_tramitacoes()
    for sequencia in (100, 9, 10):
        _passo(run=run, sequence=sequencia)

    assert [item["sequencia"] for item in _ok(client)["tramitacoes"]] == [9, 10, 100]


def test_as_98_tramitacoes_do_pior_caso_saem_todas_sem_paginacao(client):
    _proposicao()
    run = _run_das_tramitacoes()
    for sequencia in range(1, 99):
        _passo(run=run, sequence=sequencia)

    assert len(_ok(client)["tramitacoes"]) == 98


# --- o que entra e o que não entra ------------------------------------------------------------


def test_tramitacao_de_outra_proposicao_nao_aparece(client, com_tramitacao):
    _proposicao(146660)
    _passo(146660, description="Só desta outra")
    _passo(1466, description="Outra, prefixo do id")

    assert [item["descricao"] for item in _ok(client)["tramitacoes"]] == [
        "Apresentação de Requerimento"
    ]


def test_proposicao_conhecida_sem_tramitacao_devolve_lista_vazia_e_atribuicao_nula(client):
    _proposicao()

    corpo = _ok(client)

    assert corpo["tramitacoes"] == []
    assert corpo["atribuicao_das_tramitacoes"] is None
    assert corpo["atribuicao_da_proposicao"] is not None


def test_proposicao_desconhecida_e_404_mesmo_com_tramitacoes(client, com_tramitacao):
    _passo(777, description="Tramitação de proposição que o polis não tem")

    resposta = client.get(f"{BASE}777/")

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "não encontrado"}


# --- atribuição --------------------------------------------------------------------------------


def test_a_atribuicao_da_proposicao_e_a_da_execucao_que_a_viu(client, com_tramitacao):
    atribuicao = _ok(client)["atribuicao_da_proposicao"]

    assert atribuicao["conjunto"] == "Proposições das votações da Câmara (2026)"
    assert atribuicao["url_origem"] == URL_DA_PROPOSICAO
    assert atribuicao["coletado_em"] == COLETADO_DA_PROPOSICAO.isoformat()
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_a_atribuicao_das_tramitacoes_e_a_da_coleta_mais_recente_entre_elas(client):
    _proposicao()
    antiga = _run_das_tramitacoes(COLETADO_DAS_TRAMITACOES - timedelta(days=2))
    recente = _run_das_tramitacoes(COLETADO_DAS_TRAMITACOES)
    _passo(run=antiga, sequence=1)
    _passo(run=recente, sequence=2)
    _passo(run=antiga, sequence=3)

    atribuicao = _ok(client)["atribuicao_das_tramitacoes"]

    assert atribuicao["conjunto"] == "Tramitações das proposições da Câmara (2026)"
    assert atribuicao["url_origem"] == URL_DAS_TRAMITACOES
    assert atribuicao["coletado_em"] == COLETADO_DAS_TRAMITACOES.isoformat()


# --- a rota ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "id_",
    ["0", "01", "abc", "1x", "-1", "١٤٦٦٦", "12345678901", "2147483648", "99999999999999"],
)
def test_id_que_nao_e_valido_e_404_sem_consultar_o_banco(
    client, com_tramitacao, id_, django_assert_num_queries
):
    _ok(client)  # controle: a rota existe
    with django_assert_num_queries(0):
        resposta = client.get(f"{BASE}{id_}/")

    assert resposta.status_code == 404


def test_o_maior_id_de_32_bits_e_aceito_pela_rota(client):
    _proposicao(2147483647)

    assert _ok(client, 2147483647)["proposicao"]["id_camara"] == 2147483647


def test_so_leitura_post_e_405(client, com_tramitacao):
    _ok(client)  # controle

    assert client.post(f"{BASE}{PROPOSICAO}/").status_code == 405


def test_o_detalhe_custa_duas_consultas_mesmo_com_muitas_tramitacoes(
    client, django_assert_num_queries
):
    _proposicao()
    run = _run_das_tramitacoes()
    for sequencia in range(1, 99):
        _passo(run=run, sequence=sequencia)
    _ok(client)  # controle (e aquece o que o Django guarda em cache)

    # a proposição com a atribuição e as tramitações com a atribuição (sem N+1)
    with django_assert_num_queries(2):
        client.get(f"{BASE}{PROPOSICAO}/")


def test_proposicao_desconhecida_custa_uma_consulta(
    client, com_tramitacao, django_assert_num_queries
):
    _ok(client)  # controle

    with django_assert_num_queries(1):
        client.get(f"{BASE}777/")
