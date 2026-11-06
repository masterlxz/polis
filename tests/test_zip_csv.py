"""Testes de contrato do leitor de ZIP de CSV (ADR 0005, decisões 1, 5 e 6).

Não há dado real: o valor do CPF é um canário que nunca pode aparecer na saída
do leitor, nem nos contadores, nem nas mensagens de erro.
"""

import csv
import hashlib
import io
import traceback
import tracemalloc
import warnings
import zipfile

import pytest

from apps.sources.zip_csv import (
    DuplicateColumnError,
    InvalidFormatError,
    MissingColumnError,
    ZipCsvReader,
    sha256_file,
)

ALLOW = ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"]
CANARY = "CANARIO-NAO-VAZAR"


def csv_bytes(header, rows, *, encoding="iso-8859-1", eol="\r\n"):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator=eol)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue().encode(encoding)


def build_zip(path, items, *, compression=zipfile.ZIP_DEFLATED):
    with zipfile.ZipFile(path, "w", compression) as zf:
        for name, content in items.items():
            zf.writestr(name, content)
    return path


def read_all(path, allow=ALLOW):
    reader = ZipCsvReader(path, allow)
    return reader, list(reader.rows())


def evidence(reader, rows, exc=None):
    """Tudo que o leitor expõe, em texto, para procurar vazamento."""
    return repr(rows) + repr(vars(reader)) + (str(exc) if exc else "")


def traceback_text(exc):
    """Traceback com as variáveis locais de cada quadro, como Sentry ou Django em debug."""
    formatted = traceback.TracebackException.from_exception(exc, capture_locals=True).format()
    return "".join(formatted)


CPF_HEADER = ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "NR_CPF_CANDIDATO"]


def canary_zip(tmp_path, body):
    return build_zip(tmp_path / "a.zip", {"a.csv": body})


# --- Leitura por nome de coluna (ADR 0005, decisão 6) ---


def test_le_pelo_nome_da_coluna_e_nao_pela_posicao(tmp_path):
    data = csv_bytes(["SG_PARTIDO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO"], [["PT", "1", "ANA"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    _, rows = read_all(zip_path)
    assert rows == [
        ("a.csv", {"SQ_CANDIDATO": "1", "NM_URNA_CANDIDATO": "ANA", "SG_PARTIDO": "PT"})
    ]


@pytest.mark.parametrize(
    "wrong_name",
    ["sq_candidato", " SQ_CANDIDATO", "SQ_CANDIDATO ", "Sq_Candidato"],
    ids=["minuscula", "espaco-antes", "espaco-depois", "caixa-mista"],
)
def test_nome_de_coluna_com_caixa_ou_espaco_diferente_conta_como_ausente(tmp_path, wrong_name):
    data = csv_bytes([wrong_name, "NM_URNA_CANDIDATO", "SG_PARTIDO"], [["1", "ANA", "PT"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    with pytest.raises(MissingColumnError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_coluna_permitida_duplicada_no_cabecalho_falha(tmp_path):
    data = csv_bytes(["SQ_CANDIDATO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"], [])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    with pytest.raises(DuplicateColumnError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_allowlist_vazia_e_recusada(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [])})
    with pytest.raises(ValueError, match="allowlist"):
        ZipCsvReader(zip_path, [])


# --- Falha fechada por ZIP (ADR 0005, decisão 6) ---


def test_coluna_ausente_no_segundo_item_falha_antes_de_devolver_qualquer_linha(tmp_path):
    good = csv_bytes(ALLOW, [["1", "ANA", "PT"], ["2", "BIA", "PSD"]])
    bad = csv_bytes(["SQ_CANDIDATO", "NM_URNA_CANDIDATO"], [["3", "CLARA"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": good, "b.csv": bad})
    reader = ZipCsvReader(zip_path, ALLOW)
    generator = reader.rows()
    with pytest.raises(MissingColumnError):
        next(generator)
    assert reader.rows_read == 0


def test_item_csv_vazio_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": b""})
    with pytest.raises(MissingColumnError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_so_cabecalho_sem_dados_nao_devolve_nada_e_nao_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [])})
    reader, rows = read_all(zip_path)
    assert rows == []
    assert reader.rows_read == 0


# --- Allowlist e dado pessoal (ADR 0005, decisão 1) ---


def test_coluna_fora_da_allowlist_e_ignorada_e_listada(tmp_path):
    data = csv_bytes(ALLOW + ["COLUNA_NOVA"], [["1", "ANA", "PT", "x"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    reader, rows = read_all(zip_path)
    assert [set(values) for _, values in rows] == [set(ALLOW)]
    assert reader.ignored_columns == {"COLUNA_NOVA"}


def test_valor_canario_do_cpf_nunca_aparece_em_lugar_nenhum(tmp_path):
    data = csv_bytes(
        ["SQ_CANDIDATO", "NR_CPF_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"],
        [["1", CANARY, "ANA", "PT"]],
    )
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    reader, rows = read_all(zip_path)
    assert CANARY not in evidence(reader, rows)
    assert all("NR_CPF_CANDIDATO" not in values for _, values in rows)
    assert reader.ignored_columns == {"NR_CPF_CANDIDATO"}


def test_canario_numa_linha_rejeitada_nao_aparece_em_lugar_nenhum(tmp_path):
    header = ";".join(ALLOW)
    body = f"{header}\r\n1;ANA;PT\r\n2;BIA;PSD;{CANARY}\r\n3;CLARA;PSD\r\n".encode("iso-8859-1")
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": body})
    reader, rows = read_all(zip_path)
    assert reader.rejected_rows == 1
    assert CANARY not in evidence(reader, rows)


def test_canario_nao_aparece_na_mensagem_de_erro_de_coluna_ausente(tmp_path):
    data = csv_bytes(["SQ_CANDIDATO", "NR_CPF_CANDIDATO"], [["1", CANARY]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    reader = ZipCsvReader(zip_path, ALLOW)
    with pytest.raises(MissingColumnError) as info:
        next(reader.rows())
    assert CANARY not in evidence(reader, [], info.value)
    assert "a.csv" in str(info.value)


# --- Formato do CSV ---


def test_campo_entre_aspas_com_ponto_e_virgula_dentro_fica_inteiro(tmp_path):
    data = csv_bytes(ALLOW, [["1", "ANA; A SILVA", "PT"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    _, rows = read_all(zip_path)
    assert rows[0][1]["NM_URNA_CANDIDATO"] == "ANA; A SILVA"


def test_texto_iso_8859_1_vira_utf8_com_acentos_corretos(tmp_path):
    data = csv_bytes(ALLOW, [["1", "JOÃO AÇÚCAR É", "PT"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    _, rows = read_all(zip_path)
    assert rows[0][1]["NM_URNA_CANDIDATO"] == "JOÃO AÇÚCAR É"


def test_fim_de_linha_crlf_nao_deixa_barra_r_nos_valores(tmp_path):
    data = csv_bytes(ALLOW, [["1", "ANA", "PT"]], eol="\r\n")
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    _, rows = read_all(zip_path)
    assert all("\r" not in value for _, values in rows for value in values.values())


def test_item_com_bom_utf8_falha_em_vez_de_corromper_acentos(tmp_path):
    data = b"\xef\xbb\xbf" + csv_bytes(ALLOW, [["1", "JOÃO", "PT"]], encoding="utf-8")
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_campo_maior_que_o_limite_do_csv_falha_sem_citar_o_valor(tmp_path):
    huge = "X" * 200_000
    data = csv_bytes(ALLOW, [["1", huge, "PT"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data})
    reader = ZipCsvReader(zip_path, ALLOW)
    with pytest.raises(InvalidFormatError) as info:
        list(reader.rows())
    assert "XXXXXXXXXX" not in str(info.value)


# --- Linhas malformadas e contadores ---


def test_linha_com_numero_de_colunas_diferente_e_rejeitada_e_contada(tmp_path):
    header = ";".join(ALLOW)
    body = f"{header}\r\n1;ANA;PT\r\n2;BIA\r\n3;CLARA;PSD\r\n".encode("iso-8859-1")
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": body})
    reader, rows = read_all(zip_path)
    assert [values["SQ_CANDIDATO"] for _, values in rows] == ["1", "3"]
    assert reader.rejected_rows == 1
    assert reader.rows_read == 3


# --- ZIP e itens ---


def test_item_que_nao_e_csv_e_ignorado_sem_erro(tmp_path):
    zip_path = build_zip(
        tmp_path / "a.zip",
        {
            "leiame.pdf": b"%PDF-1.4\r\nlixo binario 1\r\nlixo binario 2\r\nlixo binario 3\r\n",
            "a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]]),
        },
    )
    _, rows = read_all(zip_path)
    assert [name for name, _ in rows] == ["a.csv"]


def test_item_com_nome_de_caminho_relativo_e_lido_em_memoria_sem_escrever_no_disco(tmp_path):
    inner = tmp_path / "dentro"
    inner.mkdir()
    zip_path = build_zip(inner / "a.zip", {"../fora.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    _, rows = read_all(zip_path)
    assert [name for name, _ in rows] == ["../fora.csv"]
    assert not (tmp_path / "fora.csv").exists()
    assert sorted(p.name for p in inner.iterdir()) == ["a.zip"]


def test_arquivo_que_nao_e_zip_falha(tmp_path):
    path = tmp_path / "a.zip"
    path.write_bytes(b"isto nao e um zip\r\n" * 10)
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(path, ALLOW).rows())


def test_zip_truncado_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    zip_path.write_bytes(zip_path.read_bytes()[:-30])
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_crc_invalido_falha_em_vez_de_entregar_dado_parcial_como_completo(tmp_path):
    data = csv_bytes(ALLOW, [["1", "MARCADOR-CRC-UNICO", "PT"]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data}, compression=zipfile.ZIP_STORED)
    raw = bytearray(zip_path.read_bytes())
    position = raw.find(b"MARCADOR-CRC-UNICO")
    assert position > 0
    raw[position] ^= 0x01
    zip_path.write_bytes(bytes(raw))
    with pytest.raises(InvalidFormatError):
        list(ZipCsvReader(zip_path, ALLOW).rows())


def test_varios_itens_em_ordem_sem_carregar_o_arquivo_inteiro_na_memoria(tmp_path):
    items = {
        f"{name}.csv": csv_bytes(
            ALLOW, ([str(i), f"CANDIDATO NUMERO {i} DA LISTA", "PT"] for i in range(50_000))
        )
        for name in ("a", "b", "c", "d")
    }
    zip_path = build_zip(tmp_path / "a.zip", items)
    total_size = sum(len(value) for value in items.values())
    del items

    order, total = [], 0
    tracemalloc.start()
    for name, _values in ZipCsvReader(zip_path, ALLOW).rows():
        total += 1
        if not order or order[-1] != name:
            order.append(name)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert order == ["a.csv", "b.csv", "c.csv", "d.csv"]
    assert total == 200_000
    assert peak < total_size / 5


# --- Registro multilinha (revisão adversária, C1) ---

UNBALANCED_QUOTE_BODY = (
    f'{";".join(CPF_HEADER)}\r\n1;"ANA;PT;0\r\n2;BIA;PT;{CANARY}";PT;0\r\n3;CLARA;PSD;0\r\n'
).encode("iso-8859-1")


def test_aspas_abertas_nao_engolem_a_linha_seguinte_com_o_canario(tmp_path):
    zip_path = canary_zip(tmp_path, UNBALANCED_QUOTE_BODY)
    reader, rows = read_all(zip_path, ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"])
    assert [values["SQ_CANDIDATO"] for _, values in rows] == ["3"]
    assert reader.rejected_rows == 2  # linhas físicas, não registros
    assert reader.rows_read == 3
    assert CANARY not in evidence(reader, rows)


def test_registro_multilinha_so_e_aceito_com_a_opcao_explicita(tmp_path):
    body = b'SQ_CANDIDATO;NM_URNA_CANDIDATO;SG_PARTIDO\r\n1;"A\r\nB";PT\r\n'
    zip_path = canary_zip(tmp_path, body)
    reader, rows = read_all(zip_path)
    assert rows == [] and reader.rejected_rows == 2
    permissive = ZipCsvReader(zip_path, ALLOW, allow_multiline_records=True)
    assert [values["NM_URNA_CANDIDATO"] for _, values in permissive.rows()] == ["A\r\nB"]


# --- Erros sem contexto nem variáveis com dado pessoal (revisão adversária, C2) ---


def test_erro_de_crc_nao_carrega_contexto_nem_variaveis_com_o_canario(tmp_path):
    data = csv_bytes(CPF_HEADER, [["1", "MARCADOR-CRC-UNICO", "PT", CANARY]])
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": data}, compression=zipfile.ZIP_STORED)
    raw = bytearray(zip_path.read_bytes())
    raw[raw.find(b"MARCADOR-CRC-UNICO")] ^= 0x01
    zip_path.write_bytes(bytes(raw))
    with pytest.raises(InvalidFormatError) as info:
        list(ZipCsvReader(zip_path, ALLOW).rows())
    assert info.value.__context__ is None
    assert info.value.__cause__ is None
    assert CANARY not in traceback_text(info.value)


def test_linha_acima_do_limite_nao_deixa_o_canario_no_traceback(tmp_path):
    rows = [["1", "ANA", "PT", CANARY], ["2", "BIA", "PT", CANARY * 20]]
    zip_path = canary_zip(tmp_path, csv_bytes(CPF_HEADER, rows))
    with pytest.raises(InvalidFormatError) as info:
        list(ZipCsvReader(zip_path, ALLOW, max_line_chars=120).rows())
    assert CANARY not in str(info.value) + traceback_text(info.value)


def test_arquivo_sem_cabecalho_nao_deixa_a_primeira_linha_de_dados_no_traceback(tmp_path):
    zip_path = canary_zip(tmp_path, f"1;ANA;PT;{CANARY}\r\n".encode("iso-8859-1"))
    reader = ZipCsvReader(zip_path, ALLOW)
    with pytest.raises(MissingColumnError) as info:
        next(reader.rows())
    assert CANARY not in evidence(reader, [], info.value) + traceback_text(info.value)


# --- Falha fechada completa (revisão adversária, I1, I2, I4, I5) ---


def test_zip_sem_nenhum_item_csv_falha_em_vez_de_parecer_arquivo_vazio(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"dados.txt": b"1;ANA;PT\r\n"})
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_zip_vazio_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {})
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_item_com_extensao_maiuscula_tambem_e_validado(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"DADOS.CSV": csv_bytes(["SQ_CANDIDATO"], [["1"]])})
    with pytest.raises(MissingColumnError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_cabecalho_que_e_linha_em_branco_falha_com_erro_do_leitor(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": b"\r\n1;ANA;PT\r\n"})
    with pytest.raises(MissingColumnError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_dois_itens_com_o_mesmo_nome_falham(tmp_path):
    zip_path = tmp_path / "a.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        build_zip_items = [("a.csv", csv_bytes(ALLOW, [["1", "ANA", "PT"]]))] * 2
        with zipfile.ZipFile(zip_path, "w") as zf:
            for name, content in build_zip_items:
                zf.writestr(name, content)
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_o_leitor_e_de_uso_unico(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    reader = ZipCsvReader(zip_path, ALLOW)
    assert len(list(reader.rows())) == 1
    with pytest.raises(RuntimeError, match="uma vez"):
        reader.rows()
    assert reader.rows_read == 1


def test_nome_de_item_com_quebra_de_linha_nao_injeta_linha_no_log(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a\n[FALSO].csv": csv_bytes(["SQ_CANDIDATO"], [])})
    with pytest.raises(MissingColumnError) as info:
        next(ZipCsvReader(zip_path, ALLOW).rows())
    assert "\n" not in str(info.value)


def test_item_protegido_por_senha_falha(tmp_path):
    zip_path = tmp_path / "a.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        info = zipfile.ZipInfo("a.csv")
        info.flag_bits |= 0x1
        zf.writestr(info, csv_bytes(ALLOW, [["1", "ANA", "PT"]]))
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW).rows())


def test_dados_comprimidos_corrompidos_falham(tmp_path):
    rows = [[str(i), "CANDIDATO NUMERO " * 4, "PT"] for i in range(500)]
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, rows)})
    raw = bytearray(zip_path.read_bytes())
    start = 30 + len("a.csv")
    for position in range(start + 10, start + 40):
        raw[position] ^= 0xFF
    zip_path.write_bytes(bytes(raw))
    with pytest.raises(InvalidFormatError):
        list(ZipCsvReader(zip_path, ALLOW).rows())


# --- Limites de recursos (revisão adversária, I3) ---


def test_cabecalho_com_colunas_demais_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW + ["X1", "X2"], [])})
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW, max_columns=4).rows())


def test_zip_com_itens_demais_falha(tmp_path):
    items = {f"{n}.csv": csv_bytes(ALLOW, []) for n in "abc"}
    zip_path = build_zip(tmp_path / "a.zip", items)
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW, max_items=2).rows())


def test_tamanho_descomprimido_declarado_acima_do_limite_falha(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW, max_uncompressed_bytes=10).rows())


def test_linha_gigante_com_milhoes_de_delimitadores_falha_sem_estourar_memoria(tmp_path):
    body = b"SQ_CANDIDATO;NM_URNA_CANDIDATO;SG_PARTIDO\r\n" + b";" * 5_000_000 + b"\r\n"
    zip_path = canary_zip(tmp_path, body)
    tracemalloc.start()
    with pytest.raises(InvalidFormatError):
        list(ZipCsvReader(zip_path, ALLOW).rows())
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 50_000_000


# --- Parâmetros (revisão adversária, I6) ---


@pytest.mark.parametrize(
    "kwargs",
    [
        {"encoding": "nao-existe"},
        {"delimiter": ";;"},
        {"delimiter": ""},
        {"max_columns": 0},
        {"max_line_chars": -1},
    ],
    ids=["encoding", "delimitador-longo", "delimitador-vazio", "max-colunas", "max-linha"],
)
def test_parametros_invalidos_sao_recusados_na_construcao(tmp_path, kwargs):
    with pytest.raises(ValueError):
        ZipCsvReader(tmp_path / "a.zip", ALLOW, **kwargs)


def test_allowlist_como_texto_e_recusada(tmp_path):
    with pytest.raises(ValueError):
        ZipCsvReader(tmp_path / "a.zip", "SQ_CANDIDATO")


def test_allowlist_com_nome_repetido_e_recusada(tmp_path):
    with pytest.raises(ValueError):
        ZipCsvReader(tmp_path / "a.zip", ["SQ_CANDIDATO", "SQ_CANDIDATO"])


# --- Contrato de codificação, delimitador e contadores (mutações que sobreviviam) ---


def test_bytes_0x80_a_0x9f_ficam_como_iso_8859_1_e_nao_viram_cp1252(tmp_path):
    zip_path = canary_zip(tmp_path, csv_bytes(ALLOW, [["1", "A\x92B", "PT"]]))
    _, rows = read_all(zip_path)
    assert rows[0][1]["NM_URNA_CANDIDATO"] == "A\x92B"


def test_delimitador_configuravel(tmp_path):
    body = b'"SQ_CANDIDATO","NM_URNA_CANDIDATO","SG_PARTIDO"\r\n"1","ANA","PT"\r\n'
    zip_path = canary_zip(tmp_path, body)
    rows = list(ZipCsvReader(zip_path, ALLOW, delimiter=",").rows())
    assert rows == [
        ("a.csv", {"SQ_CANDIDATO": "1", "NM_URNA_CANDIDATO": "ANA", "SG_PARTIDO": "PT"})
    ]


def test_utf8_com_byte_invalido_falha_sem_citar_o_valor(tmp_path):
    zip_path = canary_zip(tmp_path, csv_bytes(ALLOW, [["1", "JOÃO", "PT"]]))
    with pytest.raises(InvalidFormatError) as info:
        list(ZipCsvReader(zip_path, ALLOW, encoding="utf-8").rows())
    assert "JO" not in str(info.value)


def test_bom_utf8_tambem_falha_quando_a_codificacao_configurada_e_utf8(tmp_path):
    body = b"\xef\xbb\xbf" + csv_bytes(ALLOW, [["1", "ANA", "PT"]], encoding="utf-8")
    zip_path = canary_zip(tmp_path, body)
    with pytest.raises(InvalidFormatError):
        next(ZipCsvReader(zip_path, ALLOW, encoding="utf-8").rows())


def test_linhas_em_branco_no_meio_e_no_fim_nao_contam(tmp_path):
    body = b"SQ_CANDIDATO;NM_URNA_CANDIDATO;SG_PARTIDO\r\n\r\n1;ANA;PT\r\n\r\n\r\n"
    reader, rows = read_all(canary_zip(tmp_path, body))
    assert len(rows) == 1
    assert (reader.rows_read, reader.rejected_rows) == (1, 0)


def test_colunas_ignoradas_de_varios_itens_sao_a_uniao(tmp_path):
    items = {
        "a.csv": csv_bytes(ALLOW + ["EXTRA_A"], [["1", "ANA", "PT", "x"]]),
        "b.csv": csv_bytes(ALLOW + ["EXTRA_B"], [["2", "BIA", "PT", "y"]]),
    }
    reader, _ = read_all(build_zip(tmp_path / "a.zip", items))
    assert reader.ignored_columns == {"EXTRA_A", "EXTRA_B"}


# --- Integridade do original ---


def test_sha256_do_zip_e_igual_ao_calculado_de_fora(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    assert sha256_file(zip_path) == hashlib.sha256(zip_path.read_bytes()).hexdigest()
