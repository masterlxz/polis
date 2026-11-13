"""Leitura de uma linha do bruto de `camara/deputados`, sem banco (ADR 0021, Sessão 54).

Dado externo: o que sai do parser já cabe no modelo, e o erro cita só o NOME da coluna, nunca o
valor. Falha fechada (ADR 0005, decisão 6).
"""

import pytest

VALIDA = {
    "id": 204554,
    "uri": "https://dadosabertos.camara.leg.br/api/v2/deputados/204554",
    "nome": "Ana da Câmara",
    "siglaPartido": "XYZ",
    "siglaUf": "SP",
    "idLegislatura": 57,
}


@pytest.fixture
def parsing():
    from apps.legislature import parsing as modulo

    return modulo


def linha(**mudancas):
    return {**VALIDA, **mudancas}


def sem(coluna):
    return {k: v for k, v in VALIDA.items() if k != coluna}


def test_linha_valida_vira_os_campos_do_modelo(parsing):
    assert parsing.parse_row(VALIDA) == {
        "legislature_id": 57,
        "camara_id": 204554,
        "name": "Ana da Câmara",
        "party_acronym": "XYZ",
        "state": "SP",
    }


def test_o_bruto_real_guarda_numero_como_texto_e_o_parser_converte(parsing):
    """O leitor JSON grava `id` e `idLegislatura` como texto; é essa a forma que chega aqui."""
    row = parsing.parse_row(linha(id="204554", idLegislatura="57"))
    assert (row["camara_id"], row["legislature_id"]) == (204554, 57)


def test_nome_e_sigla_perdem_espacos_nas_pontas(parsing):
    row = parsing.parse_row(linha(nome="  Ana da Câmara ", siglaPartido=" XYZ "))
    assert (row["name"], row["party_acronym"]) == ("Ana da Câmara", "XYZ")


def test_partido_vazio_ou_nulo_e_aceito_como_vazio(parsing):
    assert parsing.parse_row(linha(siglaPartido=""))["party_acronym"] == ""
    assert parsing.parse_row(linha(siglaPartido=None))["party_acronym"] == ""


@pytest.mark.parametrize(
    "valores",
    [
        sem("id"),
        linha(id=None),
        linha(id=""),
        linha(id=" "),
        linha(id="20a4"),
        linha(id="2045.5"),
        linha(id="-7"),
        linha(id="0"),
        linha(id="0x1F"),
        linha(id="٥٨٩٥"),
        linha(id="9" * 20),
        linha(id=2045.5),
        linha(id=True),
        linha(id=0),
        linha(id=-7),
        linha(id=2**63),
    ],
    ids=[
        "ausente",
        "nulo",
        "vazio",
        "espaco",
        "letra",
        "texto_decimal",
        "texto_negativo",
        "texto_zero",
        "hexadecimal",
        "digitos_nao_ascii",
        "texto_enorme",
        "decimal",
        "booleano",
        "zero",
        "negativo",
        "enorme",
    ],
)
def test_id_invalido_recusa_citando_so_a_coluna_id(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "id"


@pytest.mark.parametrize(
    "valores",
    [
        sem("idLegislatura"),
        linha(idLegislatura=None),
        linha(idLegislatura="5x"),
        linha(idLegislatura="-1"),
        linha(idLegislatura=True),
        linha(idLegislatura=0),
        linha(idLegislatura=-1),
    ],
    ids=["ausente", "nulo", "letra", "texto_negativo", "booleano", "zero", "negativo"],
)
def test_legislatura_invalida_recusa_citando_idlegislatura(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "idLegislatura"


@pytest.mark.parametrize(
    "valores",
    [
        sem("siglaUf"),
        linha(siglaUf=None),
        linha(siglaUf=""),
        linha(siglaUf="sp"),
        linha(siglaUf="SPP"),
        linha(siglaUf="S"),
        linha(siglaUf="S1"),
        linha(siglaUf=35),
    ],
    ids=["ausente", "nulo", "vazio", "minuscula", "tres_letras", "uma_letra", "digito", "numero"],
)
def test_uf_invalida_recusa_citando_siglauf(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "siglaUf"


@pytest.mark.parametrize(
    "valores",
    [
        sem("nome"),
        linha(nome=None),
        linha(nome=""),
        linha(nome="   "),
        linha(nome="Ana\x00da Câmara"),
        linha(nome="Ana\nda Câmara"),
        linha(nome="A" * 101),
        linha(nome=123),
    ],
    ids=["ausente", "nulo", "vazio", "so_espacos", "nul", "quebra_de_linha", "longo", "numero"],
)
def test_nome_invalido_recusa_citando_nome(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "nome"


@pytest.mark.parametrize(
    "valores",
    [linha(siglaPartido="X" * 21), linha(siglaPartido=12), linha(siglaPartido="X\x00Y")],
    ids=["longa", "numero", "controle"],
)
def test_partido_invalido_recusa_citando_siglapartido(parsing, valores):
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(valores)
    assert erro.value.column == "siglaPartido"


def test_o_erro_nunca_cita_o_valor_recusado(parsing):
    segredo = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"
    with pytest.raises(parsing.RowError) as erro:
        parsing.parse_row(linha(nome=segredo * 10))
    assert segredo not in str(erro.value)
    assert erro.value.__cause__ is None and erro.value.__context__ is None
