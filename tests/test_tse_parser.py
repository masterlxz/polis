"""Leitura de uma linha do bruto do TSE (`apps/elections/tse.py`), sem banco.

Parsing de dado externo é código crítico (AGENTS §3, Etapa D): além dos casos de borda há um
fuzz com semente fixa. Todos os dados são sintéticos. A mensagem de erro só pode citar o NOME da
coluna, nunca o valor (a exceção de um parser costuma citar a linha, onde há dado pessoal).
"""

import random
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError

from apps.elections.models import Candidacy, Election, Person
from apps.sources.catalog import DATASETS

COLUNAS_DA_ALLOWLIST = DATASETS[0]["allowed_columns"]

LINHA_BASE = {
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
    "NM_URNA_CANDIDATO": "Fulano da Urna",
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

OBRIGATORIAS = [
    "DT_GERACAO",
    "HH_GERACAO",
    "ANO_ELEICAO",
    "CD_TIPO_ELEICAO",
    "NM_TIPO_ELEICAO",
    "NR_TURNO",
    "CD_ELEICAO",
    "DS_ELEICAO",
    "DT_ELEICAO",
    "TP_ABRANGENCIA",
    "SG_UF",
    "SG_UE",
    "NM_UE",
    "CD_CARGO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NR_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "NR_PARTIDO",
    "SG_PARTIDO",
    "NM_PARTIDO",
]

MARCADORES = ["#NULO", "#NULO#", "#NE", "#NE#", "-1", "-3", "-4", "NÃO DIVULGÁVEL", "", "   "]


def linha(**mudancas):
    return {**LINHA_BASE, **mudancas}


def test_a_linha_base_cobre_exatamente_a_allowlist_do_catalogo():
    assert set(LINHA_BASE) == set(COLUNAS_DA_ALLOWLIST)


def test_linha_valida_vira_campos_tipados(tse):
    resultado = tse.parse_row(LINHA_BASE)
    assert resultado.election == {
        "tse_code": 6259,
        "round": 1,
        "year": 2026,
        "kind_code": 2,
        "kind_name": "Eleição Ordinária",
        "description": "Eleições Gerais Estaduais 2026",
        "date": date(2026, 10, 4),
    }
    assert resultado.person == {
        "cycle_year": 2026,
        "tse_candidate_id": 1000000001,
        "public_name": "Fulano da Urna",
        "social_name": "",
    }
    assert resultado.candidacy["ballot_number"] == 12345
    assert resultado.candidacy["office_code"] == 6
    assert resultado.candidacy["state"] == "SP"
    assert resultado.candidacy["party_acronym"] == "XYZ"
    assert resultado.candidacy["coalition_name"] == "PARTIDO ISOLADO"


def test_data_e_hora_de_geracao_viram_um_instante_em_horario_de_brasilia(tse):
    resultado = tse.parse_row(LINHA_BASE)
    esperado = datetime(2026, 11, 8, 20, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo"))
    assert resultado.candidacy["source_generated_at"] == esperado


@pytest.mark.parametrize("marcador", MARCADORES)
def test_marcadores_do_tse_nos_campos_opcionais_viram_ausentes(tse, marcador):
    resultado = tse.parse_row(
        linha(
            NM_SOCIAL_CANDIDATO=marcador,
            CD_SITUACAO_CANDIDATURA=marcador,
            DS_SITUACAO_CANDIDATURA=marcador,
            SG_FEDERACAO=marcador,
            NM_FEDERACAO=marcador,
            NM_COLIGACAO=marcador,
            DS_COMPOSICAO_COLIGACAO=marcador,
            CD_SIT_TOT_TURNO=marcador,
            DS_SIT_TOT_TURNO=marcador,
        )
    )
    assert resultado.person["social_name"] == ""
    assert resultado.candidacy["status_code"] is None
    assert resultado.candidacy["status_name"] == ""
    assert resultado.candidacy["federation_acronym"] == ""
    assert resultado.candidacy["federation_name"] == ""
    assert resultado.candidacy["coalition_name"] == ""
    assert resultado.candidacy["coalition_composition"] == ""
    assert resultado.candidacy["result_code"] is None
    assert resultado.candidacy["result_name"] == ""


def test_codigos_reais_de_situacao_e_resultado_sao_preservados(tse):
    resultado = tse.parse_row(
        linha(
            CD_SITUACAO_CANDIDATURA="2",
            DS_SITUACAO_CANDIDATURA="DEFERIDO",
            CD_SIT_TOT_TURNO="1",
            DS_SIT_TOT_TURNO="ELEITO",
        )
    )
    assert resultado.candidacy["status_code"] == 2
    assert resultado.candidacy["status_name"] == "DEFERIDO"
    assert resultado.candidacy["result_code"] == 1
    assert resultado.candidacy["result_name"] == "ELEITO"


def test_nome_social_e_guardado_no_campo_interno_e_nunca_vira_nome_publico(tse):
    resultado = tse.parse_row(linha(NM_SOCIAL_CANDIDATO="Nome Social de Teste"))
    assert resultado.person["social_name"] == "Nome Social de Teste"
    assert resultado.person["public_name"] == "Fulano da Urna"


def test_nome_social_nao_divulgavel_nao_e_guardado(tse):
    resultado = tse.parse_row(linha(NM_SOCIAL_CANDIDATO="NÃO DIVULGÁVEL"))
    assert resultado.person["social_name"] == ""


@pytest.mark.parametrize("coluna", OBRIGATORIAS)
@pytest.mark.parametrize("marcador", ["#NULO", "#NE", "-1", "NÃO DIVULGÁVEL", ""])
def test_marcador_num_campo_obrigatorio_e_recusado(tse, coluna, marcador):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(**{coluna: marcador}))
    assert erro.value.column == coluna


@pytest.mark.parametrize("coluna", OBRIGATORIAS)
def test_coluna_obrigatoria_ausente_e_recusada(tse, coluna):
    valores = {k: v for k, v in LINHA_BASE.items() if k != coluna}
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(valores)
    assert erro.value.column == coluna


@pytest.mark.parametrize("valor", [None, 7, 1.5, ["a"], {"a": 1}, True])
def test_valor_que_nao_e_texto_e_recusado(tse, valor):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(NM_URNA_CANDIDATO=valor))
    assert erro.value.column == "NM_URNA_CANDIDATO"


@pytest.mark.parametrize(
    "numero",
    [
        "12a",
        "1_0",  # `int("1_0")` do Python aceita sublinhado
        "١٢٣",  # dígitos arábico-índicos: `str.isdigit()` aceitaria
        "²",
        "-5",
        "+7",
        "1.5",
        "0x10",
        " 7 8",
        "9" * 30,
        "99999999999",  # estoura o inteiro de 32 bits do número de urna
    ],
)
def test_numero_invalido_ou_fora_da_faixa_e_recusado(tse, numero):
    for coluna in ("NR_CANDIDATO", "CD_CARGO", "NR_PARTIDO", "NR_TURNO", "CD_ELEICAO"):
        with pytest.raises(tse.RowError) as erro:
            tse.parse_row(linha(**{coluna: numero}))
        assert erro.value.column == coluna


@pytest.mark.parametrize(
    "data",
    ["31/02/2026", "2026-10-04", "4/10/2026", "04/10/26", "00/00/0000", "04-10-2026", "abc"],
)
def test_data_invalida_e_recusada(tse, data):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(DT_ELEICAO=data))
    assert erro.value.column == "DT_ELEICAO"


@pytest.mark.parametrize("hora", ["25:00:00", "20:60:00", "20:00", "8h", "20:00:00:00"])
def test_hora_de_geracao_invalida_e_recusada(tse, hora):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(HH_GERACAO=hora))
    assert erro.value.column == "HH_GERACAO"


def test_texto_acima_do_tamanho_do_campo_e_recusado_antes_do_banco(tse):
    limite = Person._meta.get_field("public_name").max_length
    assert tse.parse_row(linha(NM_URNA_CANDIDATO="a" * limite)).person["public_name"]
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(NM_URNA_CANDIDATO="a" * (limite + 1)))
    assert erro.value.column == "NM_URNA_CANDIDATO"


def test_composicao_da_coligacao_tem_um_teto_mesmo_sendo_texto_livre(tse):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(DS_COMPOSICAO_COLIGACAO="x" * 100_000))
    assert erro.value.column == "DS_COMPOSICAO_COLIGACAO"


@pytest.mark.parametrize("controle", ["\x00", "\x1f", "\x7f", "a\nb", "a\rb", "a\tb", "\x85"])
def test_caractere_de_controle_e_recusado(tse, controle):
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(NM_URNA_CANDIDATO=f"Nome{controle}Teste"))
    assert erro.value.column == "NM_URNA_CANDIDATO"


@pytest.mark.parametrize("nome", ["José D'Ávila", 'Maria; da "Silva"', "Nome com 😀", "ǅ ÇÃO"])
def test_nome_com_aspas_ponto_e_virgula_acento_e_emoji_e_aceito_intacto(tse, nome):
    assert tse.parse_row(linha(NM_URNA_CANDIDATO=nome)).person["public_name"] == nome


def test_espacos_nas_pontas_sao_removidos(tse):
    resultado = tse.parse_row(linha(NM_URNA_CANDIDATO="  Fulano da Urna  "))
    assert resultado.person["public_name"] == "Fulano da Urna"


def test_o_erro_cita_so_o_nome_da_coluna_nunca_o_valor(tse):
    valor = "VALOR-SECRETO-QUE-NAO-PODE-VAZAR"
    with pytest.raises(tse.RowError) as erro:
        tse.parse_row(linha(NR_CANDIDATO=valor))
    assert valor not in str(erro.value)
    assert valor not in repr(erro.value)
    assert "NR_CANDIDATO" in str(erro.value)
    assert erro.value.__cause__ is None


# --- Fuzz com semente fixa (sem dependência nova; reproduzível) ---

SEMENTE = 20261109
VALORES_HOSTIS = [
    "",
    " ",
    "#NULO",
    "#NE",
    "-1",
    "-3",
    "-4",
    "NÃO DIVULGÁVEL",
    "0",
    "-0",
    "1_0",
    "١٢٣",
    "9" * 40,
    "12abc",
    "a;b",
    'a"b',
    "x" * 5000,
    "\x00",
    "\x1f",
    "a\nb",
    "31/02/2026",
    "2026-10-04",
    "04/10/2026",
    "99:99:99",
    "😀",
    "ǅ",
    "‮",
    "﻿",
    None,
    7,
]


def _linha_aleatoria(rng):
    valores = dict(LINHA_BASE)
    for coluna in rng.sample(sorted(valores), rng.randint(1, 4)):
        escolha = rng.random()
        if escolha < 0.1:
            del valores[coluna]
        else:
            valores[coluna] = rng.choice(VALORES_HOSTIS)
    return valores


def test_fuzz_a_linha_ou_vira_campos_validos_ou_e_recusada_sem_vazar_valor(tse):
    rng = random.Random(SEMENTE)  # noqa: S311 (fuzz reproduzível, não é criptografia)
    aceitas = recusadas = 0
    for _ in range(3000):
        valores = _linha_aleatoria(rng)
        try:
            resultado = tse.parse_row(valores)
        except tse.RowError as erro:
            recusadas += 1
            assert erro.column in COLUNAS_DA_ALLOWLIST
            assert str(erro) == f"coluna inválida: {erro.column}"
            continue
        aceitas += 1
        # Tudo que o parser aceita tem de caber nos campos do banco: nenhum erro de banco
        # (cuja mensagem poderia citar valores) pode ser a primeira defesa.
        Election(**resultado.election).clean_fields()
        Person(**resultado.person).clean_fields()
        Candidacy(**resultado.candidacy).clean_fields(
            exclude=["election", "person", "ingestion_run"]
        )
    assert aceitas > 100 and recusadas > 100


def test_fuzz_o_proprio_teste_detecta_um_campo_fora_do_limite():
    with pytest.raises(ValidationError):
        Person(cycle_year=2026, tse_candidate_id=1, public_name="a" * 101).clean_fields()
