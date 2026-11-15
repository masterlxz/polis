"""Lista de conjuntos de dados no admin como painel de fontes (monitoramento da Etapa 0).

Cada linha mostra a última coleta bem-sucedida, o resultado da última execução e a situação
(`apps/sources/freshness.py`); o filtro `?situacao=` separa os conjuntos. Dados sintéticos. O que
mais importa: a situação mostrada é a da regra (não uma conta repetida no admin), o filtro e a
coluna concordam, e o número de consultas não cresce com o número de conjuntos.
"""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LISTA = "admin:sources_dataset_changelist"
MENSAGEM_DA_RECUSA = "Normalização recusada: linhas inválidas: 2; colunas: id (2). Nada gravado."


@pytest.fixture
def fonte():
    return Source.objects.create(
        slug="fonte",
        name="Fonte de teste",
        institution="Instituição",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )


def _conjunto(fonte, slug, **extra):
    campos = {
        "source": fonte,
        "slug": slug,
        "name": f"Conjunto {slug}",
        "url": f"https://example.org/{slug}.json",
        "format": Dataset.Format.JSON,
        "enabled": True,
        "allowed_columns": ["a"],
        "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
        "license_justification": "Decisão do dono de teste.",
        "schedule_interval_hours": 24,
        **extra,
    }
    return Dataset.objects.create(**campos)


def _execucao(conjunto, estado, ha_horas, **extra):
    # O banco exige hash na execução concluída com sucesso e código de erro na que falhou.
    if estado == IngestionRun.State.SUCCEEDED:
        extra.setdefault("sha256_original", "a" * 64)
    if estado == IngestionRun.State.FAILED:
        extra.setdefault("error_code", IngestionRun.ErrorCode.DOWNLOAD)
    fim = timezone.now() - timedelta(hours=ha_horas)
    return IngestionRun.objects.create(
        dataset=conjunto,
        source_url=conjunto.url,
        state=estado,
        started_at=fim - timedelta(minutes=1),
        finished_at=fim,
        **extra,
    )


def _html(admin_client, **consulta):
    resposta = admin_client.get(reverse(LISTA), consulta)
    assert resposta.status_code == 200, "controle: a lista do admin precisa abrir"
    return resposta.content.decode()


def _conjuntos_na_lista(admin_client, **consulta):
    resposta = admin_client.get(reverse(LISTA), consulta)
    assert resposta.status_code == 200, "controle: a lista do admin precisa abrir"
    return {str(d) for d in resposta.context["cl"].result_list}


@pytest.fixture
def varios(fonte):
    em_dia = _conjunto(fonte, "em-dia")
    _execucao(em_dia, IngestionRun.State.SUCCEEDED, ha_horas=1)

    atrasado = _conjunto(fonte, "atrasado")
    _execucao(atrasado, IngestionRun.State.SUCCEEDED, ha_horas=100)

    falhou = _conjunto(fonte, "falhou")
    _execucao(falhou, IngestionRun.State.SUCCEEDED, ha_horas=30)
    _execucao(falhou, IngestionRun.State.FAILED, ha_horas=2, error_code="download")

    _conjunto(fonte, "sem-agenda", schedule_interval_hours=None)
    _conjunto(fonte, "desabilitado", enabled=False)

    normalizacao = _conjunto(
        fonte,
        "normalizacao-ruim",
        last_normalization_at=timezone.now() - timedelta(hours=1),
        last_normalization_error=MENSAGEM_DA_RECUSA,
    )
    _execucao(normalizacao, IngestionRun.State.SUCCEEDED, ha_horas=1)
    return fonte


def test_a_lista_mostra_a_situacao_de_cada_conjunto(admin_client, varios):
    html = _html(admin_client)

    rotulos = (
        "Em dia",
        "Atrasado",
        "Última coleta falhou",
        "Normalização falhou",
        "Sem agenda",
        "Desabilitado",
    )
    for rotulo in rotulos:
        assert rotulo in html, f"faltou a situação {rotulo!r} na lista"


def test_cada_situacao_cai_no_conjunto_certo_pelo_filtro(admin_client, varios):
    esperado = {
        "on_time": {"fonte/em-dia"},
        "late": {"fonte/atrasado"},
        "failed": {"fonte/falhou"},
        "normalization_failed": {"fonte/normalizacao-ruim"},
        "no_schedule": {"fonte/sem-agenda"},
        "disabled": {"fonte/desabilitado"},
    }

    for valor, conjuntos in esperado.items():
        assert _conjuntos_na_lista(admin_client, situacao=valor) == conjuntos, valor


def test_sem_filtro_aparecem_todos(admin_client, varios):
    assert len(_conjuntos_na_lista(admin_client)) == 6


def test_a_mensagem_da_recusa_aparece_na_coluna_de_normalizacao(admin_client, varios):
    assert MENSAGEM_DA_RECUSA in _html(admin_client)


def test_normalizacao_concluida_aparece_como_concluida(admin_client, fonte):
    _conjunto(fonte, "ok", last_normalization_at=timezone.now(), last_normalization_error="")

    assert "Concluída" in _html(admin_client)


def test_os_campos_do_alerta_sao_so_leitura_no_admin():
    from django.contrib import admin

    somente_leitura = admin.site._registry[Dataset].readonly_fields

    assert "last_alert_situation" in somente_leitura
    assert "last_alert_at" in somente_leitura


def test_os_campos_da_normalizacao_sao_so_leitura_no_admin():
    from django.contrib import admin

    somente_leitura = admin.site._registry[Dataset].readonly_fields

    assert "last_normalization_at" in somente_leitura
    assert "last_normalization_error" in somente_leitura


def test_filtro_desconhecido_nao_quebra_a_lista(admin_client, varios):
    # Valor inventado na URL: a lista continua abrindo (o `_conjuntos_na_lista` já confere o 200).
    _conjuntos_na_lista(admin_client, situacao="qualquer-coisa")


def test_o_resultado_da_ultima_execucao_aparece_com_o_codigo_do_erro(admin_client, varios):
    html = _html(admin_client)

    assert "Falha de download" in html


def test_execucao_em_andamento_nao_conta_como_sucesso_nem_como_falha(admin_client, fonte):
    conjunto = _conjunto(fonte, "rodando")
    _execucao(conjunto, IngestionRun.State.SUCCEEDED, ha_horas=1)
    IngestionRun.objects.create(
        dataset=conjunto, source_url=conjunto.url, state=IngestionRun.State.RUNNING
    )

    assert _conjuntos_na_lista(admin_client, situacao="on_time") == {"fonte/rodando"}


def test_execucao_em_andamento_depois_de_uma_falha_nao_apaga_a_falha(admin_client, fonte):
    conjunto = _conjunto(fonte, "retentando")
    _execucao(conjunto, IngestionRun.State.SUCCEEDED, ha_horas=30)
    _execucao(conjunto, IngestionRun.State.FAILED, ha_horas=2)
    IngestionRun.objects.create(
        dataset=conjunto, source_url=conjunto.url, state=IngestionRun.State.RUNNING
    )

    assert _conjuntos_na_lista(admin_client, situacao="failed") == {"fonte/retentando"}
    assert "Em andamento" not in _html(admin_client)


def test_o_numero_de_consultas_nao_cresce_com_o_numero_de_conjuntos(admin_client, fonte):
    for numero in range(2):
        conjunto = _conjunto(fonte, f"a{numero}")
        _execucao(conjunto, IngestionRun.State.SUCCEEDED, ha_horas=1)
    _html(admin_client)  # controle (e aquece o que o Django guarda em cache)
    with CaptureQueriesContext(connection) as poucos:
        _html(admin_client)

    for numero in range(2, 12):
        conjunto = _conjunto(fonte, f"a{numero}")
        _execucao(conjunto, IngestionRun.State.SUCCEEDED, ha_horas=1)
        _execucao(conjunto, IngestionRun.State.FAILED, ha_horas=2, error_code="download")
    with CaptureQueriesContext(connection) as muitos:
        _html(admin_client)

    assert len(muitos) == len(poucos)
