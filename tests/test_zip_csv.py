"""Testes de contrato do leitor de ZIP de CSV (ADR 0005, decisões 1, 5 e 6).

Não há dado real: o valor do CPF é um canário que nunca pode aparecer na saída
do leitor, nem nos contadores, nem nas mensagens de erro.
"""

import csv
import hashlib
import io
import tracemalloc
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


# --- Integridade do original ---


def test_sha256_do_zip_e_igual_ao_calculado_de_fora(tmp_path):
    zip_path = build_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    assert sha256_file(zip_path) == hashlib.sha256(zip_path.read_bytes()).hexdigest()
