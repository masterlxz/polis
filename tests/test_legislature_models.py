"""Modelo `Deputy`, constraints, admin só de leitura e migração em dia (Sessão 54)."""

import pytest
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db


@pytest.fixture
def run():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    dataset = Dataset.objects.create(
        source=fonte,
        slug="deputados",
        name="Deputados em exercício",
        url="https://example.org/deputados",
        format=Dataset.Format.JSON,
    )
    return IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.SUCCEEDED,
        finished_at=timezone.now(),
        sha256_original="a" * 64,
    )


def deputado(run, **mudancas):
    from apps.legislature.models import Deputy

    campos = {
        "legislature_id": 57,
        "camara_id": 1,
        "name": "Ana da Câmara",
        "party_acronym": "XYZ",
        "state": "SP",
        "ingestion_run": run,
        **mudancas,
    }
    return Deputy.objects.create(**campos)


def test_str_mostra_so_o_nome_parlamentar(run):
    assert str(deputado(run)) == "Ana da Câmara"


def test_mesma_legislatura_e_id_da_camara_nao_se_repetem(run):
    deputado(run)
    with pytest.raises(IntegrityError), transaction.atomic():
        deputado(run, name="Outro")


def test_mesmo_id_em_outra_legislatura_e_permitido(run):
    deputado(run)
    deputado(run, legislature_id=58)


def test_nome_vazio_e_barrado_pelo_banco(run):
    with pytest.raises(IntegrityError), transaction.atomic():
        deputado(run, name="")


def test_execucao_de_origem_com_deputado_nao_pode_ser_apagada(run):
    from django.db.models import ProtectedError

    deputado(run)
    with pytest.raises(ProtectedError):
        run.delete()


def test_admin_lista_deputados_e_so_deixa_ler(admin_client, run):
    ana = deputado(run)
    resposta = admin_client.get("/admin/legislature/deputy/")
    assert resposta.status_code == 200
    assert "Ana da Câmara" in resposta.content.decode()
    assert admin_client.get("/admin/legislature/deputy/add/").status_code == 403
    assert admin_client.get(f"/admin/legislature/deputy/{ana.pk}/delete/").status_code == 403
    assert admin_client.post(f"/admin/legislature/deputy/{ana.pk}/change/", {}).status_code == 403


def test_nao_ha_migracao_pendente():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
