"""API interna do perfil da pessoa (ADR 0015 decisão 2, ADR 0005 e ADR 0008, ADR 0009 fatia 3).

`GET /internal/v1/pessoas/<ciclo>-<sq>/`. Dados todos sintéticos. O que mais importa aqui é a
saída: só campos de uma lista explícita, nunca o nome social nem id interno, sempre com a
atribuição da fonte. Os testes de 404 e 405 pedem antes um 200 de controle: sem isso, uma rota
que não existe passaria por "404 esperado".
"""

from datetime import date, datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.elections.models import Candidacy, Election, Person
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

CICLO = 2026
SQ = 1_000_000_001
URL = f"/internal/v1/pessoas/{CICLO}-{SQ}/"
NOME_SOCIAL_SECRETO = "Nome Social Interno de Teste"

CHAVES_RAIZ = {"pessoa", "candidaturas"}
CHAVES_PESSOA = {"ciclo", "id_tse", "nome"}
CHAVES_CANDIDATURA = {
    "eleicao",
    "cargo",
    "abrangencia",
    "uf",
    "unidade_eleitoral",
    "numero_urna",
    "partido",
    "federacao",
    "coligacao",
    "situacao",
    "resultado",
    "atribuicao",
}
CHAVES_ELEICAO = {"codigo", "turno", "ano", "descricao", "data"}
CHAVES_UNIDADE = {"codigo", "nome"}
CHAVES_PARTIDO = {"numero", "sigla", "nome"}
CHAVES_FEDERACAO = {"sigla", "nome"}
CHAVES_COLIGACAO = {"nome", "composicao"}
CHAVES_ATRIBUICAO = {
    "fonte",
    "conjunto",
    "coletado_em",
    "gerado_pela_fonte_em",
    "url_origem",
    "licenca",
}
CHAVES_LICENCA = {"id", "url"}


@pytest.fixture
def run():
    source = Source.objects.create(
        slug="tse",
        name="TSE",
        institution="Tribunal Superior Eleitoral",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    dataset = Dataset.objects.create(
        source=source,
        slug="consulta-cand-2026",
        name="Consulta de candidatos 2026",
        url="https://example.org/consulta_cand.zip",
        format=Dataset.Format.ZIP_CSV,
        license_basis=Dataset.LicenseBasis.DECLARED,
        license_id="cc-by",
        license_url="https://example.org/licencas/cc-by",
    )
    return IngestionRun.objects.create(dataset=dataset, source_url=dataset.url)


def _eleicao(**extra):
    campos = {
        "tse_code": 6259,
        "round": 1,
        "year": 2026,
        "kind_code": 2,
        "kind_name": "Eleição Ordinária",
        "description": "Eleições Gerais Estaduais 2026",
        "date": date(2026, 10, 4),
        **extra,
    }
    return Election.objects.create(**campos)


def _pessoa(**extra):
    campos = {"cycle_year": CICLO, "tse_candidate_id": SQ, "public_name": "Fulano da Urna"}
    return Person.objects.create(**{**campos, **extra})


def _candidatura(run, eleicao, pessoa, **extra):
    campos = {
        "election": eleicao,
        "person": pessoa,
        "ballot_number": 12345,
        "office_code": 6,
        "office_name": "DEPUTADO FEDERAL",
        "scope": "ESTADUAL",
        "state": "SP",
        "electoral_unit_code": "SP",
        "electoral_unit_name": "SÃO PAULO",
        "party_number": 12,
        "party_acronym": "XYZ",
        "party_name": "Partido de Teste",
        "ingestion_run": run,
        "source_generated_at": timezone.now(),
        **extra,
    }
    return Candidacy.objects.create(**campos)


@pytest.fixture
def pessoa_simples(run):
    pessoa = _pessoa()
    _candidatura(run, _eleicao(), pessoa)
    return pessoa


def _perfil(client, url=URL):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def test_perfil_de_pessoa_existente(client, pessoa_simples):
    resposta = client.get(URL)

    assert resposta.status_code == 200
    assert resposta["Content-Type"].startswith("application/json")
    corpo = resposta.json()
    assert corpo["pessoa"] == {"ciclo": 2026, "id_tse": SQ, "nome": "Fulano da Urna"}
    [candidatura] = corpo["candidaturas"]
    assert candidatura["cargo"] == "DEPUTADO FEDERAL"
    assert candidatura["abrangencia"] == "ESTADUAL"
    assert candidatura["uf"] == "SP"
    assert candidatura["unidade_eleitoral"] == {"codigo": "SP", "nome": "SÃO PAULO"}
    assert candidatura["numero_urna"] == 12345
    assert candidatura["partido"] == {"numero": 12, "sigla": "XYZ", "nome": "Partido de Teste"}
    assert candidatura["eleicao"] == {
        "codigo": 6259,
        "turno": 1,
        "ano": 2026,
        "descricao": "Eleições Gerais Estaduais 2026",
        "data": "2026-10-04",
    }


def test_duas_candidaturas_saem_ordenadas_por_turno(client, run):
    pessoa = _pessoa()
    # Criado de propósito na ordem inversa: a ordem da resposta não pode ser a de inserção.
    _candidatura(run, _eleicao(tse_code=6260, round=2, date=date(2026, 10, 25)), pessoa)
    _candidatura(run, _eleicao(tse_code=6259, round=1), pessoa)

    corpo = _perfil(client)

    assert [c["eleicao"]["turno"] for c in corpo["candidaturas"]] == [1, 2]


def test_nome_social_nunca_aparece_no_corpo(client, run):
    pessoa = _pessoa(social_name=NOME_SOCIAL_SECRETO)
    _candidatura(run, _eleicao(), pessoa)

    resposta = client.get(URL)

    assert resposta.status_code == 200, "controle: esperava 200"
    texto = resposta.content.decode()
    assert NOME_SOCIAL_SECRETO not in texto
    assert "social" not in texto.lower()


def test_so_saem_as_chaves_da_lista_explicita(client, run):
    pessoa = _pessoa(social_name=NOME_SOCIAL_SECRETO)
    _candidatura(
        run,
        _eleicao(),
        pessoa,
        federation_acronym="FED",
        federation_name="Federação de Teste",
        coalition_name="Coligação de Teste",
        coalition_composition="A / B / C",
        status_code=2,
        status_name="Deferido",
        result_code=1,
        result_name="Eleito",
    )

    corpo = _perfil(client)

    assert set(corpo) == CHAVES_RAIZ
    assert set(corpo["pessoa"]) == CHAVES_PESSOA
    [candidatura] = corpo["candidaturas"]
    assert set(candidatura) == CHAVES_CANDIDATURA
    assert set(candidatura["eleicao"]) == CHAVES_ELEICAO
    assert set(candidatura["unidade_eleitoral"]) == CHAVES_UNIDADE
    assert set(candidatura["partido"]) == CHAVES_PARTIDO
    assert set(candidatura["federacao"]) == CHAVES_FEDERACAO
    assert set(candidatura["coligacao"]) == CHAVES_COLIGACAO
    assert set(candidatura["atribuicao"]) == CHAVES_ATRIBUICAO
    assert set(candidatura["atribuicao"]["licenca"]) == CHAVES_LICENCA


def test_situacao_e_resultado_preenchidos_saem_como_texto(client, run):
    _candidatura(
        run,
        _eleicao(),
        _pessoa(),
        status_code=2,
        status_name="Deferido",
        result_code=1,
        result_name="Eleito",
    )

    [candidatura] = _perfil(client)["candidaturas"]

    assert candidatura["situacao"] == "Deferido"
    assert candidatura["resultado"] == "Eleito"


def test_atribuicao_traz_fonte_conjunto_datas_link_e_licenca(client, run):
    gerado = timezone.now().replace(microsecond=0)
    _candidatura(run, _eleicao(), _pessoa(), source_generated_at=gerado)

    [candidatura] = _perfil(client)["candidaturas"]

    atribuicao = candidatura["atribuicao"]
    assert atribuicao["fonte"] == "TSE"
    assert atribuicao["conjunto"] == "Consulta de candidatos 2026"
    assert atribuicao["url_origem"] == "https://example.org/consulta_cand.zip"
    assert atribuicao["licenca"] == {"id": "cc-by", "url": "https://example.org/licencas/cc-by"}
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == run.started_at
    assert datetime.fromisoformat(atribuicao["gerado_pela_fonte_em"]) == gerado


def test_sem_federacao_coligacao_situacao_e_resultado_saem_null(client, pessoa_simples):
    [candidatura] = _perfil(client)["candidaturas"]

    assert candidatura["federacao"] is None
    assert candidatura["coligacao"] is None
    assert candidatura["situacao"] is None
    assert candidatura["resultado"] is None


def test_mesmo_sq_em_outro_ciclo_e_outra_pessoa(client, run):
    _candidatura(run, _eleicao(), _pessoa(public_name="Pessoa de 2026"))
    outra = _pessoa(cycle_year=2022, public_name="Pessoa de 2022")
    _candidatura(run, _eleicao(tse_code=6000, year=2022, date=date(2022, 10, 2)), outra)

    de_2026 = _perfil(client)
    de_2022 = _perfil(client, f"/internal/v1/pessoas/2022-{SQ}/")

    assert de_2026["pessoa"]["nome"] == "Pessoa de 2026"
    assert de_2022["pessoa"]["nome"] == "Pessoa de 2022"
    assert len(de_2026["candidaturas"]) == len(de_2022["candidaturas"]) == 1


def test_pessoa_inexistente_da_404_sem_repetir_o_pedido(client, pessoa_simples):
    _perfil(client)  # controle: a rota existe e a pessoa conhecida responde

    resposta = client.get("/internal/v1/pessoas/2026-9999999999/")

    assert resposta.status_code == 404
    assert "9999999999" not in resposta.content.decode()


@pytest.mark.parametrize(
    "ciclo_sq",
    ["2026-abc", "2026-", "-1000000001", "26-1000000001", "2026-1000000000001", "2026_1", "20261"],
)
def test_id_malformado_da_404(client, pessoa_simples, ciclo_sq):
    _perfil(client)  # controle

    resposta = client.get(f"/internal/v1/pessoas/{ciclo_sq}/")

    assert resposta.status_code == 404


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, pessoa_simples, metodo):
    _perfil(client)  # controle

    resposta = getattr(client, metodo)(URL)

    assert resposta.status_code == 405


def test_numero_de_consultas_nao_cresce_com_as_candidaturas(client, run):
    pessoa = _pessoa()
    _candidatura(run, _eleicao(), pessoa)
    _perfil(client)  # controle (e aquece o que o Django guarda em cache)
    with CaptureQueriesContext(connection) as com_uma:
        client.get(URL)

    _candidatura(run, _eleicao(tse_code=6260, round=2, date=date(2026, 10, 25)), pessoa)
    _candidatura(run, _eleicao(tse_code=6261, round=3, date=date(2026, 11, 1)), pessoa)
    with CaptureQueriesContext(connection) as com_tres:
        client.get(URL)

    assert len(com_tres) == len(com_uma)
