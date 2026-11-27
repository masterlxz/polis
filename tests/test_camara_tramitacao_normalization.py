"""Normalização de `camara/proposicoes-tramitacoes-2026` em `CamaraPropositionStep` (ADR 0034).
Dados sintéticos no formato medido em 2026-11-27 (Rodada 5 de `fontes/camara.md`); o bruto guarda
TUDO como texto.

Regras: sem rede; a carga mais recente do conjunto; a chave é (proposição, `sequencia`, `dataHora`,
`siglaOrgao`, `descricaoTramitacao`), porque `idTramitacao` não é chave (400 valores em 118.724
linhas) e (proposição, `sequencia`) tem 13 eventos diferentes com o mesmo número; duplicata exata
vale uma linha (38 chaves em 2026) e NÃO recusa; `sequencia` vazia vira nula (1 linha em 2026) e
a unicidade trata NULL como igual, senão a linha duplicaria a cada coleta; sem chave estrangeira
para `CamaraProposition` (a maioria das proposições do arquivo não existe lá); linha inválida
recusa tudo; nunca apaga.

Os módulos novos são importados dentro dos testes: antes de existirem, cada teste falha por si e a
coleta do pytest não para.
"""

from datetime import datetime, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "valor-de-linha-que-nao-pode-vazar"
URI = "https://dadosabertos.camara.leg.br/api/v2/proposicoes/{}"
COLUNAS = ["uriProposicao", "sequencia", "dataHora", "siglaOrgao", "descricaoTramitacao"]


def linha(proposicao="14666", sequencia="152", **extra):
    base = {
        "uriProposicao": URI.format(proposicao),
        "sequencia": sequencia,
        "dataHora": "2026-05-07T16:58:00",
        "siglaOrgao": "MESA",
        "descricaoTramitacao": "Apresentação de Requerimento",
    }
    return {**base, **extra}


@pytest.fixture
def conjunto():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="proposicoes-tramitacoes-2026",
        name="Tramitações das proposições da Câmara (2026)",
        url="https://example.org/proposicoesTramitacoes-2026.csv",
        format=Dataset.Format.CSV,
        allowed_columns=COLUNAS,
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
        [RawRecord(run=run, item_name="download.zip", values=v) for v in linhas]
    )
    return run


def modelo():
    """O modelo, importado só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import CamaraPropositionStep

    return CamaraPropositionStep


def normalizar(run):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    return normalizacao.normalize(run)


def recusa(run):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    with pytest.raises(normalizacao.NormalizationRefused) as erro:
        normalizacao.normalize(run)
    return str(erro.value)


def total():
    return modelo().objects.count()


# --- caminho feliz -----------------------------------------------------------------------------


def test_uma_linha_grava_a_tramitacao_com_o_id_da_uri_e_a_hora_de_brasilia(conjunto):
    resultado = normalizar(carga(conjunto, [linha()]))
    assert (resultado.rows_read, resultado.unique, resultado.created, resultado.existing) == (
        1,
        1,
        1,
        0,
    )
    passo = modelo().objects.get()
    assert passo.camara_proposition_id == "14666"
    assert passo.sequence == 152
    assert passo.occurred_at == datetime(2026, 5, 7, 16, 58, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert (passo.organ_code, passo.description) == ("MESA", "Apresentação de Requerimento")


def test_sequencia_vazia_grava_nulo_e_nao_recusa(conjunto):
    normalizar(carga(conjunto, [linha("2603645", "", siglaOrgao="CSAUDE")]))
    assert modelo().objects.get().sequence is None


def test_sequencia_vazia_na_mesma_chave_em_duas_cargas_continua_uma_linha(conjunto):
    """NULL conta como igual na unicidade: sem isso a linha sem `sequencia` duplica a cada carga."""
    normalizar(carga(conjunto, [linha("2603645", "")]))
    segunda = normalizar(carga(conjunto, [linha("2603645", "")]))
    assert total() == 1
    assert (segunda.created, segunda.existing) == (0, 1)


def test_sequencia_vazia_duas_vezes_na_mesma_carga_e_uma_linha(conjunto):
    resultado = normalizar(carga(conjunto, [linha("1", ""), linha("1", "")]))
    assert (resultado.rows_read, resultado.unique, resultado.created) == (2, 1, 1)
    assert total() == 1


# --- a chave -----------------------------------------------------------------------------------


def test_linha_identica_na_chave_vale_uma_e_nao_recusa(conjunto):
    """38 chaves de 2026 repetem: dado idêntico na allowlist (só `codSituacao` ou o id mudavam)."""
    resultado = normalizar(carga(conjunto, [linha(), linha()]))
    assert (resultado.rows_read, resultado.unique, resultado.created) == (2, 1, 1)
    assert total() == 1


def test_mesma_proposicao_e_sequencia_com_eventos_diferentes_sao_duas_linhas(conjunto):
    """Os 13 casos reais de 2026: NAJUR(SGM) "Recebimento" em 11/05 e "Encaminhamento" em 12/05,
    ambos com a sequência 71. Recusar pararia a coleta todo dia."""
    normalizar(
        carga(
            conjunto,
            [
                linha(
                    "2113091",
                    "71",
                    dataHora="2026-05-11T14:20:31",
                    siglaOrgao="NAJUR(SGM)",
                    descricaoTramitacao="Recebimento",
                ),
                linha(
                    "2113091",
                    "71",
                    dataHora="2026-05-12T16:07:00",
                    siglaOrgao="NAJUR(SGM)",
                    descricaoTramitacao="Encaminhamento",
                ),
            ],
        )
    )
    assert total() == 2


def test_mesmo_evento_com_sequencia_diferente_sao_duas_linhas(conjunto):
    """999 chaves de 2026: várias "Apresentação" no mesmo minuto, com sequências diferentes. Sem a
    `sequencia` na chave, 1.290 linhas se perderiam."""
    normalizar(carga(conjunto, [linha("1", "10"), linha("1", "11")]))
    assert sorted(modelo().objects.values_list("sequence", flat=True)) == [10, 11]


def test_o_id_da_tramitacao_nao_e_lido_nem_gravado():
    """`idTramitacao` repete (o valor 1 aparece 11.093 vezes): fora da allowlist e do modelo."""
    nomes = {campo.name for campo in modelo()._meta.get_fields()}
    assert not any("tramitacao" in nome.replace("_", "").lower() for nome in nomes)
    assert "idTramitacao" not in COLUNAS


@pytest.mark.parametrize(
    "mudanca",
    [
        {"uriProposicao": URI.format("99")},
        {"dataHora": "2026-05-07T16:59:00"},
        {"siglaOrgao": "PLEN"},
        {"descricaoTramitacao": "Outra descrição"},
    ],
    ids=["proposicao", "data_hora", "orgao", "descricao"],
)
def test_cada_parte_da_chave_separa_duas_linhas(conjunto, mudanca):
    normalizar(carga(conjunto, [linha(), linha(**mudanca)]))
    assert total() == 2


# --- linha inválida ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("uriProposicao", "https://dadosabertos.camara.leg.br/api/v2/orgaos/4/{S}"),
        ("uriProposicao", ""),
        ("sequencia", "abc{S}"),
        ("sequencia", "-1"),
        ("dataHora", "07/05/2026 16:58 {S}"),
        ("dataHora", ""),
        ("siglaOrgao", ""),
        ("descricaoTramitacao", ""),
        ("siglaOrgao", "X" * 31),
        ("descricaoTramitacao", "X" * 201),
        ("descricaoTramitacao", "com\x07controle {S}"),
        ("descricaoTramitacao", "com\nquebra {S}"),
        ("descricaoTramitacao", "com\ttab {S}"),
    ],
)
def test_linha_invalida_recusa_tudo_e_a_mensagem_cita_a_coluna_e_nunca_o_valor(
    conjunto, coluna, valor
):
    valor = valor.replace("{S}", SEGREDO)
    run = carga(conjunto, [linha("1", "1"), {**linha("2", "2"), coluna: valor}])
    mensagem = recusa(run)
    assert f"{coluna} (1)" in mensagem
    assert "Nada foi gravado" in mensagem
    assert SEGREDO not in mensagem
    assert total() == 0


def test_coluna_da_allowlist_ausente_recusa_citando_so_o_nome(conjunto):
    sem_orgao = {k: v for k, v in linha().items() if k != "siglaOrgao"}
    mensagem = recusa(carga(conjunto, [sem_orgao]))
    assert "siglaOrgao" in mensagem
    assert total() == 0


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [("siglaOrgao", "X" * 30), ("descricaoTramitacao", "X" * 200)],
    ids=["orgao_30", "descricao_200"],
)
def test_texto_no_teto_passa(conjunto, coluna, valor):
    normalizar(carga(conjunto, [linha(**{coluna: valor})]))
    assert total() == 1


# --- idempotência, nunca apaga, sem FK ---------------------------------------------------------


def test_segunda_normalizacao_da_mesma_carga_nao_cria_nada(conjunto):
    run = carga(conjunto, [linha("1", "1"), linha("2", "2")])
    normalizar(run)
    segunda = normalizar(run)
    assert (segunda.created, segunda.existing) == (0, 2)
    assert total() == 2


def test_linha_que_saiu_da_carga_nova_continua_no_banco(conjunto):
    normalizar(carga(conjunto, [linha("1", "1"), linha("2", "2")]))
    normalizar(carga(conjunto, [linha("1", "1")]))
    assert total() == 2


def test_a_carga_nova_atualiza_a_execucao_que_viu_a_linha(conjunto):
    primeira = carga(conjunto, [linha()])
    normalizar(primeira)
    segunda = carga(conjunto, [linha()])
    normalizar(segunda)
    assert modelo().objects.get().ingestion_run_id == segunda.pk


def test_proposicao_que_nao_esta_no_banco_nao_impede_a_gravacao(conjunto):
    from apps.legislature.models import CamaraProposition

    assert not CamaraProposition.objects.exists()
    normalizar(carga(conjunto, [linha("46295")]))
    assert total() == 1


def test_o_modelo_nao_tem_chave_para_a_proposicao():
    from apps.legislature.models import CamaraProposition

    destinos = {
        campo.related_model
        for campo in modelo()._meta.get_fields()
        if campo.is_relation and campo.related_model is not None
    }
    assert CamaraProposition not in destinos


# --- teto, lotes e transação -------------------------------------------------------------------


@pytest.mark.parametrize(("linhas", "recusa_esperada"), [(500_001, True), (500_000, False)])
def test_carga_acima_do_teto_de_linhas_recusa_antes_de_ler_e_no_teto_passa(
    conjunto, linhas, recusa_esperada
):
    run = carga(conjunto, [linha()], rows_read=linhas, rows_loaded=linhas)
    if recusa_esperada:
        mensagem = recusa(run)
        assert "limite de linhas" in mensagem
        assert "Nada foi gravado" in mensagem
        assert total() == 0
    else:
        assert normalizar(run).created == 1


def test_a_gravacao_em_lotes_nao_perde_nem_duplica_linhas(conjunto, monkeypatch):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    monkeypatch.setattr(normalizacao, "BATCH_SIZE", 2)
    resultado = normalizar(carga(conjunto, [linha(str(100 + n), str(n)) for n in range(5)]))
    assert resultado.created == 5
    assert total() == 5


def test_falha_no_meio_nao_deixa_gravacao_parcial(conjunto, monkeypatch):
    """Uma transação só: se o banco recusar no segundo lote, o primeiro também não fica."""
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    monkeypatch.setattr(normalizacao, "BATCH_SIZE", 1)
    run = carga(conjunto, [linha("1", "1"), linha("2", "2")])
    original = modelo().objects.bulk_create
    chamadas = []

    def quebra(objetos, *args, **kwargs):
        chamadas.append(1)
        if len(chamadas) == 2:
            raise RuntimeError("falha simulada")
        return original(objetos, *args, **kwargs)

    monkeypatch.setattr(modelo().objects, "bulk_create", quebra)
    with pytest.raises(RuntimeError):
        normalizar(run)
    assert total() == 0


# --- normalize_latest e o comando --------------------------------------------------------------


def test_normalize_latest_usa_a_carga_mais_recente(conjunto):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    agora = timezone.now()
    carga(conjunto, [linha("1", "1")], started_at=agora - timedelta(hours=1))
    carga(conjunto, [linha("2", "2")], started_at=agora)
    assert normalizacao.normalize_latest(conjunto).created == 1
    assert list(modelo().objects.values_list("camara_proposition_id", flat=True)) == ["2"]


def test_normalize_latest_sem_carga_com_linhas_devolve_none(conjunto):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    assert normalizacao.normalize_latest(conjunto) is None
    carga(conjunto, [], rows_loaded=0)
    assert normalizacao.normalize_latest(conjunto) is None


def test_normalize_latest_de_carga_ja_normalizada_devolve_none(conjunto):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    carga(conjunto, [linha()])
    assert normalizacao.normalize_latest(conjunto).created == 1
    assert normalizacao.normalize_latest(conjunto) is None


@pytest.mark.parametrize(
    "estado",
    [
        {"state": IngestionRun.State.FAILED, "error_code": IngestionRun.ErrorCode.DOWNLOAD},
        {"state": IngestionRun.State.RUNNING, "finished_at": None},
    ],
    ids=["falhou", "em_andamento"],
)
def test_execucao_que_nao_terminou_bem_nao_e_a_carga_mais_recente(conjunto, estado):
    from apps.legislature import camara_tramitacao_normalization as normalizacao

    agora = timezone.now()
    carga(conjunto, [linha("1", "1")], started_at=agora)
    carga(conjunto, [linha("9", "9")], started_at=agora, **estado)
    assert normalizacao.normalize_latest(conjunto).created == 1
    assert not modelo().objects.filter(camara_proposition_id="9").exists()


def comando():
    saida = StringIO()
    call_command("normalize_camara_tramitacoes", stdout=saida, stderr=saida)
    return saida.getvalue()


def test_comando_normaliza_e_resume_so_com_contagens(conjunto):
    carga(conjunto, [linha("1", "1", descricaoTramitacao=SEGREDO), linha("2", "2")])
    saida = comando()
    assert "linhas lidas 2" in saida
    assert "criadas 2" in saida
    assert SEGREDO not in saida
    assert total() == 2


def test_comando_sem_o_conjunto_diz_o_que_falta(db):
    with pytest.raises(CommandError, match="camara/proposicoes-tramitacoes-2026"):
        comando()


def test_comando_sem_carga_manda_rodar_a_coleta(conjunto):
    with pytest.raises(CommandError, match="ingest_dataset"):
        comando()


def test_comando_repassa_a_recusa_sem_valores(conjunto):
    carga(conjunto, [linha(descricaoTramitacao=SEGREDO * 10)])
    with pytest.raises(CommandError) as erro:
        comando()
    assert SEGREDO not in str(erro.value)
    assert "descricaoTramitacao" in str(erro.value)


# --- encadeamento com o agendador (conjunto registrado em `settings.NORMALIZERS`) --------------


def test_o_agendador_normaliza_o_conjunto_depois_da_coleta_e_grava_o_estado(conjunto):
    from apps.sources import scheduling

    carga(conjunto, [linha()])
    agora = timezone.now()
    resultado = scheduling.Result()

    scheduling._normalize(conjunto, str(conjunto), resultado, agora)

    conjunto.refresh_from_db()
    assert (conjunto.last_normalization_error, conjunto.last_normalization_at) == ("", agora)
    assert total() == 1
    assert resultado.normalization_failed == 0
    assert any("normalizado, linhas lidas 1, criadas 1" in texto for texto in resultado.lines)


def test_recusa_no_agendador_grava_o_erro_no_conjunto(conjunto):
    from apps.sources import scheduling

    agora = timezone.now()
    carga(conjunto, [linha(siglaOrgao="X" * 31)])
    resultado = scheduling.Result()

    scheduling._normalize(conjunto, str(conjunto), resultado, agora)

    conjunto.refresh_from_db()
    assert "siglaOrgao" in conjunto.last_normalization_error
    assert resultado.normalization_failed == 1
    assert total() == 0


# --- admin -------------------------------------------------------------------------------------


def test_o_admin_e_so_leitura_e_os_campos_de_busca_existem_no_modelo():
    from django.contrib import admin

    registro = admin.site._registry[modelo()]
    assert not registro.has_add_permission(None)
    assert not registro.has_change_permission(None)
    assert not registro.has_delete_permission(None)
    assert registro.search_fields
    for campo in registro.search_fields:
        caminho = campo.lstrip("=^@")
        modelo().objects.filter(**{f"{caminho}__icontains": "x"}).exists()


# --- modelo ------------------------------------------------------------------------------------


def passo_duplicado(sequencia):
    run = carga(Dataset.objects.get(), [linha()])
    campos = {
        "camara_proposition_id": "1",
        "sequence": sequencia,
        "occurred_at": timezone.now(),
        "organ_code": "MESA",
        "description": "x",
        "ingestion_run": run,
    }
    modelo().objects.create(**campos)
    with pytest.raises(IntegrityError), transaction.atomic():
        modelo().objects.create(**campos)


def test_a_chave_e_unica_no_banco(conjunto):
    passo_duplicado(5)


def test_a_chave_e_unica_no_banco_tambem_com_sequencia_nula(conjunto):
    passo_duplicado(None)


def test_a_mesma_chave_com_sequencias_diferentes_cabe_no_banco(conjunto):
    run = carga(conjunto, [linha()])
    quando = timezone.now()
    for sequencia in (1, 2, None):
        modelo().objects.create(
            camara_proposition_id="1",
            sequence=sequencia,
            occurred_at=quando,
            organ_code="MESA",
            description="x",
            ingestion_run=run,
        )
    assert total() == 3


def test_o_conjunto_usa_so_a_allowlist_do_adr_0034():
    from apps.sources import catalog

    definicao = next(d for d in catalog.DATASETS if d["slug"] == "proposicoes-tramitacoes-2026")
    assert definicao["allowed_columns"] == COLUNAS
    assert definicao["internal_columns"] == []
