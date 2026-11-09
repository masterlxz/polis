"""Modelos de eleição, pessoa e candidatura (normalização do TSE, ADR 0005 e ADR 0009).

Dados todos sintéticos. As restrições aqui refletem o que foi medido em `consulta-cand-2026`
(Sessão 39): a candidatura é única por eleição+turno e SQ_CANDIDATO, e o mesmo SQ aparece nos
dois turnos, então a pessoa é única por ciclo e SQ_CANDIDATO.
"""

from datetime import date

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.elections.models import Candidacy, Election, Person
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

SQ = 1_000_000_001
NOME_SOCIAL_SECRETO = "Nome Social Interno de Teste"


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
    campos = {"cycle_year": 2026, "tse_candidate_id": SQ, "public_name": "Fulano da Urna"}
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


# --- Election ---


def test_eleicao_e_unica_por_codigo_e_turno():
    _eleicao()
    with pytest.raises(IntegrityError), transaction.atomic():
        _eleicao()


def test_mesmo_codigo_em_outro_turno_e_outra_eleicao():
    _eleicao(round=1)
    assert _eleicao(round=2).pk is not None


# --- Person ---


def test_pessoa_e_unica_por_ciclo_e_id_do_tse():
    _pessoa()
    with pytest.raises(IntegrityError), transaction.atomic():
        _pessoa()


def test_mesmo_id_em_outro_ciclo_nao_e_a_mesma_pessoa():
    _pessoa(cycle_year=2022)
    assert _pessoa(cycle_year=2026).pk is not None


def test_nome_publico_vazio_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        _pessoa(public_name="")


def test_str_da_pessoa_e_o_nome_publico_e_nunca_o_social():
    pessoa = _pessoa(social_name=NOME_SOCIAL_SECRETO)
    assert str(pessoa) == "Fulano da Urna"
    assert NOME_SOCIAL_SECRETO not in str(pessoa)


# --- Candidacy ---


def test_mesma_pessoa_nos_dois_turnos_tem_uma_pessoa_e_duas_candidaturas(run):
    pessoa = _pessoa()
    primeira = _candidatura(run, _eleicao(tse_code=6259, round=1), pessoa)
    segunda = _candidatura(run, _eleicao(tse_code=6260, round=2), pessoa)
    assert Person.objects.count() == 1
    assert set(pessoa.candidacies.all()) == {primeira, segunda}


def test_candidatura_e_unica_por_eleicao_e_pessoa(run):
    eleicao, pessoa = _eleicao(), _pessoa()
    _candidatura(run, eleicao, pessoa)
    with pytest.raises(IntegrityError), transaction.atomic():
        _candidatura(run, eleicao, pessoa)


def test_candidatura_exige_a_execucao_de_origem(run):
    with pytest.raises(IntegrityError), transaction.atomic():
        _candidatura(None, _eleicao(), _pessoa())


def test_campos_que_o_tse_deixa_ausentes_sao_aceitos(run):
    candidatura = _candidatura(
        run,
        _eleicao(),
        _pessoa(),
        federation_acronym="",
        federation_name="",
        status_code=None,
        status_name="",
        result_code=None,
        result_name="",
    )
    candidatura.refresh_from_db()
    assert candidatura.status_code is None and candidatura.result_code is None


def test_nao_apaga_eleicao_pessoa_nem_execucao_com_candidatura(run):
    eleicao, pessoa = _eleicao(), _pessoa()
    _candidatura(run, eleicao, pessoa)
    for objeto in (eleicao, pessoa, run):
        with pytest.raises(ProtectedError):
            objeto.delete()


# --- Admin e migrações ---


def test_admin_lista_candidaturas_e_pessoas_sem_o_nome_social(admin_client, run):
    _candidatura(run, _eleicao(), _pessoa(social_name=NOME_SOCIAL_SECRETO))
    for caminho in ("/admin/elections/candidacy/", "/admin/elections/person/"):
        resposta = admin_client.get(caminho)
        assert resposta.status_code == 200, caminho
        assert NOME_SOCIAL_SECRETO not in resposta.content.decode(), caminho


def test_admin_nao_deixa_adicionar_nem_apagar_dado_normalizado(admin_client, run):
    candidatura = _candidatura(run, _eleicao(), _pessoa())
    assert admin_client.get("/admin/elections/candidacy/add/").status_code == 403
    assert admin_client.get("/admin/elections/person/add/").status_code == 403
    apagar = f"/admin/elections/candidacy/{candidatura.pk}/delete/"
    assert admin_client.get(apagar).status_code == 403


def test_nao_ha_migracao_pendente():
    call_command("makemigrations", "--check", "--dry-run")
