"""API interna do perfil do senador (ADR 0028, molde do ADR 0021 decisão 4 e do ADR 0027).

`GET /internal/v1/senadores/<codigo>/`. Dados sintéticos. O que mais importa é a saída: só campos
de uma lista explícita, nunca id interno, sempre com a atribuição da fonte. Os testes de 404 e 405
pedem antes um 200 de controle: sem isso, uma rota que não existe passaria por "404 esperado".
"""

from datetime import UTC, datetime

import pytest

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

CODIGO = 5895
URL = f"/internal/v1/senadores/{CODIGO}/"
COLETADO_EM = datetime(2026, 11, 12, 15, 30, tzinfo=UTC)
URL_ORIGEM = "https://example.org/dadosabertos/senador/lista/atual.json"

CHAVES_RAIZ = {"senador", "atribuicao"}
CHAVES_SENADOR = {"id_senado", "nome", "partido", "uf", "em_exercicio", "saiu_da_lista_em"}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}
CHAVES_LICENCA = {"id", "url"}


@pytest.fixture
def run():
    source = Source.objects.create(
        slug="senado",
        name="Senado Federal: Dados Abertos",
        institution="Senado Federal",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    dataset = Dataset.objects.create(
        source=source,
        slug="senadores",
        name="Senadores em exercício",
        url=URL_ORIGEM,
        format=Dataset.Format.JSON_SENADO,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Decisão do dono de teste.",
    )
    return IngestionRun.objects.create(
        dataset=dataset, source_url=dataset.url, started_at=COLETADO_EM
    )


def _senador(run, **extra):
    from apps.legislature.models import Senator

    campos = {
        "senate_id": CODIGO,
        "name": "Ana do Senado",
        "party_acronym": "XYZ",
        "state": "SP",
        "ingestion_run": run,
        **extra,
    }
    return Senator.objects.create(**campos)


@pytest.fixture
def senador(run):
    return _senador(run)


def _perfil(client, url=URL):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def test_perfil_de_senador_existente(client, senador):
    assert _perfil(client)["senador"] == {
        "id_senado": CODIGO,
        "nome": "Ana do Senado",
        "partido": "XYZ",
        "uf": "SP",
        "em_exercicio": True,
        "saiu_da_lista_em": None,
    }


def test_so_saem_as_chaves_da_lista_explicita(client, senador):
    corpo = _perfil(client)

    assert set(corpo) == CHAVES_RAIZ
    assert set(corpo["senador"]) == CHAVES_SENADOR
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO
    assert set(corpo["atribuicao"]["licenca"]) == CHAVES_LICENCA


def test_nada_de_id_interno_nem_execucao_no_corpo(client, senador):
    _perfil(client)  # controle: sem o 200, um 404 também "não tem id interno"
    texto = client.get(URL).content.decode()

    assert f'"id": {senador.pk}' not in texto
    assert "ingestion_run" not in texto


def test_atribuicao_traz_fonte_conjunto_data_origem_e_licenca_nula(client, senador):
    atribuicao = _perfil(client)["atribuicao"]

    assert atribuicao["fonte"] == "Senado Federal: Dados Abertos"
    assert atribuicao["conjunto"] == "Senadores em exercício"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM
    assert atribuicao["url_origem"] == URL_ORIGEM
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_partido_vazio_sai_como_null(client, run):
    _senador(run, party_acronym="")

    assert _perfil(client)["senador"]["partido"] is None


def test_senador_fora_da_lista_mostra_a_data_da_coleta(client, run):
    saiu = datetime(2026, 11, 13, 8, 0, tzinfo=UTC)
    _senador(run, in_office=False, left_list_at=saiu)

    perfil = _perfil(client)["senador"]

    assert perfil["em_exercicio"] is False
    assert perfil["saiu_da_lista_em"] == saiu.isoformat()


@pytest.mark.parametrize("codigo", ["999999", "1"])
def test_senador_inexistente_da_404_sem_repetir_o_pedido(client, senador, codigo):
    _perfil(client)  # controle: a rota existe e o senador conhecido responde

    resposta = client.get(f"/internal/v1/senadores/{codigo}/")

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "não encontrado"}
    assert codigo not in resposta.content.decode()


@pytest.mark.parametrize(
    "codigo", ["abc", "-1", "0x1", "1234567890", "58-95", "5895-", "5_895", "5895/1"]
)
def test_codigo_malformado_da_404_sem_consultar_o_banco(
    client, senador, codigo, django_assert_num_queries
):
    _perfil(client)  # controle

    with django_assert_num_queries(0):
        resposta = client.get(f"/internal/v1/senadores/{codigo}/")

    assert resposta.status_code == 404


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, senador, metodo):
    _perfil(client)  # controle

    assert getattr(client, metodo)(URL).status_code == 405


def test_o_perfil_custa_uma_consulta_so(client, senador, django_assert_num_queries):
    _perfil(client)  # controle (e aquece o que o Django guarda em cache)

    with django_assert_num_queries(1):
        client.get(URL)
