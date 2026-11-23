"""Fim de caminho das rotas internas: `.../5895/\\n` não pode ser outra URL do mesmo recurso.

Todas as rotas de `/internal/v1/` são `re_path` terminados em `/$`. O `$` do `re` do Python casa
também ANTES de um `\\n` final, então, se o resolvedor usasse `regex.search`, o caminho
`/internal/v1/senadores/5895/\\n` (enviado como `/internal/v1/senadores/5895/%0A`) casaria e seria
uma segunda URL para o mesmo recurso (cache, log e regras de borda que olham o caminho passariam a
ver dois). Cada caso pede antes um 200 de controle na URL normal, com o registro existente: sem
isso, um 404 poderia ser só "não há registro". O caso com `%0A` usa o MESMO registro do controle,
e a exigência de zero consultas separa o 404 do resolvedor (não chegou à view) do 404 da view
(chegou, consultou e não achou).

Um 404 sem consulta, sozinho, não prova que o `\\n` chegou ao resolvedor (o client ou um
middleware poderia tê-lo descartado). Por isso o teste do client afirma também, na resposta, que
o `path_info` da requisição termina no `\\n`; e `test_o_resolvedor_recusa_o_caminho_com_n_final`
chama `resolve()` direto, sem client nem middleware (APPEND_SLASH, CommonMiddleware).

O `$` do Python só casa antes de UM `\\n` final: `\\r\\n` nunca casou, nem com `search`. Os casos
`%0D%0A` não detectam esse risco; só guardam contra uma futura normalização que apare espaços.
"""

from datetime import UTC, date, datetime

import pytest
from django.urls import Resolver404, resolve
from django.utils import timezone

from apps.elections.models import Candidacy, Election, Person
from apps.legislature.models import Deputy, SenateVoting, Senator
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LEGISLATURA = 57
ID_CAMARA = 204554
CODIGO_SENADOR = 5895
CODIGO_VOTACAO = 7001
CICLO = 2026
SQ = 1_000_000_001

# (nome do caso, URL normal que devolve 200 com os registros de `registros`)
ROTAS = [
    ("deputado", f"/internal/v1/deputados/{LEGISLATURA}-{ID_CAMARA}/"),
    ("senador", f"/internal/v1/senadores/{CODIGO_SENADOR}/"),
    ("votos-do-senador", f"/internal/v1/senadores/{CODIGO_SENADOR}/votos/"),
    ("votacao-do-senado", f"/internal/v1/senado/votacoes/{CODIGO_VOTACAO}/"),
    ("pessoa", f"/internal/v1/pessoas/{CICLO}-{SQ}/"),
]

# (final enviado na URL, o que o servidor entrega ao resolvedor depois de decodificar).
# `%0A` é o `\n` que o `$` aceitaria; `%0D%0A` é `\r\n`, que o `$` nunca aceitou (só guarda).
FINAIS = [("%0A", "\n"), ("%0D%0A", "\r\n")]


@pytest.fixture
def registros():
    """Um registro de cada tipo, com os identificadores das URLs de `ROTAS`."""
    source = Source.objects.create(
        slug="teste",
        name="Fonte de teste",
        institution="Instituição de teste",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    dataset = Dataset.objects.create(
        source=source,
        slug="conjunto-de-teste",
        name="Conjunto de teste",
        url="https://example.org/dados.json",
        format=Dataset.Format.JSON,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Decisão do dono de teste.",
    )
    run = IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        started_at=datetime(2026, 11, 13, 9, 0, tzinfo=UTC),
    )
    Deputy.objects.create(
        legislature_id=LEGISLATURA,
        camara_id=ID_CAMARA,
        name="Ana da Câmara",
        party_acronym="XYZ",
        state="SP",
        ingestion_run=run,
    )
    Senator.objects.create(
        senate_id=CODIGO_SENADOR,
        name="Ana do Senado",
        party_acronym="XYZ",
        state="SP",
        ingestion_run=run,
    )
    SenateVoting.objects.create(
        session_voting_code=CODIGO_VOTACAO,
        voted_on=date(2026, 11, 12),
        type_acronym="PL",
        number="1",
        year=2026,
        identification="PL 1/2026",
        summary="Dispõe sobre um assunto de teste.",
        result="A",
        secret=False,
        process_id=100,
        matter_id=200,
        ingestion_run=run,
    )
    eleicao = Election.objects.create(
        tse_code=6259,
        round=1,
        year=2026,
        kind_code=2,
        kind_name="Eleição Ordinária",
        description="Eleições Gerais Estaduais 2026",
        date=date(2026, 10, 4),
    )
    pessoa = Person.objects.create(
        cycle_year=CICLO, tse_candidate_id=SQ, public_name="Fulano da Urna"
    )
    Candidacy.objects.create(
        election=eleicao,
        person=pessoa,
        ballot_number=12345,
        office_code=6,
        office_name="DEPUTADO FEDERAL",
        scope="ESTADUAL",
        state="SP",
        electoral_unit_code="SP",
        electoral_unit_name="SÃO PAULO",
        party_number=12,
        party_acronym="XYZ",
        party_name="Partido de Teste",
        ingestion_run=run,
        source_generated_at=timezone.now(),
    )


@pytest.mark.parametrize("final, decodificado", FINAIS)
@pytest.mark.parametrize("url", [url for _, url in ROTAS], ids=[nome for nome, _ in ROTAS])
def test_quebra_de_linha_no_fim_do_caminho_da_404_sem_consultar_o_banco(
    client, registros, url, final, decodificado, django_assert_num_queries
):
    controle = client.get(url)
    assert controle.status_code == 200, f"controle: esperava 200 em {url}"

    with django_assert_num_queries(0):
        resposta = client.get(url + final)

    # Premissa: o final chegou à requisição (não foi descartado pelo client nem por middleware).
    assert resposta.wsgi_request.path_info == url + decodificado
    assert resposta.status_code == 404, f"{url}{final} devia ser 404, veio {resposta.status_code}"


@pytest.mark.parametrize("url", [url for _, url in ROTAS], ids=[nome for nome, _ in ROTAS])
def test_o_resolvedor_recusa_o_caminho_com_n_final(url):
    """Direto no resolvedor, sem client nem middleware: o `\\n` final não casa nenhuma rota."""
    resolve(url)  # controle positivo: a URL normal resolve (levantaria Resolver404)

    with pytest.raises(Resolver404):
        resolve(url + "\n")
