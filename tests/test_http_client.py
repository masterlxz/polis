"""Testes do cliente HTTP com etiqueta de rede (ADR 0008, decisões 4 e 5).

Falam com um servidor HTTP real em 127.0.0.1 (sem rede externa). O relógio e o `sleep` do
cliente são falsos: o teste confere quanto o cliente pediu para esperar, sem esperar de verdade.
"""

import hashlib
import threading
import time
from dataclasses import dataclass, field
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from apps.sources.http_client import (
    USER_AGENT,
    BlockedError,
    DownloadError,
    PoliteClient,
)

WALL = 1_700_000_000.0
CORPO = b"conteudo do arquivo\n" * 50


@dataclass
class Resposta:
    status: int = 200
    headers: dict = field(default_factory=dict)
    body: bytes = CORPO
    declared_length: int | None = None
    chunked: bool = False
    delay: float = 0.0


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.requests.append({"path": self.path, "headers": dict(self.headers)})
        script = self.server.script
        resposta = script.pop(0) if len(script) > 1 else script[0]
        try:
            if resposta.delay:
                time.sleep(resposta.delay)
            self.send_response(resposta.status)
            for nome, valor in resposta.headers.items():
                self.send_header(nome, valor)
            if resposta.chunked:
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for i in range(0, len(resposta.body), 1000):
                    parte = resposta.body[i : i + 1000]
                    self.wfile.write(f"{len(parte):x}\r\n".encode() + parte + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
            else:
                tamanho = resposta.declared_length
                if tamanho is None:
                    tamanho = len(resposta.body)
                self.send_header("Content-Length", str(tamanho))
                self.end_headers()
                self.wfile.write(resposta.body)
                if tamanho > len(resposta.body):
                    self.close_connection = True
        except BrokenPipeError, ConnectionResetError:
            pass


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, segundos):
        self.sleeps.append(segundos)
        self.now += segundos


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.requests = []
    srv.script = [Resposta()]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def clock():
    return FakeClock()


def url(srv, caminho="/arquivo.zip"):
    return f"http://127.0.0.1:{srv.server_address[1]}{caminho}"


def make_client(clock, **kwargs):
    kwargs.setdefault("allowed_schemes", ("http",))
    return PoliteClient(
        sleep=clock.sleep,
        clock=clock.monotonic,
        wall_clock=lambda: WALL,
        **kwargs,
    )


# --- Download básico ---


def test_baixa_o_arquivo_com_hash_tamanho_etag_e_data(server, clock, tmp_path):
    cabecalhos = {"ETag": '"abc"', "Last-Modified": "Sat, 07 Nov 2026 08:00:00 GMT"}
    server.script = [Resposta(headers=cabecalhos)]
    destino = tmp_path / "arquivo.zip"
    resultado = make_client(clock).download(url(server), destino)
    assert destino.read_bytes() == CORPO
    assert resultado.sha256 == hashlib.sha256(CORPO).hexdigest()
    assert resultado.size_bytes == len(CORPO)
    assert resultado.etag == '"abc"'
    assert resultado.last_modified == "Sat, 07 Nov 2026 08:00:00 GMT"


def test_sem_etag_nem_data_devolve_texto_vazio(server, clock, tmp_path):
    resultado = make_client(clock).download(url(server), tmp_path / "a.zip")
    assert resultado.etag == ""
    assert resultado.last_modified == ""


def test_baixa_arquivo_grande_em_pedacos_com_hash_correto(server, clock, tmp_path):
    corpo = bytes(range(256)) * 20_000
    server.script = [Resposta(body=corpo, chunked=True)]
    resultado = make_client(clock).download(url(server), tmp_path / "grande.zip")
    assert resultado.sha256 == hashlib.sha256(corpo).hexdigest()
    assert resultado.size_bytes == len(corpo)


def test_so_o_arquivo_final_fica_no_diretorio(server, clock, tmp_path):
    make_client(clock).download(url(server), tmp_path / "arquivo.zip")
    assert [p.name for p in tmp_path.iterdir()] == ["arquivo.zip"]


# --- Identificação do coletor (decisão 4) ---


def test_envia_user_agent_honesto_com_nome_e_repositorio(server, clock, tmp_path):
    make_client(clock).download(url(server), tmp_path / "a.zip")
    agente = server.requests[0]["headers"]["User-Agent"]
    assert agente == USER_AGENT
    assert "polis" in agente
    assert "https://github.com/masterlxz/polis" in agente
    assert "Mozilla" not in agente


def test_download_nao_aceita_trocar_o_user_agent_por_requisicao(server, clock, tmp_path):
    with pytest.raises(TypeError):
        make_client(clock).download(url(server), tmp_path / "a.zip", user_agent="Mozilla/5.0")


# --- Esquema e redirecionamento ---


@pytest.mark.parametrize("endereco", ["file:///etc/hostname", "ftp://example.org/a.zip"])
def test_recusa_esquema_que_nao_seja_https(clock, tmp_path, endereco):
    with pytest.raises(DownloadError):
        PoliteClient(sleep=clock.sleep, clock=clock.monotonic).download(
            endereco, tmp_path / "a.zip"
        )
    assert list(tmp_path.iterdir()) == []


def test_por_padrao_recusa_http_sem_tls(server, clock, tmp_path):
    cliente = PoliteClient(sleep=clock.sleep, clock=clock.monotonic)
    with pytest.raises(DownloadError):
        cliente.download(url(server), tmp_path / "a.zip")
    assert server.requests == []


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_recusa_redirecionamento_e_nao_segue_o_destino(server, clock, tmp_path, status):
    server.script = [Resposta(status=status, headers={"Location": "/outro.zip"}, body=b"")]
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert [r["path"] for r in server.requests] == ["/arquivo.zip"]
    assert str(status) in str(erro.value)
    assert list(tmp_path.iterdir()) == []


# --- Pausa entre requisições (decisão 5) ---


def test_primeira_requisicao_nao_espera(server, clock, tmp_path):
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == []


def test_segunda_requisicao_ao_mesmo_host_espera_a_pausa_de_3_segundos(server, clock, tmp_path):
    cliente = make_client(clock)
    cliente.download(url(server), tmp_path / "a.zip")
    cliente.download(url(server), tmp_path / "b.zip")
    assert clock.sleeps == [3.0]


def test_nao_espera_se_a_pausa_ja_passou(server, clock, tmp_path):
    cliente = make_client(clock)
    cliente.download(url(server), tmp_path / "a.zip")
    clock.now += 10
    cliente.download(url(server), tmp_path / "b.zip")
    assert clock.sleeps == []


def test_pausa_configuravel(server, clock, tmp_path):
    cliente = make_client(clock, min_interval=5.0)
    cliente.download(url(server), tmp_path / "a.zip")
    cliente.download(url(server), tmp_path / "b.zip")
    assert clock.sleeps == [5.0]


# --- 429 e 503: recuo (decisão 5) ---


def test_429_recua_3_segundos_e_tenta_de_novo(server, clock, tmp_path):
    server.script = [Resposta(status=429, body=b""), Resposta()]
    resultado = make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [3.0]
    assert len(server.requests) == 2
    assert resultado.size_bytes == len(CORPO)


def test_recuo_dobra_a_cada_tentativa(server, clock, tmp_path):
    falha = Resposta(status=503, body=b"")
    server.script = [falha, falha, falha, Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [3.0, 6.0, 12.0]


def test_desiste_depois_de_4_tentativas_e_nao_deixa_arquivo(server, clock, tmp_path):
    server.script = [Resposta(status=429, body=b"")]
    with pytest.raises(DownloadError):
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert len(server.requests) == 4
    assert clock.sleeps == [3.0, 6.0, 12.0]
    assert list(tmp_path.iterdir()) == []


def test_retry_after_maior_que_o_recuo_vale(server, clock, tmp_path):
    server.script = [Resposta(status=503, headers={"Retry-After": "30"}, body=b""), Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [30.0]


def test_retry_after_menor_que_o_recuo_nao_encurta_a_espera(server, clock, tmp_path):
    server.script = [Resposta(status=429, headers={"Retry-After": "1"}, body=b""), Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [3.0]


def test_retry_after_em_data_http(server, clock, tmp_path):
    data = formatdate(WALL + 45, usegmt=True)
    server.script = [Resposta(status=429, headers={"Retry-After": data}, body=b""), Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [45.0]


def test_retry_after_invalido_e_ignorado(server, clock, tmp_path):
    server.script = [Resposta(status=429, headers={"Retry-After": "logo"}, body=b""), Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [3.0]


def test_espera_tem_teto_de_300_segundos(server, clock, tmp_path):
    server.script = [Resposta(status=503, headers={"Retry-After": "100000"}, body=b""), Resposta()]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [300.0]


def test_retry_after_em_resposta_200_e_ignorado(server, clock, tmp_path):
    server.script = [Resposta(headers={"Retry-After": "30"})]
    make_client(clock).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == []


# --- 403 e bloqueio: para e não contorna (decisão 5) ---


def test_403_levanta_bloqueio_sem_tentar_de_novo(server, clock, tmp_path):
    server.script = [Resposta(status=403, body=b"Access Denied")]
    with pytest.raises(BlockedError):
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert len(server.requests) == 1
    assert clock.sleeps == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("status", [401, 451])
def test_401_e_451_tambem_contam_como_bloqueio(server, clock, tmp_path, status):
    server.script = [Resposta(status=status, body=b"")]
    with pytest.raises(BlockedError):
        make_client(clock).download(url(server), tmp_path / "a.zip")


def test_depois_do_bloqueio_o_host_nao_recebe_mais_requisicoes(server, clock, tmp_path):
    server.script = [Resposta(status=403, body=b""), Resposta()]
    cliente = make_client(clock)
    with pytest.raises(BlockedError):
        cliente.download(url(server), tmp_path / "a.zip")
    with pytest.raises(BlockedError):
        cliente.download(url(server, "/outro.zip"), tmp_path / "b.zip")
    assert len(server.requests) == 1


def test_o_bloqueio_vale_so_para_a_instancia_que_o_recebeu(server, clock, tmp_path):
    server.script = [Resposta(status=403, body=b""), Resposta()]
    with pytest.raises(BlockedError):
        make_client(clock).download(url(server), tmp_path / "a.zip")
    resultado = make_client(clock).download(url(server), tmp_path / "b.zip")
    assert resultado.size_bytes == len(CORPO)


# --- Outras falhas: erro, sem retentativa ---


@pytest.mark.parametrize("status", [404, 500, 502, 504])
def test_outros_erros_http_nao_sao_retentados_nem_viram_bloqueio(server, clock, tmp_path, status):
    server.script = [Resposta(status=status, body=b"")]
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert not isinstance(erro.value, BlockedError)
    assert len(server.requests) == 1
    assert str(status) in str(erro.value)


def test_servidor_inalcancavel_e_erro_de_download(server, clock, tmp_path):
    endereco = url(server)
    server.shutdown()
    server.server_close()
    with pytest.raises(DownloadError):
        make_client(clock).download(endereco, tmp_path / "a.zip")
    assert clock.sleeps == []


def test_resposta_lenta_demais_e_erro_de_download(server, clock, tmp_path):
    server.script = [Resposta(delay=1.5)]
    with pytest.raises(DownloadError):
        make_client(clock, timeout=0.2).download(url(server), tmp_path / "a.zip")
    assert list(tmp_path.iterdir()) == []


# --- Integridade do download (ADR 0005, decisão 9) ---


def test_download_cortado_e_erro_e_nao_deixa_arquivo(server, clock, tmp_path):
    server.script = [Resposta(body=b"x" * 40, declared_length=100)]
    with pytest.raises(DownloadError):
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert list(tmp_path.iterdir()) == []


def test_falha_nao_apaga_nem_altera_o_arquivo_anterior(server, clock, tmp_path):
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"versao antiga")
    server.script = [Resposta(body=b"x" * 40, declared_length=100)]
    with pytest.raises(DownloadError):
        make_client(clock).download(url(server), destino)
    assert destino.read_bytes() == b"versao antiga"
    assert [p.name for p in tmp_path.iterdir()] == ["a.zip"]


def test_tamanho_declarado_acima_do_limite_e_recusado_antes_de_baixar(server, clock, tmp_path):
    with pytest.raises(DownloadError):
        make_client(clock, max_bytes=100).download(url(server), tmp_path / "a.zip")
    assert list(tmp_path.iterdir()) == []


def test_limite_vale_tambem_sem_content_length(server, clock, tmp_path):
    server.script = [Resposta(body=b"x" * 5000, chunked=True)]
    with pytest.raises(DownloadError):
        make_client(clock, max_bytes=1000).download(url(server), tmp_path / "a.zip")
    assert list(tmp_path.iterdir()) == []


# --- Segurança dos erros (mesma regra do leitor de ZIP) ---


def test_erro_nao_cita_corpo_da_resposta_nem_query_da_url(server, clock, tmp_path):
    server.script = [Resposta(status=500, body=b"CPF 123.456.789-09")]
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server, "/a.zip?token=segredo"), tmp_path / "a.zip")
    texto = str(erro.value)
    assert "123.456.789-09" not in texto
    assert "segredo" not in texto
    assert "127.0.0.1" in texto


def test_erro_nao_carrega_contexto_da_falha_original(server, clock, tmp_path):
    server.script = [Resposta(status=500, body=b"CPF 123.456.789-09")]
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server), tmp_path / "a.zip")
    assert erro.value.__cause__ is None
    assert erro.value.__context__ is None
