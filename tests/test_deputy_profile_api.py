"""API interna do perfil do deputado (ADR 0015 decisão 2, ADR 0021 decisão 4, ADR 0008 decisão 3).

`GET /internal/v1/deputados/<legislatura>-<id>/`. Dados todos sintéticos. O que mais importa aqui
é a saída: só campos de uma lista explícita, nunca `uri` nem id interno, sempre com a atribuição
da fonte. Os testes de 404 e 405 pedem antes um 200 de controle: sem isso, uma rota que não
existe passaria por "404 esperado".
"""

from datetime import UTC, datetime

import pytest

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LEGISLATURA = 57
ID_CAMARA = 204554
URL = f"/internal/v1/deputados/{LEGISLATURA}-{ID_CAMARA}/"
COLETADO_EM = datetime(2026, 11, 10, 15, 30, tzinfo=UTC)
URL_ORIGEM = "https://example.org/api/v2/deputados?itens=100"

CHAVES_RAIZ = {"deputado", "atribuicao"}
CHAVES_DEPUTADO = {
    "legislatura",
    "id_camara",
    "nome",
    "partido",
    "uf",
    "em_exercicio",
    "saiu_da_lista_em",
}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}
CHAVES_LICENCA = {"id", "url"}


@pytest.fixture
def run():
    source = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    dataset = Dataset.objects.create(
        source=source,
        slug="deputados",
        name="Deputados em exercício (legislatura atual)",
        url=URL_ORIGEM,
        format=Dataset.Format.JSON,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Decisão do dono de teste.",
    )
    return IngestionRun.objects.create(
        dataset=dataset, source_url=dataset.url, started_at=COLETADO_EM
    )


def _deputado(run, **extra):
    from apps.legislature.models import Deputy

    campos = {
        "legislature_id": LEGISLATURA,
        "camara_id": ID_CAMARA,
        "name": "Ana da Câmara",
        "party_acronym": "XYZ",
        "state": "SP",
        "ingestion_run": run,
        **extra,
    }
    return Deputy.objects.create(**campos)


@pytest.fixture
def deputado(run):
    return _deputado(run)


def _perfil(client, url=URL):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def test_perfil_de_deputado_existente(client, deputado):
    corpo = _perfil(client)

    assert corpo["deputado"] == {
        "legislatura": LEGISLATURA,
        "id_camara": ID_CAMARA,
        "nome": "Ana da Câmara",
        "partido": "XYZ",
        "uf": "SP",
        "em_exercicio": True,
        "saiu_da_lista_em": None,
    }


def test_so_saem_as_chaves_da_lista_explicita(client, deputado):
    corpo = _perfil(client)

    assert set(corpo) == CHAVES_RAIZ
    assert set(corpo["deputado"]) == CHAVES_DEPUTADO
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO
    assert set(corpo["atribuicao"]["licenca"]) == CHAVES_LICENCA


def test_nada_de_uri_nem_id_interno_no_corpo(client, deputado):
    _perfil(client)  # controle: sem o 200, um 404 também "não tem uri"
    texto = client.get(URL).content.decode()

    assert "uri" not in texto
    assert "dadosabertos" not in texto
    assert f'"id": {deputado.pk}' not in texto
    assert "ingestion_run" not in texto


def test_atribuicao_traz_fonte_conjunto_data_origem_e_licenca_nula(client, run, deputado):
    atribuicao = _perfil(client)["atribuicao"]

    assert atribuicao["fonte"] == "Câmara dos Deputados: Dados Abertos"
    assert atribuicao["conjunto"] == "Deputados em exercício (legislatura atual)"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM
    assert atribuicao["url_origem"] == URL_ORIGEM
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_a_atribuicao_e_a_da_ultima_execucao_que_viu_o_deputado(client, run):
    from apps.legislature.models import Deputy

    deputado = _deputado(run)
    nova = IngestionRun.objects.create(
        dataset=run.dataset,
        source_url=run.dataset.url,
        started_at=datetime(2026, 11, 11, 9, 0, tzinfo=UTC),
    )
    Deputy.objects.filter(pk=deputado.pk).update(ingestion_run=nova)

    atribuicao = _perfil(client)["atribuicao"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == datetime(
        2026, 11, 11, 9, 0, tzinfo=UTC
    )


def test_partido_vazio_sai_como_null(client, run):
    _deputado(run, party_acronym="")

    assert _perfil(client)["deputado"]["partido"] is None


def test_mesmo_id_da_camara_em_outra_legislatura_e_outro_deputado(client, run):
    _deputado(run)
    _deputado(run, legislature_id=58, name="Ana da Câmara (58)", state="RJ")

    na_57 = _perfil(client)["deputado"]
    na_58 = _perfil(client, f"/internal/v1/deputados/58-{ID_CAMARA}/")["deputado"]

    assert (na_57["legislatura"], na_57["nome"], na_57["uf"]) == (57, "Ana da Câmara", "SP")
    assert (na_58["legislatura"], na_58["nome"], na_58["uf"]) == (58, "Ana da Câmara (58)", "RJ")


@pytest.mark.parametrize("url", ["57-999999", "58-204554"])
def test_deputado_inexistente_da_404_sem_repetir_o_pedido(client, deputado, url):
    _perfil(client)  # controle: a rota existe e o deputado conhecido responde

    resposta = client.get(f"/internal/v1/deputados/{url}/")

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "não encontrado"}
    assert url.split("-")[1] not in resposta.content.decode()


@pytest.mark.parametrize(
    "legislatura_id",
    ["abc", "57-", "-1", "57-0x1", "57-1234567890", "1234567890-1", "57_1", "571", "57-1-2"],
)
def test_id_malformado_da_404_sem_consultar_o_banco(
    client, deputado, legislatura_id, django_assert_num_queries
):
    _perfil(client)  # controle

    with django_assert_num_queries(0):
        resposta = client.get(f"/internal/v1/deputados/{legislatura_id}/")

    assert resposta.status_code == 404


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, deputado, metodo):
    _perfil(client)  # controle

    resposta = getattr(client, metodo)(URL)

    assert resposta.status_code == 405


def test_o_perfil_custa_uma_consulta_so(client, deputado, django_assert_num_queries):
    _perfil(client)  # controle (e aquece o que o Django guarda em cache)

    with django_assert_num_queries(1):
        client.get(URL)
