"""Comando `normalize_tse`: do bruto do TSE para Election, Person e Candidacy.

Dados sintéticos. Regras (plano da Sessão 39, ADR 0005 e ADR 0009): lê a execução mais recente
que gravou linhas, sem rede; o bruto traz cada candidatura duas vezes (cópias idênticas);
conflito entre linhas, linha inválida ou falha inesperada não gravam nada; só apaga pela
retirada da fonte (lápide, `test_retirement.py`).
"""

import socket
from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from django.db.models import QuerySet
from django.utils import timezone

from apps.elections.models import Candidacy, Election, Person
from apps.sources.catalog import DATASETS
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"

ESTADUAL = {
    "DT_GERACAO": "08/11/2026",
    "HH_GERACAO": "20:00:00",
    "ANO_ELEICAO": "2026",
    "CD_TIPO_ELEICAO": "2",
    "NM_TIPO_ELEICAO": "Eleição Ordinária",
    "NR_TURNO": "1",
    "CD_ELEICAO": "6259",
    "DS_ELEICAO": "Eleições Gerais Estaduais 2026",
    "DT_ELEICAO": "04/10/2026",
    "TP_ABRANGENCIA": "ESTADUAL",
    "SG_UF": "SP",
    "SG_UE": "SP",
    "NM_UE": "SÃO PAULO",
    "CD_CARGO": "6",
    "DS_CARGO": "DEPUTADO FEDERAL",
    "SQ_CANDIDATO": "1000000001",
    "NR_CANDIDATO": "12345",
    "NM_URNA_CANDIDATO": "Ana da Urna",
    "NM_SOCIAL_CANDIDATO": "#NULO",
    "CD_SITUACAO_CANDIDATURA": "-3",
    "DS_SITUACAO_CANDIDATURA": "#NE",
    "TP_AGREMIACAO": "PARTIDO ISOLADO",
    "NR_PARTIDO": "12",
    "SG_PARTIDO": "XYZ",
    "NM_PARTIDO": "Partido de Teste",
    "NR_FEDERACAO": "-1",
    "NM_FEDERACAO": "#NULO",
    "SG_FEDERACAO": "#NULO",
    "DS_COMPOSICAO_FEDERACAO": "#NULO",
    "SQ_COLIGACAO": "1",
    "NM_COLIGACAO": "PARTIDO ISOLADO",
    "DS_COMPOSICAO_COLIGACAO": "Partido de Teste",
    "CD_SIT_TOT_TURNO": "-1",
    "DS_SIT_TOT_TURNO": "#NULO",
}


def linha(**mudancas):
    return {**ESTADUAL, **mudancas}


def ana(**mudancas):
    return linha(**mudancas)


BETO = {
    "CD_ELEICAO": "6257",
    "DS_ELEICAO": "Eleição Geral Federal 2026",
    "TP_ABRANGENCIA": "FEDERAL",
    "SG_UF": "BR",
    "SG_UE": "BR",
    "NM_UE": "BRASIL",
    "CD_CARGO": "1",
    "DS_CARGO": "PRESIDENTE",
    "SQ_CANDIDATO": "1000000002",
    "NR_CANDIDATO": "13",
    "NM_URNA_CANDIDATO": "Beto da Urna",
}


def beto_1o_turno(**mudancas):
    return linha(**{**BETO, **mudancas})


def beto_2o_turno(**mudancas):
    return beto_1o_turno(**{"NR_TURNO": "2", "CD_ELEICAO": "6258", **mudancas})


@pytest.fixture
def dataset():
    fonte = Source.objects.create(
        slug="tse",
        name="TSE",
        institution="Tribunal Superior Eleitoral",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="consulta-cand-2026",
        name="Consulta de candidatos 2026",
        url="https://example.org/consulta_cand_2026.zip",
        format=Dataset.Format.ZIP_CSV,
        allowed_columns=DATASETS[0]["allowed_columns"],
    )


def carga(dataset, linhas, itens=None, **extra):
    """Cria uma execução com `linhas` no bruto. `itens` dá o arquivo do ZIP de cada linha."""
    campos = {
        "state": IngestionRun.State.SUCCEEDED,
        "finished_at": timezone.now(),
        "sha256_original": HASH,
        "rows_read": len(linhas),
        "rows_loaded": len(linhas),
        **extra,
    }
    run = IngestionRun.objects.create(dataset=dataset, source_url=dataset.url, **campos)
    itens = itens or ["consulta_cand_2026_BRASIL.csv"] * len(linhas)
    RawRecord.objects.bulk_create(
        [RawRecord(run=run, item_name=i, values=v) for i, v in zip(itens, linhas, strict=True)]
    )
    return run


def carga_vazia(dataset):
    """Execução bem-sucedida de arquivo igual ao anterior: 0 linhas (ADR 0008, decisão 6)."""
    return carga(dataset, [], rows_read=0, rows_loaded=0)


def carga_com_falha(dataset):
    return IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.FAILED,
        error_code=IngestionRun.ErrorCode.DOWNLOAD,
        finished_at=timezone.now(),
    )


def normalizar():
    saida, erro = StringIO(), StringIO()
    call_command("normalize_tse", stdout=saida, stderr=erro)
    return saida.getvalue() + erro.getvalue()


def contagens():
    return Election.objects.count(), Person.objects.count(), Candidacy.objects.count()


# --- O que a carga produz ---


def test_bruto_duplicado_vira_uma_candidatura_por_chave_e_o_2o_turno_reaproveita_a_pessoa(dataset):
    linhas = [ana(), ana(), beto_1o_turno(), beto_1o_turno(), beto_2o_turno(), beto_2o_turno()]
    itens = ["BRASIL.csv", "SP.csv", "BRASIL.csv", "BR.csv", "BRASIL.csv", "BR.csv"]
    carga(dataset, linhas, itens)
    saida = normalizar()
    assert contagens() == (3, 2, 3)
    beto = Person.objects.get(tse_candidate_id=1000000002)
    assert beto.candidacies.count() == 2
    assert {c.election.round for c in beto.candidacies.all()} == {1, 2}
    assert "linhas lidas 6" in saida
    assert "candidaturas únicas 3" in saida
    assert "criadas 3" in saida


def test_nome_publico_e_o_de_urna_e_o_social_fica_so_no_campo_interno(dataset):
    carga(dataset, [ana(NM_SOCIAL_CANDIDATO="Ana Social de Teste")])
    normalizar()
    pessoa = Person.objects.get()
    assert pessoa.public_name == "Ana da Urna"
    assert pessoa.social_name == "Ana Social de Teste"


def test_cada_candidatura_guarda_a_execucao_e_o_instante_de_geracao_da_fonte(dataset):
    run = carga(dataset, [ana()])
    normalizar()
    candidatura = Candidacy.objects.get()
    assert candidatura.ingestion_run_id == run.pk
    esperado = datetime(2026, 11, 8, 20, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert candidatura.source_generated_at == esperado


def test_marcadores_do_tse_viram_ausentes_no_banco(dataset):
    carga(dataset, [ana()])
    normalizar()
    candidatura = Candidacy.objects.get()
    assert candidatura.status_code is None and candidatura.status_name == ""
    assert candidatura.result_code is None and candidatura.result_name == ""
    assert candidatura.federation_acronym == "" and candidatura.federation_name == ""


# --- Idempotência e atualização ---


def test_rodar_duas_vezes_nao_duplica_nada(dataset):
    carga(dataset, [ana(), beto_1o_turno()])
    normalizar()
    antes = contagens()
    segunda = normalizar()
    assert contagens() == antes == (2, 2, 2)
    assert "criadas 0" in segunda
    assert "já existentes 2" in segunda


def test_carga_nova_com_campo_mudado_atualiza_sem_duplicar(dataset):
    carga(dataset, [ana()])
    normalizar()
    run2 = carga(dataset, [ana(SG_PARTIDO="ABC", NM_URNA_CANDIDATO="Ana Nova")])
    normalizar()
    assert contagens() == (1, 1, 1)
    candidatura = Candidacy.objects.get()
    assert candidatura.party_acronym == "ABC"
    assert candidatura.person.public_name == "Ana Nova"
    assert candidatura.ingestion_run_id == run2.pk


def test_candidatura_que_sumiu_de_carga_integra_e_retirada_e_a_eleicao_fica(dataset):
    # Mudou na fatia da lápide (ADR 0005, decisão 9): antes continuava no banco. Agora some a
    # candidatura e a pessoa (dado pessoal); a eleição fica. Detalhes em test_retirement.py.
    carga(dataset, [ana(), beto_1o_turno()])
    normalizar()
    carga(dataset, [ana()])
    normalizar()
    assert contagens() == (2, 1, 1)


def test_volume_acima_do_tamanho_do_lote_fica_correto_e_idempotente(dataset):
    linhas = []
    for i in range(2500):
        base = ana(SQ_CANDIDATO=str(2_000_000_000 + i), NM_URNA_CANDIDATO=f"Candidato {i}")
        linhas += [base, base]
    carga(dataset, linhas)
    normalizar()
    assert contagens() == (1, 2500, 2500)
    normalizar()
    assert contagens() == (1, 2500, 2500)


# --- Qual execução é lida ---


def test_le_a_execucao_mais_recente_que_gravou_linhas(dataset):
    run1 = carga(dataset, [ana()])
    carga_vazia(dataset)
    carga_com_falha(dataset)
    normalizar()
    assert Candidacy.objects.get().ingestion_run_id == run1.pk


def test_sem_conjunto_cadastrado_e_recusado(db):
    with pytest.raises(CommandError, match="Conjunto"):
        normalizar()


def test_sem_nenhuma_carga_com_linhas_e_recusado(dataset):
    with pytest.raises(CommandError, match="Nenhuma carga"):
        normalizar()
    carga_vazia(dataset)
    carga_com_falha(dataset)
    with pytest.raises(CommandError, match="Nenhuma carga"):
        normalizar()
    assert contagens() == (0, 0, 0)


# --- Conflitos: nada é gravado ---


def test_copias_divergentes_da_mesma_candidatura_param_sem_gravar(dataset):
    carga(dataset, [ana(SG_PARTIDO="AAA"), ana(SG_PARTIDO="BBB")], ["BRASIL.csv", "SP.csv"])
    with pytest.raises(CommandError, match="conflitantes") as erro:
        normalizar()
    assert contagens() == (0, 0, 0)
    for valor in ("AAA", "BBB", "Ana da Urna"):
        assert valor not in str(erro.value)


def test_mesma_eleicao_descrita_de_dois_jeitos_para_sem_gravar(dataset):
    carga(dataset, [ana(), beto_1o_turno(CD_ELEICAO="6259", DS_ELEICAO="Outra descrição")])
    with pytest.raises(CommandError, match="conflitantes"):
        normalizar()
    assert contagens() == (0, 0, 0)


def test_mesmo_sq_com_dois_nomes_de_urna_no_ciclo_para_sem_gravar(dataset):
    carga(dataset, [beto_1o_turno(), beto_2o_turno(NM_URNA_CANDIDATO="Outro Nome")])
    with pytest.raises(CommandError, match="conflitantes") as erro:
        normalizar()
    assert contagens() == (0, 0, 0)
    assert "Beto da Urna" not in str(erro.value) and "Outro Nome" not in str(erro.value)


# --- Falhas: tudo ou nada, sem vazar valor ---


def test_linha_invalida_no_meio_desfaz_tudo_e_cita_so_a_coluna_e_a_contagem(dataset):
    ruim = ana(SQ_CANDIDATO="1000000003", NM_URNA_CANDIDATO="Carla Invalida")
    ruim["NR_CANDIDATO"] = "VALOR-RUIM-XYZ"
    carga(dataset, [ana(), ruim, beto_1o_turno()])
    with pytest.raises(CommandError, match="linhas inválidas") as erro:
        normalizar()
    mensagem = str(erro.value)
    assert "NR_CANDIDATO" in mensagem and "1" in mensagem
    for valor in ("VALOR-RUIM-XYZ", "Carla Invalida", "Ana da Urna", "Beto da Urna"):
        assert valor not in mensagem
    assert contagens() == (0, 0, 0)


def test_falha_inesperada_na_gravacao_desfaz_tudo_e_nao_vaza_o_detalhe(dataset, monkeypatch):
    carga(dataset, [ana(), beto_1o_turno()])
    original = QuerySet.bulk_create

    def falha(self, objs, *args, **kwargs):
        if self.model is Candidacy:
            raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")
        return original(self, objs, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "bulk_create", falha)
    with pytest.raises(CommandError, match="inesperada") as erro:
        normalizar()
    assert SEGREDO not in str(erro.value)
    assert erro.value.__cause__ is None and erro.value.__context__ is None
    assert contagens() == (0, 0, 0)


def test_falha_inesperada_mostra_so_a_classe_da_excecao(dataset, monkeypatch):
    carga(dataset, [ana()])

    def falha(self, objs, *args, **kwargs):
        raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")

    monkeypatch.setattr(QuerySet, "bulk_create", falha)
    with pytest.raises(CommandError) as erro:
        normalizar()
    assert str(erro.value) == (
        "A normalização falhou de forma inesperada (RuntimeError); nada foi gravado."
    )


def test_classe_com_nome_que_nao_e_identificador_vira_interrogacao(dataset, monkeypatch):
    carga(dataset, [ana()])
    forjada = type("Falsa\nforjada: tudo certo", (Exception,), {})

    def falha(self, objs, *args, **kwargs):
        raise forjada(SEGREDO)

    monkeypatch.setattr(QuerySet, "bulk_create", falha)
    with pytest.raises(CommandError) as erro:
        normalizar()
    assert str(erro.value) == "A normalização falhou de forma inesperada (?); nada foi gravado."


# --- Saída e rede ---


def test_a_saida_traz_so_contagens_e_nenhum_nome(dataset):
    carga(dataset, [ana(NM_SOCIAL_CANDIDATO="Ana Social de Teste"), beto_1o_turno()])
    saida = normalizar()
    for nome in ("Ana da Urna", "Ana Social de Teste", "Beto da Urna"):
        assert nome not in saida


def test_nao_faz_nenhuma_requisicao_de_rede(dataset, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("o comando tentou usar a rede")

    carga(dataset, [ana()])
    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    normalizar()
    assert contagens() == (1, 1, 1)


# --- `normalize_latest`: o passo que o agendador chama depois de cada coleta ---


def normalize_latest(dataset):
    from apps.elections import normalization

    return normalization.normalize_latest(dataset)


def test_normalize_latest_normaliza_a_carga_mais_recente(dataset):
    carga(dataset, [ana(), beto_1o_turno()])

    resultado = normalize_latest(dataset)

    assert contagens() == (2, 2, 2)
    assert (resultado.rows_read, resultado.created, resultado.existing) == (2, 2, 0)


def test_normalize_latest_de_carga_ja_normalizada_devolve_none_sem_regravar(dataset):
    carga(dataset, [ana()])
    normalize_latest(dataset)
    Candidacy.objects.update(status_name="ALTERADO-DEPOIS")

    resultado = normalize_latest(dataset)

    assert resultado is None
    assert Candidacy.objects.get().status_name == "ALTERADO-DEPOIS"


def test_normalize_latest_sem_carga_com_linhas_devolve_none(dataset):
    carga_vazia(dataset)
    carga_com_falha(dataset)

    assert normalize_latest(dataset) is None
    assert contagens() == (0, 0, 0)


def test_normalize_latest_ignora_execucao_mais_nova_de_arquivo_igual(dataset):
    carga(dataset, [ana()])
    normalize_latest(dataset)
    carga_vazia(dataset)  # arquivo igual: 0 linhas, mais nova que a normalizada
    Candidacy.objects.update(status_name="ALTERADO-DEPOIS")

    assert normalize_latest(dataset) is None
    assert Candidacy.objects.get().status_name == "ALTERADO-DEPOIS"


def test_normalize_latest_com_bruto_invalido_levanta_a_excecao_base_sem_valores(dataset):
    from apps.sources.normalization import NormalizationRefused

    carga(dataset, [ana(SQ_CANDIDATO="VALOR-RUIM-XYZ")])

    with pytest.raises(NormalizationRefused) as erro:
        normalize_latest(dataset)

    assert "VALOR-RUIM-XYZ" not in str(erro.value)
    assert contagens() == (0, 0, 0)


def test_normalize_latest_retenta_a_carga_que_recusou_quando_vem_uma_valida(dataset):
    from apps.sources.normalization import NormalizationRefused

    carga(dataset, [ana(SQ_CANDIDATO="VALOR-RUIM-XYZ")])
    with pytest.raises(NormalizationRefused):
        normalize_latest(dataset)

    carga(dataset, [ana()])

    assert normalize_latest(dataset).created == 1


# --- Estado da última normalização (painel e alerta) depois do comando à mão (Sessão 85) ---
# `Dataset.last_normalization_error` só era escrito pelo agendador, depois de coleta bem-sucedida.
# Um `normalize_tse` à mão que desse certo deixava a recusa antiga no painel e, com a coleta
# falhando, o aviso seguia dizendo que as retiradas estavam paradas quando já tinham sido aplicadas.

RECUSA_ANTIGA = "Normalização recusada: candidaturas sumiram do arquivo: 25 de 100. Nada gravado."


def recusa_antiga(dataset):
    """Deixa no conjunto a recusa que o agendador gravou antes; devolve a hora que ele gravou."""
    antes = timezone.now() - timedelta(days=1)
    Dataset.objects.filter(pk=dataset.pk).update(
        last_normalization_error=RECUSA_ANTIGA, last_normalization_at=antes
    )
    return antes


def estado_da_normalizacao(dataset):
    dataset.refresh_from_db()
    return dataset.last_normalization_error, dataset.last_normalization_at


def normalizar_com(*argumentos):
    call_command("normalize_tse", *argumentos, stdout=StringIO(), stderr=StringIO())


@pytest.mark.parametrize("argumentos", [(), ("--aceitar-retiradas",)])
def test_normalizar_com_sucesso_limpa_a_recusa_antiga_e_marca_a_hora(dataset, argumentos):
    carga(dataset, [ana()])
    antes = recusa_antiga(dataset)
    comando_em = timezone.now()

    normalizar_com(*argumentos)

    erro, hora = estado_da_normalizacao(dataset)
    assert erro == ""
    assert hora is not None and hora > antes and hora >= comando_em


def test_normalizar_com_sucesso_sem_erro_gravado_so_atualiza_a_hora(dataset):
    carga(dataset, [ana()])
    Dataset.objects.filter(pk=dataset.pk).update(last_normalization_at=None)

    normalizar_com()

    erro, hora = estado_da_normalizacao(dataset)
    assert erro == ""
    assert hora is not None


def test_recusa_do_comando_nao_mexe_no_estado_gravado(dataset):
    carga(dataset, [ana(SQ_CANDIDATO="VALOR-RUIM-XYZ")])
    antes = recusa_antiga(dataset)

    with pytest.raises(CommandError):
        normalizar_com()

    erro, hora = estado_da_normalizacao(dataset)
    assert erro == RECUSA_ANTIGA
    assert hora == antes


def test_falha_inesperada_do_comando_nao_mexe_no_estado_gravado(dataset, monkeypatch):
    carga(dataset, [ana()])
    antes = recusa_antiga(dataset)
    original = QuerySet.bulk_create

    def falha(self, objs, *args, **kwargs):
        if self.model is Candidacy:
            raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")
        return original(self, objs, *args, **kwargs)

    monkeypatch.setattr(QuerySet, "bulk_create", falha)
    with pytest.raises(CommandError, match="inesperada"):
        normalizar_com()

    erro, hora = estado_da_normalizacao(dataset)
    assert erro == RECUSA_ANTIGA
    assert hora == antes


def test_o_comando_limpa_so_o_conjunto_do_tse_e_nao_o_de_outra_fonte(dataset):
    outra_fonte = Source.objects.create(
        slug="camara",
        name="Câmara",
        institution="Câmara dos Deputados",
        official_url="https://example.org/camara",
        access_type=Source.AccessType.API,
    )
    outro = Dataset.objects.create(
        source=outra_fonte,
        slug="deputados",
        name="Deputados",
        url="https://example.org/deputados.json",
        format=Dataset.Format.JSON,
        allowed_columns=["id"],
        last_normalization_error="Normalização recusada: dados de outra fonte.",
    )
    carga(dataset, [ana()])
    recusa_antiga(dataset)

    normalizar_com()

    assert estado_da_normalizacao(dataset)[0] == ""
    assert estado_da_normalizacao(outro)[0] == "Normalização recusada: dados de outra fonte."


def test_depois_do_comando_o_aviso_de_coleta_falhada_nao_diz_que_as_retiradas_estao_paradas(
    dataset,
):
    from apps.sources import alerts

    Dataset.objects.filter(pk=dataset.pk).update(
        enabled=True,
        schedule_interval_hours=24,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Decisão do dono de teste.",
    )
    carga(dataset, [ana()])
    carga_com_falha(dataset)  # a coleta de depois falhou: a situação é "Última coleta falhou"
    recusa_antiga(dataset)
    normalizar_com("--aceitar-retiradas")
    textos = []

    alerts.send_pending(timezone.now(), textos.append)

    assert textos == ["ALERTA tse/consulta-cand-2026: Última coleta falhou (Falha de download)"]
    assert alerts.RETIREMENTS_HELD_TEXT not in textos[0]
