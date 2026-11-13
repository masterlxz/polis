"""Saída do exercício do deputado da Câmara (ADR 0022 e 0027). Dados sintéticos.

A lista `camara/deputados` é de deputados EM EXERCÍCIO. Quem some dela da carga mais recente fica
com `in_office=False` e `left_list_at` = início da execução que primeiro não o trouxe (a data da
COLETA, não do mandato: a lista não diz o motivo nem a data real). Nunca apaga. Quem volta à lista
volta a `in_office=True` e `left_list_at` limpo. Só a carga mais recente mexe nesse estado: falha,
"arquivo igual" e normalização manual de carga velha não marcam nem desmarcam ninguém.
"""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.sources.catalog import DATASETS
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64


def deputado(id, nome, legislatura=57):
    return {
        "id": id,
        "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id}",
        "nome": nome,
        "siglaPartido": "XYZ",
        "siglaUf": "SP",
        "idLegislatura": legislatura,
    }


ANA = deputado(1, "Ana da Câmara")
BETO = deputado(2, "Beto da Câmara")
CAIO = deputado(3, "Caio da Câmara")


def modelo():
    """`Deputy`, importado só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import Deputy

    return Deputy


def deputy(camara_id):
    return modelo().objects.get(camara_id=camara_id)


@pytest.fixture
def dataset():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="deputados",
        name="Deputados em exercício",
        url="https://example.org/deputados",
        format=Dataset.Format.JSON,
        allowed_columns=DATASETS[-1]["allowed_columns"],
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
    RawRecord.objects.bulk_create(
        [RawRecord(run=run, item_name="deputados.json", values=v) for v in linhas]
    )
    return run


def normalizar():
    saida = StringIO()
    call_command("normalize_camara", stdout=saida, stderr=saida)
    return saida.getvalue()


def agora_menos(**atraso):
    return timezone.now() - timedelta(**atraso)


@pytest.fixture
def ana_beto_caio_e_depois_so_ana_e_beto(dataset):
    """Carga 1 com 3 deputados (ontem) e carga 2 só com Ana e Beto (3 h atrás)."""
    primeira = carga(dataset, [ANA, BETO, CAIO], started_at=agora_menos(days=1))
    normalizar()
    for camara_id in (1, 2, 3):  # controle: todos entram em exercício
        assert deputy(camara_id).in_office is True
        assert deputy(camara_id).left_list_at is None
    segunda = carga(dataset, [ANA, BETO], started_at=agora_menos(hours=3))
    normalizar()
    return primeira, segunda


# --- Sair da lista ---


def test_deputado_que_some_da_carga_seguinte_sai_do_exercicio_com_o_inicio_daquela_execucao(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    _, segunda = ana_beto_caio_e_depois_so_ana_e_beto
    caio = deputy(3)
    assert caio.in_office is False
    assert caio.left_list_at == segunda.started_at


def test_quem_continua_na_lista_continua_em_exercicio(ana_beto_caio_e_depois_so_ana_e_beto):
    for camara_id in (1, 2):
        assert deputy(camara_id).in_office is True
        assert deputy(camara_id).left_list_at is None


def test_normalizar_de_novo_a_mesma_carga_nao_muda_o_instante_da_saida(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    antes = deputy(3).left_list_at
    assert antes is not None  # controle
    normalizar()
    assert deputy(3).left_list_at == antes


def test_sair_da_lista_nao_apaga_nada_e_guarda_a_ultima_execucao_que_o_viu(
    ana_beto_caio_e_depois_so_ana_e_beto,
):
    primeira, _ = ana_beto_caio_e_depois_so_ana_e_beto
    assert modelo().objects.count() == 3
    assert deputy(3).ingestion_run == primeira


# --- Voltar e sair de novo ---


def test_quem_volta_para_a_lista_volta_ao_exercicio_e_o_instante_some(
    dataset, ana_beto_caio_e_depois_so_ana_e_beto
):
    assert deputy(3).in_office is False  # controle
    carga(dataset, [ANA, BETO, CAIO])
    normalizar()
    assert deputy(3).in_office is True
    assert deputy(3).left_list_at is None


def test_sair_de_novo_grava_um_instante_novo(dataset, ana_beto_caio_e_depois_so_ana_e_beto):
    primeiro_instante = deputy(3).left_list_at
    carga(dataset, [ANA, BETO, CAIO], started_at=agora_menos(hours=2))
    normalizar()
    quarta = carga(dataset, [ANA, BETO], started_at=agora_menos(hours=1))
    normalizar()
    assert deputy(3).in_office is False
    assert deputy(3).left_list_at == quarta.started_at
    assert deputy(3).left_list_at != primeiro_instante


# --- Quando NÃO marca ninguém ---


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
    from apps.legislature import normalization

    primeira, _ = ana_beto_caio_e_depois_so_ana_e_beto
    instante = deputy(3).left_list_at
    normalization.normalize(primeira)
    assert deputy(3).in_office is False
    assert deputy(3).left_list_at == instante
    assert deputy(1).in_office is True


# --- Troca de legislatura (documentada: a lista passa a ser da legislatura nova) ---


def test_na_troca_de_legislatura_a_lista_nova_tira_os_deputados_da_anterior(dataset):
    carga(dataset, [deputado(1, "Ana da Câmara", 57), deputado(2, "Beto da Câmara", 57)])
    normalizar()
    carga(dataset, [deputado(1, "Ana da Câmara", 58)])
    normalizar()
    assert modelo().objects.get(legislature_id=58, camara_id=1).in_office is True
    assert modelo().objects.get(legislature_id=57, camara_id=1).in_office is False
    assert modelo().objects.get(legislature_id=57, camara_id=2).in_office is False


# --- O que a API interna mostra ---


def _perfil(client, legislatura, camara_id):
    resposta = client.get(f"/internal/v1/deputados/{legislatura}-{camara_id}/")
    assert resposta.status_code == 200, "controle: esperava 200"
    return resposta.json()["deputado"]


def test_api_mostra_em_exercicio_e_nenhuma_saida_para_quem_esta_na_lista(
    client, ana_beto_caio_e_depois_so_ana_e_beto
):
    perfil = _perfil(client, 57, 1)
    assert perfil["em_exercicio"] is True
    assert perfil["saiu_da_lista_em"] is None


def test_api_mostra_fora_do_exercicio_e_o_instante_da_coleta_que_o_perdeu(
    client, ana_beto_caio_e_depois_so_ana_e_beto
):
    _, segunda = ana_beto_caio_e_depois_so_ana_e_beto
    perfil = _perfil(client, 57, 3)
    assert perfil["em_exercicio"] is False
    assert perfil["saiu_da_lista_em"] == segunda.started_at.isoformat()


def test_deputado_criado_direto_no_banco_nasce_em_exercicio(dataset):
    run = carga(dataset, [ANA])
    novo = modelo().objects.create(
        legislature_id=57, camara_id=9, name="Novo", state="SP", ingestion_run=run
    )
    assert novo.in_office is True
    assert novo.left_list_at is None
