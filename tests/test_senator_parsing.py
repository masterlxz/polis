"""Leitura de uma linha do bruto de `senado/senadores`, sem banco (ADR 0028).

Dado externo: o que sai do parser já cabe no modelo, e o erro cita só o NOME da coluna, nunca o
valor. Falha fechada (ADR 0005, decisão 6). O bruto guarda TUDO como texto (o leitor JSON converte
número em texto), então o código do parlamentar chega como "5895", não como inteiro.
"""

import pytest

VALIDA = {
    "CodigoParlamentar": "5895",
    "NomeParlamentar": "Ana do Senado",
    "SiglaPartidoParlamentar": "XYZ",
    "UfParlamentar": "SP",
}


@pytest.fixture
def parsing():
    from apps.legislature import senate_parsing as modulo

    return modulo


def linha(**mudancas):
    return {**VALIDA, **mudancas}


def sem(coluna):
    return {k: v for k, v in VALIDA.items() if k != coluna}


def test_linha_valida_vira_os_campos_do_modelo(parsing):
    assert parsing.parse_row(VALIDA) == {
        "senate_id": 5895,
        "name": "Ana do Senado",
        "party_acronym": "XYZ",
        "state": "SP",
    }


def test_nome_e_sigla_perdem_espacos_nas_pontas(parsing):
    row = parsing.parse_row(
        linha(NomeParlamentar="  Ana do Senado ", SiglaPartidoParlamentar=" X ")
    )
    assert (row["name"], row["party_acronym"]) == ("Ana do Senado", "X")


def test_partido_vazio_ou_nulo_e_aceito_como_vazio(parsing):
    assert parsing.parse_row(linha(SiglaPartidoParlamentar=""))["party_acronym"] == ""
    assert parsing.parse_row(linha(SiglaPartidoParlamentar=None))["party_acronym"] == ""


@pytest.mark.parametrize(
    "valores",
    [
        sem("CodigoParlamentar"),
        linha(CodigoParlamentar=None),
        linha(CodigoParlamentar=""),
        linha(CodigoParlamentar=" "),
        linha(CodigoParlamentar="58a5"),
        linha(CodigoParlamentar="58.5"),
        linha(CodigoParlamentar="-7"),
        linha(CodigoParlamentar="0"),
        linha(CodigoParlamentar="0x1F"),
        linha(CodigoParlamentar="٥٨٩٥"),
        linha(CodigoParlamentar="9" * 20),
        linha(CodigoParlamentar=5895),
        linha(CodigoParlamentar=True),
    ],
    ids=[
        "ausente",
        "nulo",
        "vazio",
        "espaco",
        "letra",
        "decimal",
        "negativo",
        "zero",
        "hexadecimal",
        "digitos_nao_ascii",
        "enorme",
        "inteiro_fora_do_bruto",
        "booleano",
    ],
)
def test_codigo_invalido_recusa_citando_so_o_codigo(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "CodigoParlamentar"


@pytest.mark.parametrize(
    "valores",
    [
        sem("UfParlamentar"),
        linha(UfParlamentar=None),
        linha(UfParlamentar=""),
        linha(UfParlamentar="sp"),
        linha(UfParlamentar="SPP"),
        linha(UfParlamentar="S1"),
        linha(UfParlamentar=35),
    ],
    ids=["ausente", "nulo", "vazio", "minuscula", "tres_letras", "digito", "numero"],
)
def test_uf_invalida_recusa_citando_ufparlamentar(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "UfParlamentar"


@pytest.mark.parametrize(
    "valores",
    [
        sem("NomeParlamentar"),
        linha(NomeParlamentar=None),
        linha(NomeParlamentar=""),
        linha(NomeParlamentar="   "),
        linha(NomeParlamentar="Ana\x00do Senado"),
        linha(NomeParlamentar="Ana\ndo Senado"),
        linha(NomeParlamentar="A" * 101),
        linha(NomeParlamentar=123),
    ],
    ids=["ausente", "nulo", "vazio", "so_espacos", "nul", "quebra_de_linha", "longo", "numero"],
)
def test_nome_invalido_recusa_citando_nomeparlamentar(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "NomeParlamentar"


@pytest.mark.parametrize(
    "valores",
    [
        linha(SiglaPartidoParlamentar="X" * 21),
        linha(SiglaPartidoParlamentar=12),
        linha(SiglaPartidoParlamentar="X\x00Y"),
    ],
    ids=["longa", "numero", "controle"],
)
def test_partido_invalido_recusa_citando_siglapartidoparlamentar(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "SiglaPartidoParlamentar"


def test_o_erro_nunca_cita_o_valor_recusado(parsing):
    segredo = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(linha(NomeParlamentar=segredo * 10))
    assert segredo not in str(erro.value)
    assert erro.value.__cause__ is None and erro.value.__context__ is None
