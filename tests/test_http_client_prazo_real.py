"""Watchdog do prazo total do `PoliteClient` (P-20; nota em "Consequências" do ADR 0008).

O prazo conferido entre leituras do corpo não alcança o que o `http.client` lê por conta própria
(linha de status e cabeçalhos, linha do tamanho do pedaço, trailers). Aqui o servidor é um socket
cru em 127.0.0.1 que goteja 1 byte a cada `PASSO` s, e o prazo é de tempo real (a thread do
watchdog espera de verdade). O relógio e o `sleep` do cliente continuam falsos: o relógio não anda,
então só o watchdog pode cortar. Cada gotejamento dura bem mais que o prazo; sem o watchdog o
download termina bem e o teste falha por não levantar `DownloadError`. O socket recebe
`min(timeout, total_timeout)` = 0,3 s por operação, contra um passo de 0,05 s (folga de 6x).
"""

import socket
import ssl
import subprocess
import threading
import time

import pytest

from apps.sources import http_client
from apps.sources.http_client import DownloadError, PoliteClient

PRAZO = 0.3
PASSO = 0.05
LIMITE_DE_ESPERA = 2.0  # o corte tem de vir bem antes do gotejamento terminar (>= 3 s)
HEADERS = b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\n\r\n"
HEADERS_CHUNKED = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
PREENCHIMENTO = b"a" * 80


class Gotejador:
    """Servidor TCP cru: lê o pedido e escreve `imediato` de uma vez e `lento` 1 byte por vez."""

    def __init__(self, imediato, lento, contexto_tls=None):
        self.imediato = imediato
        self.lento = lento
        self.contexto_tls = contexto_tls
        self.encerrar = threading.Event()
        self.escutando = socket.socket()
        self.escutando.bind(("127.0.0.1", 0))
        self.escutando.listen()
        self.porta = self.escutando.getsockname()[1]
        threading.Thread(target=self._aceitar, daemon=True).start()

    def _aceitar(self):
        while True:
            try:
                conexao, _ = self.escutando.accept()
            except OSError:
                return
            threading.Thread(target=self._servir, args=(conexao,), daemon=True).start()

    def _servir(self, conexao):
        with conexao:
            try:
                if self.contexto_tls is not None:
                    conexao = self.contexto_tls.wrap_socket(conexao, server_side=True)
                pedido = b""
                while b"\r\n\r\n" not in pedido:
                    dados = conexao.recv(4096)
                    if not dados:
                        return
                    pedido += dados
                conexao.sendall(self.imediato)
                for i in range(len(self.lento)):
                    if self.encerrar.wait(PASSO):
                        return
                    conexao.sendall(self.lento[i : i + 1])
            except OSError:
                return

    @property
    def url(self):
        esquema = "http" if self.contexto_tls is None else "https"
        host = "127.0.0.1" if self.contexto_tls is None else "localhost"
        return f"{esquema}://{host}:{self.porta}/arquivo.zip"

    def fechar(self):
        self.encerrar.set()
        self.escutando.close()


@pytest.fixture
def gotejador():
    criados = []

    def criar(imediato, lento, contexto_tls=None):
        servidor = Gotejador(imediato, lento, contexto_tls)
        criados.append(servidor)
        return servidor

    yield criar
    for servidor in criados:
        servidor.fechar()


@pytest.fixture
def tls(tmp_path, monkeypatch):
    """Contexto de servidor com certificado autoassinado de `localhost` (gerado com `openssl`).

    O cliente confia nele por `SSL_CERT_FILE`, lido quando o `PoliteClient` é construído (o
    contexto padrão carrega as CAs do ambiente). Sem `openssl` no ambiente o teste é pulado.
    """
    certificado, chave = tmp_path / "cert.pem", tmp_path / "chave.pem"
    try:
        base = "openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=localhost".split()
        extensao = ["-addext", "subjectAltName=DNS:localhost"]
        saida = ["-keyout", str(chave), "-out", str(certificado)]
        subprocess.run(base + extensao + saida, check=True, capture_output=True)  # noqa: S603
    except FileNotFoundError:
        pytest.skip("openssl não encontrado")
    contexto = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    contexto.load_cert_chain(certificado, chave)
    monkeypatch.setenv("SSL_CERT_FILE", str(certificado))
    return contexto


class RelogioParado:
    now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, segundos):
        pass


def cliente(**kwargs):
    relogio = RelogioParado()
    kwargs.setdefault("total_timeout", PRAZO)
    return PoliteClient(
        allowed_schemes=("http", "https"),
        timeout=30.0,
        sleep=relogio.sleep,
        clock=relogio.monotonic,
        **kwargs,
    )


def baixar_e_medir(servidor, destino, **kwargs):
    inicio = time.monotonic()
    with pytest.raises(DownloadError) as erro:
        cliente(**kwargs).download(servidor.url, destino)
    return str(erro.value), time.monotonic() - inicio


MENSAGEM = f"Download de 127.0.0.1 acima do prazo de {PRAZO:g} segundos."


# Se o host goteja a linha de status e os cabeçalhos, o cliente corta no prazo.
def test_cabecalhos_gotejados_sao_cortados_pelo_prazo(gotejador, tmp_path):
    servidor = gotejador(b"", HEADERS[:-2] + b"X-Pad: " + PREENCHIMENTO + b"\r\n\r\nabcd")
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == MENSAGEM
    assert demorou < LIMITE_DE_ESPERA
    assert list(tmp_path.iterdir()) == []


# Se o host goteja a linha do tamanho do pedaço (chunked), o cliente corta no prazo.
def test_linha_de_tamanho_do_pedaco_gotejada_e_cortada_pelo_prazo(gotejador, tmp_path):
    servidor = gotejador(HEADERS_CHUNKED, b"0" * 80 + b"1\r\nx\r\n0\r\n\r\n")
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == MENSAGEM
    assert demorou < LIMITE_DE_ESPERA
    assert list(tmp_path.iterdir()) == []


# Se o host goteja os trailers depois do último pedaço, o cliente corta no prazo.
def test_trailers_gotejados_sao_cortados_pelo_prazo(gotejador, tmp_path):
    servidor = gotejador(
        HEADERS_CHUNKED + b"1\r\nx\r\n0\r\n", b"X-T: " + PREENCHIMENTO + b"\r\n\r\n"
    )
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == MENSAGEM
    assert demorou < LIMITE_DE_ESPERA
    assert list(tmp_path.iterdir()) == []


# Se o host goteja o corpo com Content-Length, o cliente corta no prazo (o relógio parado
# não ajuda: quem corta é o watchdog).
def test_corpo_gotejado_e_cortado_pelo_prazo(gotejador, tmp_path):
    servidor = gotejador(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n", b"x" * 100)
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == MENSAGEM
    assert demorou < LIMITE_DE_ESPERA


# Se o prazo estoura com um arquivo anterior no destino, o arquivo anterior fica intacto.
def test_prazo_estourado_nao_altera_o_arquivo_anterior(gotejador, tmp_path):
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"anterior")
    servidor = gotejador(HEADERS_CHUNKED, b"0" * 80 + b"1\r\nx\r\n0\r\n\r\n")
    baixar_e_medir(servidor, destino)
    assert destino.read_bytes() == b"anterior"
    assert [p.name for p in tmp_path.iterdir()] == ["a.zip"]


# Se o host responde rápido e íntegro, baixa normal e não deixa a thread do watchdog viva.
def test_download_normal_passa_e_nao_deixa_thread(gotejador, tmp_path):
    servidor = gotejador(HEADERS + b"abcd", b"")
    resultado = cliente().download(servidor.url, tmp_path / "a.zip")
    assert resultado.size_bytes == 4
    assert (tmp_path / "a.zip").read_bytes() == b"abcd"
    assert not [t for t in threading.enumerate() if t.name == http_client.WATCHDOG_THREAD_NAME]


# Se o prazo é infinito, nenhuma thread de watchdog é criada.
def test_prazo_infinito_nao_cria_thread(gotejador, tmp_path):
    assert http_client._Watchdog(float("inf"))._timer is None
    servidor = gotejador(HEADERS + b"abcd", b"")
    resultado = cliente(total_timeout=float("inf")).download(servidor.url, tmp_path / "a.zip")
    assert resultado.size_bytes == 4
    assert not [t for t in threading.enumerate() if t.name == http_client.WATCHDOG_THREAD_NAME]


# Se o prazo estoura, o erro não é retentado: um só pedido chega ao servidor.
def test_prazo_estourado_nao_e_retentado(gotejador, tmp_path):
    servidor = gotejador(HEADERS_CHUNKED, b"0" * 80 + b"1\r\nx\r\n0\r\n\r\n")
    pedidos = []
    original = servidor._servir

    def contar(conexao):
        pedidos.append(1)
        original(conexao)

    servidor._servir = contar
    baixar_e_medir(servidor, tmp_path / "a.zip")
    assert len(pedidos) == 1


# Se o prazo vence antes de a conexão ficar pronta, o socket é cortado ao ser registrado.
def test_prazo_vencido_antes_da_conexao_corta_o_socket_ao_registrar():
    watchdog = http_client._Watchdog(0.01)
    try:
        assert watchdog._timer is not None
        watchdog._timer.join(5)
        assert watchdog.expired
        lado_do_cliente, lado_do_servidor = socket.socketpair()
        with lado_do_cliente, lado_do_servidor:
            lado_do_cliente.settimeout(5)
            watchdog.register(lado_do_cliente)
            assert lado_do_cliente.recv(1) == b""
    finally:
        watchdog.stop()


# --- Mesmos cortes sobre TLS (o socket registrado é o `SSLSocket`) ---


# Se o host TLS goteja a linha do tamanho do pedaço, o cliente corta no prazo.
def test_tls_linha_de_tamanho_do_pedaco_gotejada_e_cortada_pelo_prazo(gotejador, tls, tmp_path):
    servidor = gotejador(HEADERS_CHUNKED, b"0" * 80 + b"1\r\nx\r\n0\r\n\r\n", tls)
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == "Download de localhost acima do prazo de 0.3 segundos."
    assert demorou < LIMITE_DE_ESPERA
    assert list(tmp_path.iterdir()) == []


# Se o host TLS goteja o corpo, o cliente corta no prazo.
def test_tls_corpo_gotejado_e_cortado_pelo_prazo(gotejador, tls, tmp_path):
    servidor = gotejador(b"HTTP/1.1 200 OK\r\nContent-Length: 100\r\n\r\n", b"x" * 100, tls)
    mensagem, demorou = baixar_e_medir(servidor, tmp_path / "a.zip")
    assert mensagem == "Download de localhost acima do prazo de 0.3 segundos."
    assert demorou < LIMITE_DE_ESPERA


# Se o host TLS responde rápido e íntegro, baixa normal (o certificado é verificado de verdade).
def test_tls_download_normal_passa(gotejador, tls, tmp_path):
    servidor = gotejador(HEADERS + b"abcd", b"", tls)
    resultado = cliente().download(servidor.url, tmp_path / "a.zip")
    assert (tmp_path / "a.zip").read_bytes() == b"abcd"
    assert resultado.size_bytes == 4
