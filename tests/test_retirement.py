"""Retirada pela fonte e lápide (ADR 0005, decisão 9), só para o TSE. Dados sintéticos.

Regras: candidatura que some de uma carga ÍNTEGRA (execução `succeeded` com linhas) é apagada,
junto com a pessoa se for a última, e com as linhas brutas do id nas cargas retidas; fica uma
lápide só com ids. Falha técnica e "arquivo igual" nunca apagam. Mais de `max(20, 1%)` retiradas
numa carga recusam a normalização inteira (disjuntor) até `--aceitar-retiradas`. Registro que
reaparece segue a fonte: volta e a lápide fica reativada. `apply_tombstones` reaplica as ativas
depois de um restore. Deputado da Câmara não é tocado (ADR 0022).
"""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.elections import normalization
from apps.elections.models import Candidacy, Election, Person
from apps.sources import models as sources_models
from apps.sources.catalog import DATASETS
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64

BASE = {
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


def ana():
    return dict(BASE)


def beto(turno=1):
    """Beto concorre à Presidência nos dois turnos (eleições diferentes, mesma pessoa)."""
    return {
        **BASE,
        "NR_TURNO": str(turno),
        "CD_ELEICAO": "6257" if turno == 1 else "6258",
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


def gente(numero):
    """Uma pessoa distinta por número, todas na mesma eleição."""
    return {
        **BASE,
        "SQ_CANDIDATO": str(2000000000 + numero),
        "NR_CANDIDATO": str(10000 + numero),
        "NM_URNA_CANDIDATO": f"Gente {numero}",
    }


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


def carga(dataset, linhas):
    run = IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.SUCCEEDED,
        finished_at=timezone.now(),
        sha256_original=HASH,
        rows_read=len(linhas),
        rows_loaded=len(linhas),
    )
    RawRecord.objects.bulk_create(
        [RawRecord(run=run, item_name="BRASIL.csv", values=v) for v in linhas]
    )
    return run


def carga_com_falha(dataset):
    return IngestionRun.objects.create(
        dataset=dataset,
        source_url=dataset.url,
        state=IngestionRun.State.FAILED,
        error_code=IngestionRun.ErrorCode.DOWNLOAD,
        finished_at=timezone.now(),
    )


def normalizar(*argumentos):
    saida = StringIO()
    call_command("normalize_tse", *argumentos, stdout=saida, stderr=saida)
    return saida.getvalue()


def reaplicar():
    saida = StringIO()
    call_command("apply_tombstones", stdout=saida, stderr=saida)
    return saida.getvalue()


def lapidas():
    """As lápides (`Tombstone` é lido só ao usar: cada teste falha por si, não a coleta)."""
    return sources_models.Tombstone.objects


ANA = "2026:1000000001:6259:1"
BETO_2O_TURNO = "2026:1000000002:6258:2"


# --- A retirada em si ---


def test_candidatura_ausente_de_carga_integra_apaga_tudo_e_deixa_a_lapide(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    assert (Person.objects.count(), Candidacy.objects.count()) == (2, 2)  # controle

    segunda = carga(dataset, [beto()])
    normalizar()

    assert list(Person.objects.values_list("public_name", flat=True)) == ["Beto da Urna"]
    assert Candidacy.objects.count() == 1
    lapide = lapidas().get()
    assert lapide.source_key == ANA
    assert lapide.dataset_id == dataset.pk
    assert lapide.retired_in_run_id == segunda.pk
    assert lapide.retired_at is not None
    assert lapide.reinstated_at is None


def test_normalizar_de_novo_a_mesma_carga_nao_duplica_a_lapide(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [beto()])
    normalizar()
    normalizar()
    assert lapidas().count() == 1


def test_pessoa_com_dois_turnos_so_perde_a_candidatura_retirada(dataset):
    carga(dataset, [beto(1), beto(2)])
    normalizar()
    carga(dataset, [beto(1)])
    normalizar()
    pessoa = Person.objects.get()
    assert pessoa.candidacies.count() == 1
    assert set(lapidas().values_list("source_key", flat=True)) == {BETO_2O_TURNO}


def test_linhas_brutas_do_id_somem_das_cargas_retidas_e_as_outras_ficam(dataset):
    primeira = carga(dataset, [ana(), beto()])
    normalizar()
    segunda = carga(dataset, [beto()])
    normalizar()
    nomes_na_primeira = {r.values["NM_URNA_CANDIDATO"] for r in primeira.raw_records.all()}
    assert nomes_na_primeira == {"Beto da Urna"}
    assert segunda.raw_records.count() == 1


# --- O que NUNCA apaga ---


def test_carga_que_falhou_nunca_apaga(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga_com_falha(dataset)
    normalizar()
    assert (Person.objects.count(), Candidacy.objects.count()) == (2, 2)
    assert lapidas().count() == 0


def test_arquivo_igual_com_zero_linhas_nunca_apaga(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [])
    normalizar()
    assert (Person.objects.count(), Candidacy.objects.count()) == (2, 2)
    assert lapidas().count() == 0


# --- O disjuntor: max(20, 1% das candidaturas já normalizadas) ---


def _carga_com_retiradas(dataset, total, retiradas):
    carga(dataset, [gente(i) for i in range(total)])
    normalizar()
    assert Candidacy.objects.count() == total  # controle
    # Entra uma pessoa nova na mesma carga, para provar que NADA é gravado se for recusada.
    return carga(dataset, [gente(i) for i in range(retiradas, total)] + [gente(total + 1)])


@pytest.mark.parametrize(
    ("total", "retiradas", "passa"),
    [
        (100, 20, True),  # no mínimo de 20: passa
        (100, 21, False),  # 21 > 20: recusa
        (2500, 25, True),  # 1% de 2500 = 25: passa
        (2500, 26, False),  # 26 > 25: recusa
    ],
)
def test_limite_exato_passa_e_um_a_mais_recusa(dataset, total, retiradas, passa):
    _carga_com_retiradas(dataset, total, retiradas)
    if passa:
        normalizar()
        assert lapidas().count() == retiradas
        assert Candidacy.objects.count() == total - retiradas + 1
        return
    with pytest.raises(CommandError) as erro:
        normalizar()
    assert "--aceitar-retiradas" in str(erro.value)
    assert lapidas().count() == 0
    assert Candidacy.objects.count() == total
    assert not Person.objects.filter(tse_candidate_id=2000000000 + total + 1).exists()


def test_mensagem_do_disjuntor_so_tem_contagens(dataset):
    _carga_com_retiradas(dataset, 100, 21)
    with pytest.raises(CommandError) as erro:
        normalizar()
    mensagem = str(erro.value)
    assert "21" in mensagem
    assert "Gente" not in mensagem
    assert "20000000" not in mensagem


def test_aceitar_retiradas_libera_o_que_o_disjuntor_segurou(dataset):
    _carga_com_retiradas(dataset, 100, 21)
    with pytest.raises(CommandError):
        normalizar()
    normalizar("--aceitar-retiradas")
    assert lapidas().count() == 21
    assert Candidacy.objects.count() == 100 - 21 + 1


def test_o_passo_encadeado_do_agendador_nunca_aceita_retiradas_acima_do_limite(dataset):
    _carga_com_retiradas(dataset, 100, 21)
    with pytest.raises(normalization.RetirementsHeld):
        normalization.normalize_latest(dataset)
    assert lapidas().count() == 0


# --- Reaparecimento segue a fonte; reaplicação após restore ---


def test_reaparecimento_recria_o_registro_e_reativa_a_lapide(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [beto()])
    normalizar()
    assert not Person.objects.filter(public_name="Ana da Urna").exists()  # controle

    carga(dataset, [ana(), beto()])
    normalizar()

    assert Person.objects.filter(public_name="Ana da Urna").exists()
    assert lapidas().get().reinstated_at is not None


def test_apply_tombstones_nao_apaga_o_que_foi_reativado(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [beto()])
    normalizar()
    carga(dataset, [ana(), beto()])
    normalizar()
    reaplicar()
    assert Person.objects.filter(public_name="Ana da Urna").exists()


def test_retirar_de_novo_depois_de_reativar_torna_a_lapide_ativa(dataset):
    carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [beto()])
    normalizar()
    carga(dataset, [ana(), beto()])
    normalizar()
    quarta = carga(dataset, [beto()])
    normalizar()
    lapide = lapidas().get()
    assert lapide.reinstated_at is None
    assert lapide.retired_in_run_id == quarta.pk
    assert not Person.objects.filter(public_name="Ana da Urna").exists()


def test_restore_simulado_apply_tombstones_apaga_de_novo_e_e_idempotente(dataset):
    primeira = carga(dataset, [ana(), beto()])
    normalizar()
    carga(dataset, [beto()])
    normalizar()

    # Simula um backup antigo restaurado: o dado que a fonte retirou volta ao banco.
    eleicao = Election.objects.get(tse_code=6259)
    pessoa = Person.objects.create(
        cycle_year=2026, tse_candidate_id=1000000001, public_name="Ana da Urna"
    )
    Candidacy.objects.create(
        election=eleicao,
        person=pessoa,
        ballot_number=12345,
        office_code=6,
        office_name="DEPUTADO FEDERAL",
        scope="ESTADUAL",
        state="SP",
        electoral_unit_code="SP",
        electoral_unit_name="SÃO PAULO",
        party_number=12,
        party_acronym="XYZ",
        party_name="Partido de Teste",
        ingestion_run=primeira,
        source_generated_at=timezone.now(),
    )
    RawRecord.objects.create(run=primeira, item_name="BRASIL.csv", values=ana())

    saida = reaplicar()
    assert "candidaturas apagadas 1" in saida
    assert not Person.objects.filter(public_name="Ana da Urna").exists()
    assert not RawRecord.objects.filter(values__SQ_CANDIDATO="1000000001").exists()
    assert Person.objects.filter(public_name="Beto da Urna").exists()

    assert "candidaturas apagadas 0" in reaplicar()


# --- O que o público vê ---


def test_pessoa_retirada_some_do_perfil_e_da_busca(dataset, client):
    carga(dataset, [ana(), beto()])
    normalizar()
    perfil = "/internal/v1/pessoas/2026-1000000001/"
    assert client.get(perfil).status_code == 200  # controle
    assert "Ana da Urna" in client.get("/internal/v1/busca/?q=Ana").content.decode()  # controle

    carga(dataset, [beto()])
    normalizar()

    assert client.get(perfil).status_code == 404
    assert "Ana da Urna" not in client.get("/internal/v1/busca/?q=Ana").content.decode()


# --- Deputado da Câmara não é tocado (ADR 0022: sumir da lista de exercício não é retirada) ---


def deputado(id, nome):
    return {
        "id": id,
        "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{id}",
        "nome": nome,
        "siglaPartido": "XYZ",
        "siglaUf": "SP",
        "idLegislatura": 57,
    }


def test_deputado_que_some_da_lista_de_exercicio_continua_e_nao_gera_lapide():
    from apps.legislature.models import Deputy

    fonte = Source.objects.create(
        slug="camara",
        name="Câmara",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    camara = Dataset.objects.create(
        source=fonte,
        slug="deputados",
        name="Deputados em exercício",
        url="https://example.org/deputados",
        format=Dataset.Format.JSON,
        allowed_columns=DATASETS[-1]["allowed_columns"],
    )
    carga(camara, [deputado(1, "Ana da Câmara"), deputado(2, "Beto da Câmara")])
    call_command("normalize_camara", stdout=StringIO())
    assert Deputy.objects.count() == 2  # controle

    carga(camara, [deputado(2, "Beto da Câmara")])
    call_command("normalize_camara", stdout=StringIO())

    assert Deputy.objects.count() == 2
    assert lapidas().count() == 0


# --- A lápide não guarda dado pessoal ---


def test_lapide_so_tem_campos_de_origem_e_datas():
    campos = {campo.name for campo in sources_models.Tombstone._meta.get_fields()}
    esperado = {"id", "dataset", "source_key", "retired_at", "retired_in_run", "reinstated_at"}
    assert campos == esperado
