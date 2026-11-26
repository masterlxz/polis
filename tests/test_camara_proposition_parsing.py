"""Leitura de uma linha de `votacoesProposicoes-2026` e `votacoesObjetos-2026`, sem banco.

Valores no formato medido em 2026-11-26 (`fontes/camara.md`, Rodada 4): a primeira linha de
`votacoesProposicoes` (id 104333, "PL 11/2003") é cópia da fonte; o resto é sintético no mesmo
formato. O bruto guarda tudo como texto. Regras: `ementa` troca quebra de linha e TAB por espaço
(o TAB é o único controle real, 7 + 35 ocorrências) e recusa qualquer outro controle; `ementa`
vazia vale (404 proposições reais); `ano` vazio vira `None` (32.899 linhas de `votacoesObjetos`);
o erro cita só o NOME da coluna.

O módulo novo é importado dentro dos testes: antes de existir, cada teste falha por si e a coleta
do pytest não para.
"""

import pytest

EMENTA_REAL = (
    "Proíbe a veiculação de peças publicitárias, em qualquer meio de comunicação, "
    "que utilizem imagens sexuais como atrativo."
)


def linha(**extra):
    base = {
        "idVotacao": "104333-87",
        "proposicao_id": "104333",
        "proposicao_titulo": "PL 11/2003",
        "proposicao_ementa": EMENTA_REAL,
        "proposicao_siglaTipo": "PL",
        "proposicao_numero": "11",
        "proposicao_ano": "2003",
    }
    return {**base, **extra}


def ler(**extra):
    from apps.legislature.camara_proposition_parsing import parse_row

    return parse_row(linha(**extra))


def coluna_recusada(**extra):
    from apps.legislature.parsing import RowError

    with pytest.raises(RowError) as erro:
        ler(**extra)
    return erro.value.column


def test_linha_de_votacoes_proposicoes_vira_o_id_da_votacao_e_os_campos_da_proposicao():
    id_votacao, campos = ler()
    assert id_votacao == "104333-87"
    assert campos == {
        "camara_id": 104333,
        "title": "PL 11/2003",
        "type_acronym": "PL",
        "number": 11,
        "year": 2003,
        "ementa": EMENTA_REAL,
    }


def test_ano_vazio_vira_none_e_o_titulo_fica_inteiro():
    _, campos = ler(
        proposicao_id="2600556",
        proposicao_titulo="RDF 1 => MPV 1312/2025",
        proposicao_siglaTipo="RDF",
        proposicao_numero="1",
        proposicao_ano="",
    )
    assert campos["year"] is None
    assert campos["title"] == "RDF 1 => MPV 1312/2025"


@pytest.mark.parametrize(
    "bruto",
    ["a\nb", "a\r\nb", "a\rb", "a\tb", "a b", "a b"],
    ids=["lf", "crlf", "cr", "tab", "u2028", "u2029"],
)
def test_quebra_de_linha_e_tab_da_ementa_viram_um_espaco(bruto):
    assert ler(proposicao_ementa=bruto)[1]["ementa"] == "a b"


def test_ementa_vazia_e_aceita_como_vazia():
    assert ler(proposicao_ementa="")[1]["ementa"] == ""


def test_outro_caractere_de_controle_na_ementa_recusa_a_linha():
    assert coluna_recusada(proposicao_ementa="a\x07b") == "proposicao_ementa"


def test_ementa_no_teto_de_20000_caracteres_passa_e_com_um_a_mais_recusa():
    assert len(ler(proposicao_ementa="x" * 20_000)[1]["ementa"]) == 20_000
    assert coluna_recusada(proposicao_ementa="x" * 20_001) == "proposicao_ementa"


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("idVotacao", "104333"),
        ("idVotacao", "x-1"),
        ("idVotacao", "٣-1"),
        ("idVotacao", "9999999999-9999999999"),
        ("proposicao_id", "0"),
        ("proposicao_id", "-1"),
        ("proposicao_id", "1a"),
        ("proposicao_id", "١٢"),
        ("proposicao_id", "12345678901"),
        ("proposicao_id", ""),
        ("proposicao_titulo", ""),
        ("proposicao_titulo", "x" * 101),
        ("proposicao_siglaTipo", ""),
        ("proposicao_siglaTipo", "x" * 11),
        ("proposicao_numero", "-1"),
        ("proposicao_numero", "a"),
        ("proposicao_numero", ""),
        ("proposicao_ano", "20x6"),
        ("proposicao_ano", "-1"),
        ("proposicao_ano", "٢٠٢٦"),
    ],
)
def test_valor_invalido_recusa_a_linha_pelo_nome_da_coluna(coluna, valor):
    assert coluna_recusada(**{coluna: valor}) == coluna


def test_coluna_ausente_recusa_a_linha():
    from apps.legislature.camara_proposition_parsing import parse_row
    from apps.legislature.parsing import RowError

    bruto = linha()
    del bruto["proposicao_titulo"]
    with pytest.raises(RowError) as erro:
        parse_row(bruto)
    assert erro.value.column == "proposicao_titulo"


def test_a_mensagem_do_erro_nao_cita_o_valor():
    from apps.legislature.camara_proposition_parsing import parse_row
    from apps.legislature.parsing import RowError

    segredo = "valor-de-linha-que-nao-pode-vazar"
    with pytest.raises(RowError) as erro:
        parse_row(linha(proposicao_siglaTipo=segredo))
    assert segredo not in str(erro.value)
