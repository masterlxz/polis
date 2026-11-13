"""Normalização de `senado/senadores` em `Senator` e saída da lista (ADR 0028, molde dos ADR 0022 e
0027). Dados sintéticos. O bruto guarda TUDO como texto, como o leitor JSON grava.

Regras: lê a carga mais recente, sem rede; linha inválida ou conflito não gravam nada; upsert pela
chave (código do parlamentar), sem legislatura; nunca apaga. Quem some da carga mais recente fica
com `in_office=False` e `left_list_at` = início da execução que primeiro não o trouxe (a COLETA, não
o fim do mandato); quem volta, volta. Só a carga mais recente mexe nesse estado.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64


def senador(codigo, nome, partido="XYZ", uf="SP"):
    return {
        "CodigoParlamentar": str(codigo),
        "NomeParlamentar": nome,
        "SiglaPartidoParlamentar": partido,
        "UfParlamentar": uf,
    }


ANA = senador(1, "Ana do Senado")
BETO = senador(2, "Beto do Senado", uf="RJ")
CAIO = senador(3, "Caio do Senado", uf="MG")


def modelo():
    """`Senator`, importado só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import Senator

    return Senator


def sen(codigo):
    return modelo().objects.get(senate_id=codigo)


@pytest.fixture
def dataset():
    fonte = Source.objects.create(
        slug="senado",
        name="Senado Federal: Dados Abertos",
        institution="Senado Federal",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="senadores",
        name="Senadores em exercício",
        url="https://example.org/senadores",
        format=Dataset.Format.JSON_SENADO,
        allowed_columns=[
            "CodigoParlamentar",
            "NomeParlamentar",
            "SiglaPartidoParlamentar",
            "UfParlamentar",
        ],
    )


def carga(dataset, linhas, **extra):
    campos = {
        "state": IngestionRun.State.SUCCEEDED,
        "finished_at": timezone.now(),
        "sha256_original": HASH,
        "rows_read": len(linhas),
        "rows_loaded": len(linhas),
        **extra,
    }
    run = IngestionRun.objects.create(dataset=dataset, source_url=dataset.url, **campos)
    RawRecord.objects.bulk_create([RawRecord(run=run, item_name="dados", values=v) for v in linhas])
    return run


def normalizar():
    saida = StringIO()
    call_command("normalize_senado", stdout=saida, stderr=saida)
    return saida.getvalue()


def agora_menos(**atraso):
    return timezone.now() - timedelta(**atraso)


# --- Normalização ------------------------------------------------------------------------------


def test_carga_vira_senadores_com_os_campos_certos(dataset):
    carga(dataset, [ANA, BETO])

    texto = normalizar()

    assert modelo().objects.count() == 2
    ana = sen(1)
    assert (ana.name, ana.party_acronym, ana.state) == ("Ana do Senado", "XYZ", "SP")
    assert ana.in_office is True and ana.left_list_at is None
    assert "criadas 2" in texto


def test_normalizar_de_novo_a_mesma_carga_e_idempotente(dataset):
    carga(dataset, [ANA, BETO])
    normalizar()
    texto = normalizar()

    assert modelo().objects.count() == 2
    assert "criadas 0" in texto and "já existentes 2" in texto


def test_trocar_de_partido_sobrescreve_a_linha_sem_duplicar(dataset):
    carga(dataset, [ANA], started_at=agora_menos(days=1))
    normalizar()
    carga(dataset, [senador(1, "Ana do Senado", partido="ABC")], sha256_original="b" * 64)
    normalizar()

    assert modelo().objects.count() == 1
    assert sen(1).party_acronym == "ABC"


def test_linhas_identicas_viram_uma(dataset):
    carga(dataset, [ANA, ANA])
    normalizar()
    assert modelo().objects.count() == 1


def test_mesmo_codigo_com_dados_diferentes_para_tudo_e_nao_grava_nada(dataset):
    carga(dataset, [ANA, BETO, senador(1, "Outra Pessoa")])

    with pytest.raises(CommandError) as erro:
        normalizar()

    assert modelo().objects.count() == 0
    assert "Outra Pessoa" not in str(erro.value) and "Nada foi gravado" in str(erro.value)


def test_linha_invalida_para_tudo_e_cita_so_o_nome_da_coluna(dataset):
    carga(dataset, [ANA, {**BETO, "UfParlamentar": "SEGREDO"}])

    with pytest.raises(CommandError) as erro:
        normalizar()

    assert modelo().objects.count() == 0
    assert "UfParlamentar" in str(erro.value) and "SEGREDO" not in str(erro.value)


def test_sem_carga_com_linhas_o_comando_avisa(dataset):
    with pytest.raises(CommandError):
        normalizar()


def test_o_agendador_encadeia_a_normalizacao_do_senado():
    assert settings.NORMALIZERS["senado/senadores"] == (
        "apps.legislature.senate_normalization.normalize_latest"
    )


def test_normalize_latest_nao_repete_carga_ja_normalizada(dataset):
    from apps.legislature import senate_normalization

    carga(dataset, [ANA])
    assert senate_normalization.normalize_latest(dataset) is not None, "controle"
    assert senate_normalization.normalize_latest(dataset) is None


# --- Saída da lista ----------------------------------------------------------------------------


@pytest.fixture
def ana_beto_caio_e_depois_so_ana_e_beto(dataset):
    """Carga 1 com 3 senadores (ontem) e carga 2 só com Ana e Beto (3 h atrás)."""
    primeira = carga(dataset, [ANA, BETO, CAIO], started_at=agora_menos(days=1))
    normalizar()
    for codigo in (1, 2, 3):  # controle: todos entram em exercício
        assert sen(codigo).in_office is True
        assert sen(codigo).left_list_at is None
    segunda = carga(dataset, [ANA, BETO], started_at=agora_menos(hours=3), sha256_original="b" * 64)
    normalizar()
    return primeira, segunda


def test_senador_que_some_da_carga_seguinte_sai_do_exercicio_com_o_inicio_daquela_execucao(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    _, segunda = ana_beto_caio_e_depois_so_ana_e_beto
    assert sen(3).in_office is False
    assert sen(3).left_list_at == segunda.started_at


def test_quem_continua_na_lista_continua_em_exercicio(ana_beto_caio_e_depois_so_ana_e_beto):
    for codigo in (1, 2):
        assert sen(codigo).in_office is True
        assert sen(codigo).left_list_at is None


def test_normalizar_de_novo_nao_muda_o_instante_da_saida(ana_beto_caio_e_depois_so_ana_e_beto):
    antes = sen(3).left_list_at
    assert antes is not None  # controle
    normalizar()
    assert sen(3).left_list_at == antes


def test_sair_nao_apaga_nada_e_guarda_a_ultima_execucao_que_o_viu(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    primeira, _ = ana_beto_caio_e_depois_so_ana_e_beto
    assert modelo().objects.count() == 3
    assert sen(3).ingestion_run == primeira


def test_quem_volta_para_a_lista_volta_ao_exercicio_e_o_instante_some(
    dataset, ana_beto_caio_e_depois_so_ana_e_beto
):
    assert sen(3).in_office is False  # controle
    carga(dataset, [ANA, BETO, CAIO], sha256_original="c" * 64)
    normalizar()
    assert sen(3).in_office is True
    assert sen(3).left_list_at is None


def test_sair_de_novo_grava_um_instante_novo(dataset, ana_beto_caio_e_depois_so_ana_e_beto):
    primeiro_instante = sen(3).left_list_at
    carga(dataset, [ANA, BETO, CAIO], started_at=agora_menos(hours=2), sha256_original="c" * 64)
    normalizar()
    quarta = carga(dataset, [ANA, BETO], started_at=agora_menos(hours=1), sha256_original="d" * 64)
    normalizar()
    assert sen(3).in_office is False
    assert sen(3).left_list_at == quarta.started_at
    assert sen(3).left_list_at != primeiro_instante


def test_carga_que_falhou_nao_marca_ninguem(dataset):
    carga(dataset, [ANA, BETO])
    normalizar()
    IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.FAILED,
        error_code=IngestionRun.ErrorCode.DOWNLOAD,
        finished_at=timezone.now(),
    )
    normalizar()
    assert modelo().objects.filter(in_office=False).count() == 0


def test_arquivo_igual_com_zero_linhas_nao_marca_ninguem(dataset):
    carga(dataset, [ANA, BETO])
    normalizar()
    carga(dataset, [])
    normalizar()
    assert modelo().objects.filter(in_office=False).count() == 0


def test_normalizar_a_mao_uma_carga_antiga_nao_mexe_no_estado(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    from apps.legislature import senate_normalization

    primeira, _ = ana_beto_caio_e_depois_so_ana_e_beto
    instante = sen(3).left_list_at
    senate_normalization.normalize(primeira)
    assert sen(3).in_office is False
    assert sen(3).left_list_at == instante
    assert sen(1).in_office is True


def test_senador_criado_direto_no_banco_nasce_em_exercicio(dataset):
    run = carga(dataset, [ANA])
    novo = modelo().objects.create(senate_id=9, name="Novo", state="SP", ingestion_run=run)
    assert novo.in_office is True
    assert novo.left_list_at is None


def test_o_mesmo_codigo_nao_se_repete_na_tabela(dataset):
    from django.db import IntegrityError, transaction

    run = carga(dataset, [ANA])
    modelo().objects.create(senate_id=9, name="Um", state="SP", ingestion_run=run)
    with pytest.raises(IntegrityError), transaction.atomic():
        modelo().objects.create(senate_id=9, name="Dois", state="SP", ingestion_run=run)
