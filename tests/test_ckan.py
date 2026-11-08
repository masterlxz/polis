"""Testes da leitura da licença declarada no CKAN (ADR 0008, decisão 2).

O cliente é falso: escreve o JSON combinado no destino ou levanta o erro combinado, sem rede.
"""

import json
from pathlib import Path

import pytest

from apps.sources.ckan import CkanError, read_license_id
from apps.sources.http_client import BlockedError, DownloadError, DownloadResult

URL = "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2026"


class FakeJsonClient:
    def __init__(self, conteudo=None, error=None):
        self.conteudo = conteudo
        self.error = error
        self.calls = []

    def download(self, url, destination):
        self.calls.append(url)
        if self.error is not None:
            raise self.error
        if isinstance(self.conteudo, bytes):
            dados = self.conteudo
        else:
            dados = json.dumps(self.conteudo).encode()
        Path(destination).write_bytes(dados)
        return DownloadResult(
            path=Path(destination), sha256="x", size_bytes=len(dados), etag="", last_modified=""
        )


def pacote(**result):
    return {"success": True, "result": result}


def test_devolve_o_license_id_do_pacote(tmp_path):
    cliente = FakeJsonClient(pacote(license_id="cc-by", name="candidatos-2026"))
    assert read_license_id(cliente, URL, tmp_path) == "cc-by"
    assert cliente.calls == [URL]


def test_license_id_vazio_devolve_vazio(tmp_path):
    assert read_license_id(FakeJsonClient(pacote(license_id="")), URL, tmp_path) == ""


def test_pacote_sem_license_id_devolve_vazio(tmp_path):
    assert read_license_id(FakeJsonClient(pacote(name="x")), URL, tmp_path) == ""


def test_license_id_nulo_devolve_vazio(tmp_path):
    assert read_license_id(FakeJsonClient(pacote(license_id=None)), URL, tmp_path) == ""


@pytest.mark.parametrize(
    "conteudo",
    [
        {"success": False, "error": {"message": "Not found"}},
        {"success": True},
        {"success": True, "result": []},
        {"success": True, "result": {"license_id": 123}},
        [1, 2, 3],
        b"isto nao e json",
        b"",
    ],
)
def test_resposta_fora_do_formato_levanta_ckan_error(tmp_path, conteudo):
    with pytest.raises(CkanError):
        read_license_id(FakeJsonClient(conteudo), URL, tmp_path)


def test_resposta_grande_demais_levanta_ckan_error(tmp_path):
    grande = pacote(license_id="cc-by", notes="x" * 2000)
    with pytest.raises(CkanError):
        read_license_id(FakeJsonClient(grande), URL, tmp_path, max_bytes=1000)


def test_erro_de_download_e_de_bloqueio_passam_sem_serem_engolidos(tmp_path):
    with pytest.raises(BlockedError):
        read_license_id(FakeJsonClient(error=BlockedError("bloqueio")), URL, tmp_path)
    with pytest.raises(DownloadError):
        read_license_id(FakeJsonClient(error=DownloadError("rede")), URL, tmp_path)


def test_a_mensagem_do_erro_nao_cita_o_conteudo_da_resposta(tmp_path):
    segredo = "VALOR-QUE-NAO-PODE-VAZAR"
    with pytest.raises(CkanError) as erro:
        read_license_id(FakeJsonClient({"success": False, "error": segredo}), URL, tmp_path)
    assert segredo not in str(erro.value)
