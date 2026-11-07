import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import DataError, IntegrityError, transaction
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
    if kwargs.get("enabled"):
        # Os testes que não tratam do portão de licença habilitam com licença válida,
        # para que a falha deles seja só da regra que testam.
        base = kwargs.setdefault("license_basis", Dataset.LicenseBasis.DECLARED)
        if base == Dataset.LicenseBasis.DECLARED:
            kwargs.setdefault("license_id", "cc-by")
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


# --- Dataset: portão de licença por conjunto (ADR 0008, decisão 1) ---


def test_conjunto_habilitado_sem_base_de_licenca_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(enabled=True, license_basis=Dataset.LicenseBasis.NONE)


def test_conjunto_habilitado_com_licenca_declarada_e_aceito():
    dataset = make_dataset(
        enabled=True,
        license_basis=Dataset.LicenseBasis.DECLARED,
        license_id="cc-by",
        license_url="http://www.opendefinition.org/licenses/cc-by",
    )
    assert dataset.enabled is True


def test_conjunto_habilitado_com_licenca_declarada_sem_identificador_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(enabled=True, license_basis=Dataset.LicenseBasis.DECLARED, license_id="")


def test_conjunto_habilitado_por_decisao_do_dono_com_justificativa_e_aceito():
    dataset = make_dataset(
        enabled=True,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Fonte não declara licença; dono decidiu coletar em 2026-11-07.",
    )
    assert dataset.license_id == ""


def test_conjunto_habilitado_por_decisao_do_dono_sem_justificativa_e_recusado():
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(
            enabled=True,
            license_basis=Dataset.LicenseBasis.OWNER_DECISION,
            license_justification="",
        )


def test_conjunto_sem_licenca_nao_habilitado_e_aceito():
    dataset = make_dataset(enabled=False)
    assert dataset.license_basis == Dataset.LicenseBasis.NONE


def test_licenca_na_fonte_nao_habilita_o_conjunto():
    fonte = make_source(license_note="CC BY nos metadados do portal")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(source=fonte, enabled=True, license_basis=Dataset.LicenseBasis.NONE)


def test_validacao_do_formulario_recusa_habilitar_sem_licenca():
    dataset = make_dataset(enabled=False)
    dataset.enabled = True
    with pytest.raises(ValidationError) as erro:
        dataset.full_clean()
    assert "license_basis" in erro.value.message_dict


def test_validacao_do_formulario_recusa_justificativa_so_com_espacos():
    dataset = make_dataset(
        enabled=False,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="   ",
    )
    dataset.enabled = True
    with pytest.raises(ValidationError) as erro:
        dataset.full_clean()
    assert "license_justification" in erro.value.message_dict


def test_base_de_licenca_fora_do_conjunto_fechado_e_recusada():
    dataset = make_dataset(license_basis="qualquer-coisa")
    with pytest.raises(ValidationError):
        dataset.full_clean()


# --- Migrações: o modelo e as migrações não se afastam ---


def test_nao_ha_migracao_pendente():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


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
    # Hash longo demais é barrado pelo tipo da coluna (DataError); os demais, pela restrição.
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
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


@pytest.mark.parametrize("codigo", ["blocked", "license"])
def test_execucao_com_falha_aceita_codigos_de_bloqueio_e_de_licenca(codigo):
    run = make_run(
        state=IngestionRun.State.FAILED,
        finished_at=timezone.now(),
        error_code=codigo,
    )
    run.full_clean()
    assert run.error_code == codigo


def test_codigo_de_erro_fora_do_conjunto_fechado_e_recusado():
    run = IngestionRun(
        dataset=make_dataset(),
        source_url="https://example.org/consulta_cand.zip",
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


def test_admin_lista_conjuntos_com_a_base_de_licenca(admin_client):
    make_dataset(enabled=True, license_basis=Dataset.LicenseBasis.DECLARED, license_id="cc-by")
    resposta = admin_client.get("/admin/sources/dataset/")
    assert resposta.status_code == 200
    assert "Declarada pela fonte" in resposta.content.decode()


def test_admin_edita_fonte_e_conjunto(admin_client):
    dataset = make_dataset()
    assert admin_client.get("/admin/sources/source/").status_code == 200
    assert admin_client.get(f"/admin/sources/dataset/{dataset.pk}/change/").status_code == 200
