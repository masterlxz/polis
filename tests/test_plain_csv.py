"""Testes de contrato do leitor de CSV simples (ADR 0005, decisões 1, 5 e 6; ADR 0031).

Formato dos arquivos anuais da Câmara, medido em 2026-11-24: UTF-8 com BOM, `;`, colunas pelo
nome no cabeçalho, e (em `votacoes`) registros que ocupam mais de uma linha física. Os dados são
sintéticos; `deputado_nome` é um canário que nunca pode aparecer na saída, nos contadores nem nas
mensagens de erro.

O módulo é importado dentro dos testes: antes de ele existir, cada teste falha por si e a coleta
do pytest não para.
"""

import csv
import io

import pytest

from apps.sources.zip_csv import DuplicateColumnError, InvalidFormatError, MissingColumnError

BOM = b"\xef\xbb\xbf"
CANARIO = "CANARIO-NAO-VAZAR"

CABECALHO_VOTOS = [
    "idVotacao",
    "uriVotacao",
    "dataHoraVoto",
    "voto",
    "deputado_id",
    "deputado_uri",
    "deputado_nome",
    "deputado_siglaPartido",
    "deputado_uriPartido",
    "deputado_siglaUf",
    "deputado_idLegislatura",
    "deputado_urlFoto",
]
PERMITIDAS_VOTOS = [
    "idVotacao",
    "dataHoraVoto",
    "voto",
    "deputado_id",
    "deputado_siglaPartido",
    "deputado_idLegislatura",
]
CABECALHO_VOTACOES = ["id", "data", "descricao"]


def leitor(caminho, permitidas, **kwargs):
    from apps.sources.plain_csv import PlainCsvReader

    return PlainCsvReader(caminho, permitidas, **kwargs)


def linha_de_voto(votacao="2641546-7", voto="Sim", deputado="204379", partido="PT"):
    return [
        votacao,
        f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{votacao}",
        "2026-03-10T15:21:04",
        voto,
        deputado,
        f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado}",
        CANARIO,
        partido,
        "https://dadosabertos.camara.leg.br/api/v2/partidos/36844",
        "SP",
        "57",
        f"https://www.camara.leg.br/internet/deputado/bandep/{deputado}.jpg",
    ]


def permitidas_de(linha):
    return dict(zip(CABECALHO_VOTOS, linha, strict=True))


def escrever(caminho, cabecalho, linhas, *, bom=True, fim_de_linha="\n"):
    buffer = io.StringIO(newline="")
    escritor = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator=fim_de_linha)
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    caminho.write_bytes((BOM if bom else b"") + buffer.getvalue().encode("utf-8"))
    return caminho


def ler_tudo(leitor_):
    """Linhas devolvidas até o fim ou até o erro; o erro é de quem chama."""
    devolvidas = []
    for item in leitor_.rows():
        devolvidas.append(item)
    return devolvidas


# --- Colunas: só a allowlist sai (ADR 0005, decisão 1) ---


@pytest.mark.parametrize("bom", [True, False], ids=["com_bom", "sem_bom"])
@pytest.mark.parametrize("fim_de_linha", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_devolve_so_a_allowlist_com_o_nome_do_arquivo_e_nunca_o_canario(
    tmp_path, bom, fim_de_linha
):
    linhas = [
        linha_de_voto(voto="Sim"),
        linha_de_voto(voto="Não", deputado="160976", partido="PL"),
        linha_de_voto(voto="Abstenção", deputado="178957", partido="NOVO"),
    ]
    arquivo = escrever(
        tmp_path / "votos.csv", CABECALHO_VOTOS, linhas, bom=bom, fim_de_linha=fim_de_linha
    )
    leitor_ = leitor(arquivo, PERMITIDAS_VOTOS)

    devolvidas = ler_tudo(leitor_)

    assert devolvidas == [
        (
            "votos.csv",
            {coluna: permitidas_de(linha)[coluna] for coluna in PERMITIDAS_VOTOS},
        )
        for linha in linhas
    ]
    assert [valores["voto"] for _, valores in devolvidas] == ["Sim", "Não", "Abstenção"]
    assert (leitor_.rows_read, leitor_.rejected_rows) == (3, 0)
    assert leitor_.ignored_columns == set(CABECALHO_VOTOS) - set(PERMITIDAS_VOTOS)
    assert CANARIO not in repr(devolvidas) + repr(vars(leitor_))


@pytest.mark.parametrize(
    ("cabecalho", "linha", "erro"),
    [
        (
            [c for c in CABECALHO_VOTOS if c != "voto"],
            [v for c, v in permitidas_de(linha_de_voto()).items() if c != "voto"],
            MissingColumnError,
        ),
        (
            [*CABECALHO_VOTOS, "voto"],
            [*linha_de_voto(), "Sim"],
            DuplicateColumnError,
        ),
    ],
    ids=["coluna_permitida_ausente", "coluna_permitida_duplicada"],
)
def test_esquema_diferente_recusa_tudo_sem_devolver_linha(tmp_path, cabecalho, linha, erro):
    arquivo = escrever(tmp_path / "votos.csv", cabecalho, [linha, linha])
    devolvidas = []

    with pytest.raises(erro) as falha:
        for item in leitor(arquivo, PERMITIDAS_VOTOS).rows():
            devolvidas.append(item)

    assert devolvidas == []
    assert CANARIO not in str(falha.value)


@pytest.mark.parametrize("conteudo", [b"", BOM], ids=["vazio", "so_bom"])
def test_arquivo_sem_cabecalho_nao_passa_por_integro_sem_registros(tmp_path, conteudo):
    arquivo = tmp_path / "votos.csv"
    arquivo.write_bytes(conteudo)

    with pytest.raises(MissingColumnError):
        ler_tudo(leitor(arquivo, PERMITIDAS_VOTOS))


# --- Registro em mais de uma linha física (medido: 5 `descricao` em 9.153 votações) ---


def test_registro_multilinha_aceito_chega_inteiro_e_conta_as_linhas_fisicas(tmp_path):
    arquivo = escrever(
        tmp_path / "votacoes.csv",
        CABECALHO_VOTACOES,
        [
            ["2645346-18", "2026-11-23", "linha um\r\nlinha dois"],
            ["2645346-19", "2026-11-23", "sem quebra"],
        ],
    )
    leitor_ = leitor(arquivo, CABECALHO_VOTACOES, allow_multiline_records=True)

    devolvidas = ler_tudo(leitor_)

    assert devolvidas == [
        (
            "votacoes.csv",
            {"id": "2645346-18", "data": "2026-11-23", "descricao": "linha um\r\nlinha dois"},
        ),
        ("votacoes.csv", {"id": "2645346-19", "data": "2026-11-23", "descricao": "sem quebra"}),
    ]
    assert (leitor_.rows_read, leitor_.rejected_rows) == (3, 0)


def test_registro_multilinha_sem_a_permissao_e_rejeitado_e_o_resto_segue(tmp_path):
    arquivo = escrever(
        tmp_path / "votacoes.csv",
        CABECALHO_VOTACOES,
        [
            ["2645346-18", "2026-11-23", "linha um\r\nlinha dois"],
            ["2645346-19", "2026-11-23", "sem quebra"],
        ],
    )
    leitor_ = leitor(arquivo, CABECALHO_VOTACOES)

    devolvidas = ler_tudo(leitor_)

    assert devolvidas == [
        ("votacoes.csv", {"id": "2645346-19", "data": "2026-11-23", "descricao": "sem quebra"})
    ]
    assert (leitor_.rows_read, leitor_.rejected_rows) == (3, 2)


def test_linha_com_numero_de_colunas_diferente_e_rejeitada_sem_citar_o_conteudo(tmp_path):
    arquivo = escrever(
        tmp_path / "votacoes.csv",
        CABECALHO_VOTACOES,
        [["2645346-18", "2026-11-23", "ok"], ["2645346-19", CANARIO]],
    )
    leitor_ = leitor(arquivo, CABECALHO_VOTACOES)

    devolvidas = ler_tudo(leitor_)

    assert [valores["id"] for _, valores in devolvidas] == ["2645346-18"]
    assert (leitor_.rows_read, leitor_.rejected_rows) == (2, 1)
    assert CANARIO not in repr(devolvidas) + repr(vars(leitor_))


# --- Limites (falha fechada) ---


def test_arquivo_acima_do_limite_de_bytes_recusa_a_carga(tmp_path):
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [linha_de_voto()] * 5)
    devolvidas = []

    with pytest.raises(InvalidFormatError) as falha:
        for item in leitor(arquivo, PERMITIDAS_VOTOS, max_bytes=arquivo.stat().st_size - 1).rows():
            devolvidas.append(item)

    assert devolvidas == []
    assert CANARIO not in str(falha.value)


def test_arquivo_no_limite_exato_de_bytes_passa(tmp_path):
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [linha_de_voto()] * 5)

    devolvidas = ler_tudo(leitor(arquivo, PERMITIDAS_VOTOS, max_bytes=arquivo.stat().st_size))

    assert len(devolvidas) == 5


def test_linha_acima_do_limite_de_caracteres_recusa_sem_vazar_o_conteudo(tmp_path):
    arquivo = escrever(
        tmp_path / "votacoes.csv",
        CABECALHO_VOTACOES,
        [["2645346-18", "2026-11-23", CANARIO * 50]],
    )

    with pytest.raises(InvalidFormatError) as falha:
        ler_tudo(leitor(arquivo, CABECALHO_VOTACOES, max_line_chars=100))

    assert CANARIO not in str(falha.value)
    assert falha.value.__context__ is None


# --- Teto por registro: o `csv.reader` junta linhas enquanto houver aspas abertas ---


def test_registro_com_mais_linhas_que_o_teto_recusa_a_carga(tmp_path):
    # Cada linha `";"` fecha o campo aberto, separa e abre outro: o registro nunca termina.
    arquivo = tmp_path / "votacoes.csv"
    arquivo.write_bytes(('a;b\n"x\n' + '";"\n' * 50).encode())

    with pytest.raises(InvalidFormatError) as falha:
        ler_tudo(leitor(arquivo, ["a", "b"], allow_multiline_records=True, max_record_lines=5))

    assert falha.value.__context__ is None


def test_o_teto_de_linhas_vale_por_registro_e_nao_pelo_arquivo_todo(tmp_path):
    registros = [[f"2645346-{n}", "2026-11-23", "um\r\ndois\r\ntres"] for n in range(4)]
    arquivo = escrever(tmp_path / "votacoes.csv", CABECALHO_VOTACOES, registros)

    devolvidas = ler_tudo(
        leitor(arquivo, CABECALHO_VOTACOES, allow_multiline_records=True, max_record_lines=3)
    )

    assert len(devolvidas) == 4


def test_registro_exatamente_acima_do_teto_recusa(tmp_path):
    arquivo = escrever(
        tmp_path / "votacoes.csv",
        CABECALHO_VOTACOES,
        [["2645346-18", "2026-11-23", "um\r\ndois\r\ntres\r\nquatro"]],
    )

    with pytest.raises(InvalidFormatError):
        ler_tudo(
            leitor(arquivo, CABECALHO_VOTACOES, allow_multiline_records=True, max_record_lines=3)
        )


# --- Entradas que quebram (falha fechada) ---


def test_utf8_invalido_recusa_a_carga_sem_vazar_o_conteudo(tmp_path):
    arquivo = tmp_path / "votos.csv"
    arquivo.write_bytes(
        BOM + ";".join(CABECALHO_VOTOS).encode() + b"\n" + CANARIO.encode() + b"\xe3\x80\n"
    )

    with pytest.raises(InvalidFormatError) as falha:
        ler_tudo(leitor(arquivo, PERMITIDAS_VOTOS))

    assert CANARIO not in str(falha.value)
    assert falha.value.__context__ is None


def test_bom_duplicado_recusa_a_carga(tmp_path):
    arquivo = tmp_path / "votos.csv"
    arquivo.write_bytes(BOM + BOM + ";".join(CABECALHO_VOTOS).encode() + b"\n")

    with pytest.raises(InvalidFormatError):
        ler_tudo(leitor(arquivo, PERMITIDAS_VOTOS))


def test_so_cabecalho_entrega_zero_linhas_e_quem_consome_olha_rows_read(tmp_path):
    # Caracterização: o leitor não trata "só cabeçalho" como erro (como o de ZIP); o consumidor
    # vê `rows_read == 0`. É um limite conhecido do ADR 0031.
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [])
    leitor_ = leitor(arquivo, PERMITIDAS_VOTOS)

    assert ler_tudo(leitor_) == []
    assert (leitor_.rows_read, leitor_.rejected_rows) == (0, 0)


def test_diretorio_nao_e_arquivo_regular(tmp_path):
    with pytest.raises(InvalidFormatError):
        ler_tudo(leitor(tmp_path, PERMITIDAS_VOTOS))


def test_arquivo_inexistente_sobe_como_erro_de_sistema_e_nao_como_csv_invalido(tmp_path):
    with pytest.raises(FileNotFoundError):
        ler_tudo(leitor(tmp_path / "nao-existe.csv", PERMITIDAS_VOTOS))


# --- Contrato do objeto ---


@pytest.mark.parametrize("teto", [0, -1, "3", 1.5])
def test_teto_de_linhas_por_registro_invalido_e_recusado(tmp_path, teto):
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [linha_de_voto()])

    with pytest.raises(ValueError, match="limites"):
        leitor(arquivo, PERMITIDAS_VOTOS, max_record_lines=teto)


def test_leitor_e_de_uso_unico(tmp_path):
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [linha_de_voto()])
    leitor_ = leitor(arquivo, PERMITIDAS_VOTOS)
    ler_tudo(leitor_)

    with pytest.raises(RuntimeError):
        leitor_.rows()


def test_allowlist_vazia_ou_em_texto_e_recusada(tmp_path):
    arquivo = escrever(tmp_path / "votos.csv", CABECALHO_VOTOS, [linha_de_voto()])

    with pytest.raises(ValueError, match="allowlist"):
        leitor(arquivo, [])
    with pytest.raises(ValueError, match="allowlist"):
        leitor(arquivo, "voto")
