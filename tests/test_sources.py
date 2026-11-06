import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, Source

HASH_OK = "a" * 64

pytestmark = pytest.mark.django_db


def make_source(slug="tse", **kwargs):
    return Source.objects.create(
        slug=slug,
        name=f"Fonte {slug}",
        institution="Instituição",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
        **kwargs,
    )


def make_dataset(source=None, slug="consulta-cand", **kwargs):
    kwargs.setdefault("allowed_columns", ["SQ_CANDIDATO", "NM_URNA_CANDIDATO"])
    return Dataset.objects.create(
        source=source or make_source(),
        slug=slug,
        name="Consulta de candidatos",
        url="https://example.org/consulta_cand.zip",
        format=Dataset.Format.ZIP_CSV,
        **kwargs,
    )


def make_run(dataset=None, **kwargs):
    return IngestionRun.objects.create(
        dataset=dataset or make_dataset(),
        source_url="https://example.org/consulta_cand.zip",
        **kwargs,
    )


def succeeded_run_kwargs(**overrides):
    kwargs = {
        "state": IngestionRun.State.SUCCEEDED,
        "finished_at": timezone.now(),
        "sha256_original": HASH_OK,
        "rows_read": 10,
        "rows_loaded": 10,
    }
    kwargs.update(overrides)
    return kwargs


# --- Dataset: allowlist declarada (ADR 0005, decisão 1) ---


def test_conjunto_habilitado_com_lista_vazia_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(enabled=True, allowed_columns=[])


def test_conjunto_nao_habilitado_com_lista_vazia_e_aceito():
    dataset = make_dataset(enabled=False, allowed_columns=[])
    assert dataset.pk is not None


def test_conjunto_habilitado_com_lista_preenchida_e_aceito():
    dataset = make_dataset(enabled=True)
    assert dataset.enabled is True


def test_coluna_interna_fora_das_permitidas_e_recusada():
    dataset = make_dataset(internal_columns=["DT_NASCIMENTO"])
    with pytest.raises(ValidationError):
        dataset.full_clean()


def test_coluna_interna_dentro_das_permitidas_e_aceita():
    dataset = make_dataset(
        allowed_columns=["SQ_CANDIDATO", "DT_NASCIMENTO"],
        internal_columns=["DT_NASCIMENTO"],
    )
    dataset.full_clean()


def test_slug_com_espaco_e_recusado():
    dataset = make_dataset(slug="com espaco")
    with pytest.raises(ValidationError):
        dataset.full_clean()


def test_mesmo_slug_na_mesma_fonte_e_recusado():
    source = make_source()
    make_dataset(source=source, slug="votos")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(source=source, slug="votos")


def test_mesmo_slug_em_fontes_diferentes_e_aceito():
    make_dataset(source=make_source("camara"), slug="votos")
    make_dataset(source=make_source("senado"), slug="votos")


# --- PROTECT: o histórico não some (PRD §9.1) ---


def test_apagar_fonte_com_conjuntos_e_recusado():
    dataset = make_dataset()
    with pytest.raises(ProtectedError):
        dataset.source.delete()


def test_apagar_conjunto_com_execucoes_e_recusado():
    run = make_run()
    with pytest.raises(ProtectedError):
        run.dataset.delete()


# --- IngestionRun: restrições do banco ---


def test_execucao_em_andamento_e_aceita_sem_hash():
    run = make_run()
    assert run.state == IngestionRun.State.RUNNING
    assert run.sha256_original == ""


def test_execucao_com_sucesso_valida_e_aceita():
    run = make_run(**succeeded_run_kwargs())
    assert run.pk is not None


@pytest.mark.parametrize(
    "hash_invalido",
    ["", "a" * 63, "a" * 65, "A" * 64, "g" * 64, ("a" * 63) + " "],
    ids=["vazio", "curto", "longo", "maiusculo", "nao-hex", "espaco"],
)
def test_execucao_com_sucesso_exige_sha256_valido(hash_invalido):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_run(**succeeded_run_kwargs(sha256_original=hash_invalido))


def test_execucao_com_sucesso_exige_data_de_fim():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_run(**succeeded_run_kwargs(finished_at=None))


def test_execucao_em_andamento_nao_pode_ter_data_de_fim():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_run(finished_at=timezone.now())


def test_linhas_gravadas_nao_passam_das_lidas():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_run(**succeeded_run_kwargs(rows_read=5, rows_loaded=6))


def test_execucao_com_falha_exige_codigo_de_erro():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_run(state=IngestionRun.State.FAILED, finished_at=timezone.now())


def test_execucao_com_falha_e_codigo_de_erro_e_aceita():
    run = make_run(
        state=IngestionRun.State.FAILED,
        finished_at=timezone.now(),
        error_code=IngestionRun.ErrorCode.SCHEMA,
    )
    assert run.error_code == "schema"


def test_codigo_de_erro_fora_do_conjunto_fechado_e_recusado():
    run = make_run(
        state=IngestionRun.State.FAILED,
        finished_at=timezone.now(),
        error_code="Traceback: linha com 123.456.789-09",
    )
    with pytest.raises(ValidationError):
        run.full_clean()


def test_execucao_nao_tem_campo_de_texto_livre_de_erro():
    nomes = {campo.name for campo in IngestionRun._meta.get_fields()}
    assert not nomes & {"error_message", "error", "traceback", "message", "details"}


# --- IngestionRun: imutável depois de concluída ---


def test_execucao_em_andamento_pode_ser_concluida():
    run = make_run()
    for campo, valor in succeeded_run_kwargs().items():
        setattr(run, campo, valor)
    run.save()
    run.refresh_from_db()
    assert run.state == IngestionRun.State.SUCCEEDED


def test_execucao_concluida_nao_pode_ser_alterada():
    run = make_run(**succeeded_run_kwargs())
    run.rows_read = 999
    with pytest.raises(ValueError, match="imutável"):
        run.save()
    run.refresh_from_db()
    assert run.rows_read == 10


def test_execucao_com_falha_tambem_nao_pode_ser_alterada():
    run = make_run(
        state=IngestionRun.State.FAILED,
        finished_at=timezone.now(),
        error_code=IngestionRun.ErrorCode.DOWNLOAD,
    )
    run.error_code = IngestionRun.ErrorCode.OTHER
    with pytest.raises(ValueError, match="imutável"):
        run.save()


# --- Admin ---


def test_admin_lista_execucoes_sem_botao_de_adicionar(admin_client):
    make_run()
    resposta = admin_client.get("/admin/sources/ingestionrun/")
    assert resposta.status_code == 200
    assert "/admin/sources/ingestionrun/add/" not in resposta.content.decode()


def test_admin_nao_deixa_adicionar_execucao(admin_client):
    assert admin_client.get("/admin/sources/ingestionrun/add/").status_code == 403


def test_admin_nao_deixa_apagar_execucao(admin_client):
    run = make_run()
    resposta = admin_client.get(f"/admin/sources/ingestionrun/{run.pk}/delete/")
    assert resposta.status_code == 403


def test_admin_mostra_execucao_somente_leitura(admin_client):
    run = make_run(**succeeded_run_kwargs())
    resposta = admin_client.post(
        f"/admin/sources/ingestionrun/{run.pk}/change/", {"rows_read": 999}
    )
    run.refresh_from_db()
    assert resposta.status_code in (200, 403)
    assert run.rows_read == 10


def test_admin_edita_fonte_e_conjunto(admin_client):
    dataset = make_dataset()
    assert admin_client.get("/admin/sources/source/").status_code == 200
    assert admin_client.get(f"/admin/sources/dataset/{dataset.pk}/change/").status_code == 200
