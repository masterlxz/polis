"""Testes do leitor de ZIP de CSV (spike descartável do ADR 0006).

Fixam o comportamento das decisões 1, 5 e 6 do ADR 0005: allowlist por nome de
coluna, descarte na leitura, falha fechada e rejeição de linha malformada.
Não há dado real: o valor do CPF é um canário que nunca pode aparecer na saída.
"""
import csv
import hashlib
import io
import tracemalloc
import zipfile

import pytest

from leitor import ColunaAusente, LeitorZip, sha256_arquivo

ALLOW = ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"]
CANARIO = "CANARIO-NAO-VAZAR"


def csv_bytes(cabecalho, linhas, *, encoding="iso-8859-1", eol="\r\n"):
    buf = io.StringIO(newline="")
    escritor = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator=eol)
    escritor.writerow(cabecalho)
    escritor.writerows(linhas)
    return buf.getvalue().encode(encoding)


def montar_zip(caminho, itens):
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zf:
        for nome, conteudo in itens.items():
            zf.writestr(nome, conteudo)
    return caminho


def ler(caminho, allow=ALLOW):
    leitor = LeitorZip(caminho, allow)
    return leitor, list(leitor.linhas())


def test_le_pelo_nome_da_coluna_e_nao_pela_posicao(tmp_path):
    dados = csv_bytes(["SG_PARTIDO", "SQ_CANDIDATO", "NM_URNA_CANDIDATO"], [["PT", "1", "ANA"]])
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    _, linhas = ler(z)
    assert linhas == [("a.csv", {"SQ_CANDIDATO": "1", "NM_URNA_CANDIDATO": "ANA", "SG_PARTIDO": "PT"})]


def test_coluna_da_allowlist_ausente_falha_antes_de_qualquer_linha_do_item(tmp_path):
    dados = csv_bytes(["SQ_CANDIDATO", "NM_URNA_CANDIDATO"], [["1", "ANA"], ["2", "BIA"]])
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    gerador = LeitorZip(z, ALLOW).linhas()
    with pytest.raises(ColunaAusente):
        next(gerador)


def test_coluna_nova_fora_da_allowlist_e_ignorada_com_alerta(tmp_path):
    dados = csv_bytes(
        ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO", "COLUNA_NOVA"],
        [["1", "ANA", "PT", "x"]],
    )
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    leitor, linhas = ler(z)
    assert [set(l.keys()) for _, l in linhas] == [set(ALLOW)]
    assert leitor.colunas_ignoradas == {"COLUNA_NOVA"}


def test_valor_canario_do_cpf_nunca_aparece_na_saida(tmp_path):
    dados = csv_bytes(
        ["SQ_CANDIDATO", "NR_CPF_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"],
        [["1", CANARIO, "ANA", "PT"]],
    )
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    _, linhas = ler(z)
    assert CANARIO not in repr(linhas)
    assert all("NR_CPF_CANDIDATO" not in l for _, l in linhas)


def test_campo_entre_aspas_com_ponto_e_virgula_dentro_fica_inteiro(tmp_path):
    dados = csv_bytes(["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"], [["1", "ANA; A SILVA", "PT"]])
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    _, linhas = ler(z)
    assert linhas[0][1]["NM_URNA_CANDIDATO"] == "ANA; A SILVA"


def test_texto_iso_8859_1_vira_utf8_com_acentos_corretos(tmp_path):
    dados = csv_bytes(["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"], [["1", "JOÃO AÇÚCAR É", "PT"]])
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    _, linhas = ler(z)
    assert linhas[0][1]["NM_URNA_CANDIDATO"] == "JOÃO AÇÚCAR É"


def test_fim_de_linha_crlf_nao_deixa_barra_r_nos_valores(tmp_path):
    dados = csv_bytes(["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"], [["1", "ANA", "PT"]], eol="\r\n")
    z = montar_zip(tmp_path / "a.zip", {"a.csv": dados})
    _, linhas = ler(z)
    assert all("\r" not in v for _, l in linhas for v in l.values())


def test_varios_itens_em_ordem_sem_carregar_o_arquivo_inteiro_na_memoria(tmp_path):
    cab = ["SQ_CANDIDATO", "NM_URNA_CANDIDATO", "SG_PARTIDO"]
    itens = {
        f"{nome}.csv": csv_bytes(cab, ([str(i), f"CANDIDATO NUMERO {i} DA LISTA", "PT"] for i in range(50_000)))
        for nome in ("a", "b", "c", "d")
    }
    z = montar_zip(tmp_path / "a.zip", itens)
    tamanho_total = sum(len(v) for v in itens.values())
    del itens

    ordem, total = [], 0
    tracemalloc.start()
    for nome, _linha in LeitorZip(z, ALLOW).linhas():
        total += 1
        if not ordem or ordem[-1] != nome:
            ordem.append(nome)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert ordem == ["a.csv", "b.csv", "c.csv", "d.csv"]
    assert total == 200_000
    assert pico < tamanho_total / 5  # muito abaixo do conteúdo descomprimido


def test_sha256_do_zip_e_igual_ao_calculado_de_fora(tmp_path):
    z = montar_zip(tmp_path / "a.zip", {"a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])})
    assert sha256_arquivo(z) == hashlib.sha256(z.read_bytes()).hexdigest()


def test_linha_com_numero_de_colunas_diferente_e_rejeitada_e_contada(tmp_path):
    cab = ",".join(ALLOW).replace(",", ";")
    corpo = f"{cab}\r\n1;ANA;PT\r\n2;BIA\r\n3;CLARA;PSD\r\n".encode("iso-8859-1")
    z = montar_zip(tmp_path / "a.zip", {"a.csv": corpo})
    leitor, linhas = ler(z)
    assert [l["SQ_CANDIDATO"] for _, l in linhas] == ["1", "3"]
    assert leitor.rejeitadas == 1


def test_item_que_nao_e_csv_e_ignorado_sem_erro(tmp_path):
    z = montar_zip(
        tmp_path / "a.zip",
        {"leiame.pdf": b"%PDF-1.4 conteudo binario", "a.csv": csv_bytes(ALLOW, [["1", "ANA", "PT"]])},
    )
    _, linhas = ler(z)
    assert [nome for nome, _ in linhas] == ["a.csv"]
