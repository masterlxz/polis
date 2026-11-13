"""Testes do cadastro inicial (`seed_sources`) e da allowlist do TSE (ADR 0005 e 0008).

A lista de 50 colunas é o esquema medido de `consulta_cand_2026` (project/fontes/tse.md).
"""

from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.sources import catalog
from apps.sources.models import Dataset, Source
from apps.sources.zip_csv import ZipCsvReader

pytestmark = pytest.mark.django_db

ESQUEMA_MEDIDO = (
    "DT_GERACAO HH_GERACAO ANO_ELEICAO CD_TIPO_ELEICAO NM_TIPO_ELEICAO NR_TURNO CD_ELEICAO "
    "DS_ELEICAO DT_ELEICAO TP_ABRANGENCIA SG_UF SG_UE NM_UE CD_CARGO DS_CARGO SQ_CANDIDATO "
    "NR_CANDIDATO NM_CANDIDATO NM_URNA_CANDIDATO NM_SOCIAL_CANDIDATO NR_CPF_CANDIDATO DS_EMAIL "
    "CD_SITUACAO_CANDIDATURA DS_SITUACAO_CANDIDATURA TP_AGREMIACAO NR_PARTIDO SG_PARTIDO "
    "NM_PARTIDO NR_FEDERACAO NM_FEDERACAO SG_FEDERACAO DS_COMPOSICAO_FEDERACAO SQ_COLIGACAO "
    "NM_COLIGACAO DS_COMPOSICAO_COLIGACAO SG_UF_NASCIMENTO DT_NASCIMENTO "
    "NR_TITULO_ELEITORAL_CANDIDATO CD_GENERO DS_GENERO CD_GRAU_INSTRUCAO DS_GRAU_INSTRUCAO "
    "CD_ESTADO_CIVIL DS_ESTADO_CIVIL CD_COR_RACA DS_COR_RACA CD_OCUPACAO DS_OCUPACAO "
    "CD_SIT_TOT_TURNO DS_SIT_TOT_TURNO"
).split()

# ADR 0005: decisão 1 (CPF, título, e-mail), decisão 4 (demográficos) e decisão do dono de
# não coletar ainda o nome civil, a data e a UF de nascimento (sem ligação entre fontes).
EXCLUIDAS = {
    "NR_CPF_CANDIDATO",
    "DS_EMAIL",
    "NR_TITULO_ELEITORAL_CANDIDATO",
    "CD_GENERO",
    "DS_GENERO",
    "CD_GRAU_INSTRUCAO",
    "DS_GRAU_INSTRUCAO",
    "CD_ESTADO_CIVIL",
    "DS_ESTADO_CIVIL",
    "CD_COR_RACA",
    "DS_COR_RACA",
    "CD_OCUPACAO",
    "DS_OCUPACAO",
    "NM_CANDIDATO",
    "DT_NASCIMENTO",
    "SG_UF_NASCIMENTO",
}

URL_TSE = "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip"


def seed():
    saida = StringIO()
    call_command("seed_sources", stdout=saida)
    return saida.getvalue()


def dataset_tse():
    return Dataset.objects.get(source__slug="tse", slug="consulta-cand-2026")


# --- Contrato da allowlist (ADR 0005, decisões 1 e 4) ---


def test_o_esquema_medido_tem_50_colunas_sem_repeticao():
    assert len(ESQUEMA_MEDIDO) == 50
    assert len(set(ESQUEMA_MEDIDO)) == 50


def test_allowlist_do_tse_tem_34_colunas_sem_repeticao():
    colunas = catalog.DATASETS[0]["allowed_columns"]
    assert len(colunas) == 34
    assert len(set(colunas)) == 34


def test_allowlist_so_usa_colunas_do_esquema_medido():
    colunas = catalog.DATASETS[0]["allowed_columns"]
    assert set(colunas) <= set(ESQUEMA_MEDIDO)


def test_allowlist_nao_traz_nenhuma_das_16_colunas_excluidas():
    colunas = set(catalog.DATASETS[0]["allowed_columns"])
    assert colunas & EXCLUIDAS == set()
    assert colunas == set(ESQUEMA_MEDIDO) - EXCLUIDAS


def test_allowlist_mantem_identificacao_publica_e_situacao():
    colunas = set(catalog.DATASETS[0]["allowed_columns"])
    assert {"SQ_CANDIDATO", "NM_URNA_CANDIDATO", "NM_SOCIAL_CANDIDATO"} <= colunas
    assert {"SG_PARTIDO", "DS_CARGO", "DS_SITUACAO_CANDIDATURA", "DS_SIT_TOT_TURNO"} <= colunas
    assert {"DT_GERACAO", "HH_GERACAO"} <= colunas


def test_nenhuma_coluna_interna_por_enquanto():
    assert catalog.DATASETS[0]["internal_columns"] == []


def test_o_leitor_aceita_a_allowlist_do_catalogo():
    ZipCsvReader("nao-importa.zip", catalog.DATASETS[0]["allowed_columns"])


# --- O que o seed cria ---


def test_seed_cria_as_tres_fontes_e_os_conjuntos_do_tse_da_camara_e_do_senado():
    seed()
    assert set(Source.objects.values_list("slug", flat=True)) == {"camara", "senado", "tse"}
    assert {str(d) for d in Dataset.objects.all()} == {
        "tse/consulta-cand-2026",
        "camara/deputados",
        "senado/senadores",
        "senado/votacoes",
    }
    assert str(dataset_tse()) == "tse/consulta-cand-2026"


def test_os_conjuntos_sem_licenca_declarada_nascem_desabilitados_e_sem_justificativa():
    seed()
    conjuntos = Dataset.objects.filter(source__slug__in=("camara", "senado"))
    assert conjuntos.count() == 3
    for conjunto in conjuntos:
        assert conjunto.enabled is False
        assert conjunto.license_basis == Dataset.LicenseBasis.OWNER_DECISION
        assert conjunto.license_justification == "", "a justificativa é do dono, no admin"


def test_votacoes_do_senado_so_leem_a_allowlist_combinada_e_coletam_uma_vez_por_dia():
    seed()
    votacoes = Dataset.objects.get(source__slug="senado", slug="votacoes")
    assert votacoes.format == Dataset.Format.JSON_SENADO_VOTACOES
    assert votacoes.url == "https://legis.senado.leg.br/dadosabertos/votacao"
    assert votacoes.allowed_columns == [
        "codigoSessaoVotacao",
        "dataSessao",
        "sigla",
        "numero",
        "ano",
        "identificacao",
        "ementa",
        "resultadoVotacao",
        "votacaoSecreta",
        "totalVotosSim",
        "totalVotosNao",
        "totalVotosAbstencao",
        "idProcesso",
        "codigoMateria",
        "codigoParlamentar",
        "nomeParlamentar",
        "siglaPartidoParlamentar",
        "siglaUFParlamentar",
        "siglaVotoParlamentar",
    ]
    # Minimização (ADR 0005): sexo, texto livre do voto e o informe legislativo ficam de fora.
    for fora in ("sexoParlamentar", "descricaoVotoParlamentar", "informeLegislativo"):
        assert fora not in votacoes.allowed_columns
    assert votacoes.internal_columns == []
    assert votacoes.schedule_interval_hours == 24
    assert votacoes.earliest_hour_utc == 8


def test_o_agendador_normaliza_as_votacoes_do_senado_depois_da_coleta():
    assert (
        settings.NORMALIZERS["senado/votacoes"]
        == "apps.legislature.senate_voting_normalization.normalize_latest"
    )


def test_fontes_nascem_medidas_e_sem_integracao():
    seed()
    assert set(Source.objects.values_list("status", flat=True)) == {Source.Status.MEASURED}


def test_conjunto_nasce_desabilitado_com_licenca_declarada():
    seed()
    dataset = dataset_tse()
    assert dataset.enabled is False
    assert dataset.license_basis == Dataset.LicenseBasis.DECLARED
    assert dataset.license_id == "cc-by"
    assert dataset.license_url == "http://www.opendefinition.org/licenses/cc-by"
    assert dataset.format == Dataset.Format.ZIP_CSV
    assert dataset.url == URL_TSE
    assert dataset.allowed_columns == catalog.DATASETS[0]["allowed_columns"]


def test_conjunto_do_tse_aponta_para_o_pacote_do_ckan_que_declara_a_licenca():
    seed()
    assert dataset_tse().license_check_url == (
        "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2026"
    )


def test_registros_criados_passam_na_validacao_do_modelo():
    seed()
    for fonte in Source.objects.all():
        fonte.full_clean()
    dataset = dataset_tse()
    dataset.full_clean()


def test_toda_fonte_tem_termos_em_https_e_nota_de_licenca():
    seed()
    for fonte in Source.objects.all():
        assert fonte.terms_url.startswith("https://")
        assert fonte.license_note.strip() != ""
        assert fonte.official_url.startswith("https://")


def test_seed_resume_so_com_contagens():
    texto = seed()
    assert "3" in texto
    assert "NR_CPF" not in texto


# --- Idempotência e respeito às decisões do dono ---


def test_segunda_execucao_nao_duplica_nem_cria():
    seed()
    texto = seed()
    assert Source.objects.count() == 3
    assert Dataset.objects.count() == 4
    assert "0 criad" in texto


def test_seed_nao_sobrescreve_status_nem_habilitacao_do_dono():
    seed()
    Source.objects.filter(slug="tse").update(status=Source.Status.PAUSED)
    Dataset.objects.filter(source__slug="tse").update(enabled=True)
    seed()
    assert Source.objects.get(slug="tse").status == Source.Status.PAUSED
    assert dataset_tse().enabled is True


def test_seed_nao_sobrescreve_observacoes_nem_a_licenca_registrada():
    seed()
    Source.objects.filter(slug="tse").update(notes="anotação do dono")
    Dataset.objects.update(
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_id="",
        license_url="",
        license_justification="Decisão do dono em 2026-11-07.",
    )
    seed()
    assert Source.objects.get(slug="tse").notes == "anotação do dono"
    dataset = dataset_tse()
    assert dataset.license_basis == Dataset.LicenseBasis.OWNER_DECISION
    assert dataset.license_id == ""
    assert dataset.license_url == ""
    assert dataset.license_justification == "Decisão do dono em 2026-11-07."


def test_seed_restaura_campos_descritivos_alterados_no_banco():
    seed()
    Source.objects.filter(slug="tse").update(official_url="https://errado.example.org")
    Dataset.objects.update(name="outro nome", url="https://errado.example.org/a.zip")
    seed()
    assert Source.objects.get(slug="tse").official_url == "https://dadosabertos.tse.jus.br"
    assert dataset_tse().url == URL_TSE
    assert dataset_tse().name != "outro nome"


def test_seed_aplica_mudanca_da_allowlist_do_catalogo(monkeypatch):
    seed()
    nova = {**catalog.DATASETS[0], "allowed_columns": ["SQ_CANDIDATO", "NM_URNA_CANDIDATO"]}
    monkeypatch.setattr(catalog, "DATASETS", [nova])
    texto = seed()
    assert dataset_tse().allowed_columns == ["SQ_CANDIDATO", "NM_URNA_CANDIDATO"]
    assert "1 atualiz" in texto
