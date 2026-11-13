"""Comando `normalize_camara`: do bruto de `camara/deputados` para `Deputy` (Sessão 54).

Dados sintéticos. Regras (plano da Sessão 54, ADR 0005, 0009 e 0021): lê a execução mais recente
que gravou linhas, sem rede; linha inválida, conflito ou falha inesperada não gravam nada; nunca
apaga; quem some da lista continua na tabela, com a execução antiga.
"""

import socket
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.db.models import QuerySet
from django.utils import timezone

from apps.sources.catalog import DATASETS
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"


def deputado(id=1, nome="Ana da Câmara", partido="XYZ", uf="SP", legislatura=57):
    return {
        "id": id,
        "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id}",
        "nome": nome,
        "siglaPartido": partido,
        "siglaUf": uf,
        "idLegislatura": legislatura,
    }


ANA = deputado(1, "Ana da Câmara", "XYZ", "SP")
BETO = deputado(2, "Beto da Câmara", "ABC", "RJ")
CAIO = deputado(3, "Caio da Câmara", "", "MG")


def Deputy():
    from apps.legislature.models import Deputy as modelo

    return modelo


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
    saida, erro = StringIO(), StringIO()
    call_command("normalize_camara", stdout=saida, stderr=erro)
    return saida.getvalue() + erro.getvalue()


# --- O que a carga produz ---


def test_tres_deputados_validos_viram_tres_linhas(dataset):
    run = carga(dataset, [ANA, BETO, CAIO])
    saida = normalizar()
    assert Deputy().objects.count() == 3
    ana = Deputy().objects.get(camara_id=1)
    assert (ana.legislature_id, ana.name, ana.party_acronym, ana.state) == (
        57,
        "Ana da Câmara",
        "XYZ",
        "SP",
    )
    assert ana.ingestion_run == run
    assert Deputy().objects.get(camara_id=3).party_acronym == ""
    assert "linhas lidas 3" in saida
    assert "criadas 3" in saida
    assert "já existentes 0" in saida


def test_rodar_de_novo_sobre_o_mesmo_bruto_nao_duplica(dataset):
    carga(dataset, [ANA, BETO, CAIO])
    normalizar()
    saida = normalizar()
    assert Deputy().objects.count() == 3
    assert "criadas 0" in saida
    assert "já existentes 3" in saida


def test_linha_identica_repetida_no_bruto_vira_uma(dataset):
    carga(dataset, [ANA, ANA, BETO])
    normalizar()
    assert Deputy().objects.count() == 2


def test_troca_de_partido_atualiza_a_mesma_linha(dataset):
    carga(dataset, [ANA])
    normalizar()
    nova = carga(dataset, [deputado(1, "Ana da Câmara", "NOVO", "SP")])
    normalizar()
    assert Deputy().objects.count() == 1
    ana = Deputy().objects.get()
    assert ana.party_acronym == "NOVO"
    assert ana.ingestion_run == nova


def test_mesmo_id_em_duas_legislaturas_sao_duas_linhas(dataset):
    carga(dataset, [deputado(1, legislatura=57), deputado(1, legislatura=58)])
    normalizar()
    assert Deputy().objects.count() == 2
    assert set(Deputy().objects.values_list("legislature_id", flat=True)) == {57, 58}


def test_deputado_que_sumiu_da_lista_continua_com_a_execucao_antiga(dataset):
    antiga = carga(dataset, [ANA, BETO, CAIO], started_at=timezone.now() - timedelta(days=1))
    normalizar()
    nova = carga(dataset, [ANA, BETO])
    normalizar()
    assert Deputy().objects.count() == 3
    assert Deputy().objects.get(camara_id=3).ingestion_run == antiga
    assert Deputy().objects.get(camara_id=1).ingestion_run == nova


# --- Qual execução é lida ---


def test_usa_a_execucao_mais_recente_que_gravou_linhas(dataset):
    carga(dataset, [ANA], started_at=timezone.now() - timedelta(days=2))
    carga(dataset, [BETO])
    normalizar()
    assert list(Deputy().objects.values_list("camara_id", flat=True)) == [2]


def test_ignora_execucao_mais_nova_sem_linhas_ou_com_falha(dataset):
    carga(dataset, [ANA])
    carga(dataset, [], rows_read=0, rows_loaded=0)
    IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.FAILED,
        error_code=IngestionRun.ErrorCode.DOWNLOAD,
        finished_at=timezone.now(),
    )
    normalizar()
    assert list(Deputy().objects.values_list("camara_id", flat=True)) == [1]


def test_sem_o_conjunto_cadastrado_o_comando_diz_que_nao_encontrou():
    with pytest.raises(CommandError, match="não encontrado"):
        normalizar()


def test_sem_carga_com_linhas_o_comando_manda_rodar_a_coleta(dataset):
    carga(dataset, [], rows_read=0, rows_loaded=0)
    with pytest.raises(CommandError, match="ingest_dataset"):
        normalizar()
    assert Deputy().objects.count() == 0


# --- Falha fechada ---


@pytest.mark.parametrize(
    ("ruim", "coluna"),
    [
        ({**ANA, "id": True}, "id"),
        ({**ANA, "id": 0}, "id"),
        ({k: v for k, v in ANA.items() if k != "id"}, "id"),
        ({**ANA, "siglaUf": "sp"}, "siglaUf"),
        ({**ANA, "nome": "   "}, "nome"),
        ({**ANA, "idLegislatura": "5x"}, "idLegislatura"),
    ],
    ids=["id_booleano", "id_zero", "id_ausente", "uf_minuscula", "nome_vazio", "legislatura_letra"],
)
def test_linha_invalida_entre_validas_recusa_tudo_e_cita_so_a_coluna(dataset, ruim, coluna):
    carga(dataset, [BETO, ruim, CAIO])
    with pytest.raises(CommandError) as erro:
        normalizar()
    mensagem = str(erro.value)
    assert coluna in mensagem
    assert "Nada foi gravado" in mensagem
    for valor in ("Ana da Câmara", "Beto da Câmara", "Caio da Câmara"):
        assert valor not in mensagem
    assert Deputy().objects.count() == 0


def test_mesma_chave_com_nomes_diferentes_no_bruto_recusa_por_conflito(dataset):
    carga(dataset, [ANA, deputado(1, "Outro Nome Qualquer", "XYZ", "SP")])
    with pytest.raises(CommandError, match="conflitantes") as erro:
        normalizar()
    assert "Outro Nome Qualquer" not in str(erro.value)
    assert Deputy().objects.count() == 0


def test_falha_inesperada_na_gravacao_desfaz_tudo_e_nao_vaza_o_detalhe(dataset, monkeypatch):
    carga(dataset, [ANA, BETO])
    original = QuerySet.bulk_create

    def falha(self, objs, *args, **kwargs):
        if self.model is Deputy():
            raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")
        return original(self, objs, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "bulk_create", falha)
    with pytest.raises(CommandError, match="inesperada") as erro:
        normalizar()
    assert SEGREDO not in str(erro.value)
    assert erro.value.__cause__ is None and erro.value.__context__ is None
    assert Deputy().objects.count() == 0


# --- Saída e rede ---


def test_a_saida_traz_so_contagens_e_nenhum_nome(dataset):
    carga(dataset, [ANA, BETO])
    saida = normalizar()
    for nome in ("Ana da Câmara", "Beto da Câmara"):
        assert nome not in saida


def test_nao_faz_nenhuma_requisicao_de_rede(dataset, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("o comando tentou usar a rede")

    carga(dataset, [ANA])
    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    normalizar()
    assert Deputy().objects.count() == 1


# --- `normalize_latest`: o passo que o agendador chama depois de cada coleta ---


def normalize_latest(dataset):
    from apps.legislature import normalization

    return normalization.normalize_latest(dataset)


def test_normalize_latest_normaliza_a_carga_mais_recente(dataset):
    carga(dataset, [ANA, BETO])

    resultado = normalize_latest(dataset)

    assert Deputy().objects.count() == 2
    assert (resultado.rows_read, resultado.created, resultado.existing) == (2, 2, 0)


def test_normalize_latest_de_carga_ja_normalizada_devolve_none_sem_regravar(dataset):
    carga(dataset, [ANA])
    normalize_latest(dataset)
    Deputy().objects.update(name="ALTERADO-DEPOIS")

    resultado = normalize_latest(dataset)

    assert resultado is None
    assert Deputy().objects.get().name == "ALTERADO-DEPOIS"


def test_normalize_latest_sem_carga_com_linhas_devolve_none(dataset):
    carga(dataset, [], rows_read=0, rows_loaded=0)

    assert normalize_latest(dataset) is None
    assert Deputy().objects.count() == 0


def test_normalize_latest_ignora_execucao_mais_nova_de_arquivo_igual(dataset):
    carga(dataset, [ANA], started_at=timezone.now() - timedelta(days=1))
    normalize_latest(dataset)
    carga(dataset, [], rows_read=0, rows_loaded=0)  # arquivo igual: 0 linhas, mais nova
    Deputy().objects.update(name="ALTERADO-DEPOIS")

    assert normalize_latest(dataset) is None
    assert Deputy().objects.get().name == "ALTERADO-DEPOIS"


def test_normalize_latest_com_bruto_invalido_levanta_a_excecao_base_sem_valores(dataset):
    from apps.sources.normalization import NormalizationRefused

    carga(dataset, [{**ANA, "nome": "VALOR-RUIM-XYZ" * 20}])

    with pytest.raises(NormalizationRefused) as erro:
        normalize_latest(dataset)

    assert "VALOR-RUIM-XYZ" not in str(erro.value)
    assert Deputy().objects.count() == 0


def test_normalize_latest_retenta_a_carga_que_recusou_quando_vem_uma_valida(dataset):
    from apps.sources.normalization import NormalizationRefused

    ruim = {**ANA, "nome": "VALOR-RUIM-XYZ" * 20}
    carga(dataset, [ruim], started_at=timezone.now() - timedelta(days=1))
    with pytest.raises(NormalizationRefused):
        normalize_latest(dataset)

    carga(dataset, [ANA])

    assert normalize_latest(dataset).created == 1
