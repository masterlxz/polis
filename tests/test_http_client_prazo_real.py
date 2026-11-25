"""Watchdog do prazo total do `PoliteClient` (P-20; nota em "Consequências" do ADR 0008).

O prazo conferido entre leituras do corpo não alcança o que o `http.client` lê por conta própria
(linha de status e cabeçalhos, linha do tamanho do pedaço, trailers). Aqui o servidor é um socket
cru em 127.0.0.1 que goteja 1 byte a cada `PASSO` s, e o prazo é de tempo real (a thread do
watchdog espera de verdade). O relógio e o `sleep` do cliente continuam falsos: o relógio não anda,
então só o watchdog pode cortar. Cada gotejamento dura bem mais que o prazo; sem o watchdog o
download termina bem e o teste falha por não levantar `DownloadError`. O socket recebe
`min(timeout, total_timeout)` = 0,3 s por operação, contra um passo de 0,05 s (folga de 6x).
"""

import http.client
import math
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

    def __init__(self, imediato, lento, contexto_tls=None, ler_pedido=True):
        self.imediato = imediato
        self.lento = lento
        self.contexto_tls = contexto_tls
        self.ler_pedido = ler_pedido  # False: fala primeiro (o servidor TLS que goteja o aperto)
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
                while self.ler_pedido and b"\r\n\r\n" not in pedido:
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

    def criar(imediato, lento, contexto_tls=None, ler_pedido=True):
        servidor = Gotejador(imediato, lento, contexto_tls, ler_pedido)
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
    # A fixture `tls` também grava o certificado e a chave neste diretório.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["cert.pem", "chave.pem"]


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
    assert esperar_sem_threads_de_abertura()


# --- A abertura (DNS, TCP, aperto de mão TLS) também respeita o prazo total ---


def threads_de_abertura():
    return [t for t in threading.enumerate() if t.name == http_client.OPEN_THREAD_NAME]


def esperar_sem_threads_de_abertura(segundos=2.0):
    fim = time.monotonic() + segundos
    while threads_de_abertura() and time.monotonic() < fim:
        time.sleep(0.01)
    return not threads_de_abertura()


class RespostaQueFecha:
    def __init__(self):
        self.fechada = False

    def close(self):
        self.fechada = True


# Se o servidor TLS goteja o aperto de mão (começa um registro de 16 KiB e entrega 1 byte por
# vez), o cliente corta no prazo. REGRESSÃO, não prova da thread: o CPython já usa o `timeout`
# do socket (aqui `min(timeout, total_timeout)`) como prazo único do handshake, e o CI mostrou
# este teste passando antes da thread. O socket TLS ainda nem foi registrado no watchdog.
def test_aperto_de_mao_tls_gotejado_e_cortado_pelo_prazo(gotejador, tmp_path):
    servidor = gotejador(b"\x16\x03\x03\x40\x00", b"\x00" * 60, ler_pedido=False)
    inicio = time.monotonic()
    with pytest.raises(DownloadError) as erro:
        cliente().download(f"https://localhost:{servidor.porta}/arquivo.zip", tmp_path / "a.zip")
    assert str(erro.value) == "Download de localhost acima do prazo de 0.3 segundos."
    assert time.monotonic() - inicio < LIMITE_DE_ESPERA
    assert list(tmp_path.iterdir()) == []


# Se o resolvedor de nomes trava (getaddrinfo não tem timeout), o cliente corta no prazo e a
# thread abandonada termina quando o resolvedor volta.
def test_resolvedor_travado_e_cortado_pelo_prazo(tmp_path, monkeypatch):
    liberar = threading.Event()

    def getaddrinfo_travado(*args, **kwargs):
        liberar.wait(5)
        raise socket.gaierror("nome não resolvido")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo_travado)
    inicio = time.monotonic()
    try:
        with pytest.raises(DownloadError) as erro:
            cliente().download("http://trava.invalid/arquivo.zip", tmp_path / "a.zip")
        demorou = time.monotonic() - inicio
        assert str(erro.value) == "Download de trava.invalid acima do prazo de 0.3 segundos."
        assert demorou < LIMITE_DE_ESPERA
        assert list(tmp_path.iterdir()) == []
    finally:
        liberar.set()
    assert esperar_sem_threads_de_abertura()


# Se a thread abandonada termina depois com uma resposta, a resposta é fechada (sem vazar).
def test_resposta_que_chega_depois_do_abandono_e_fechada():
    handoff = http_client._Handoff()
    assert handoff.wait(0.01) is False  # ninguém rodou: o prazo estourou e a thread é abandonada
    resposta = RespostaQueFecha()
    handoff.run(lambda _url: (resposta, None, None, False), "u")
    assert resposta.fechada


# Se a thread terminou antes do estouro, a resposta fica para a thread principal (aberta).
def test_resposta_que_chega_a_tempo_nao_e_fechada():
    handoff = http_client._Handoff()
    resposta = RespostaQueFecha()
    handoff.run(lambda _url: (resposta, 200, None, False), "u")
    assert handoff.wait(0.01) is True
    assert handoff.result() == (resposta, 200, None, False)
    assert not resposta.fechada


# Se a abertura lança uma exceção inesperada na thread, ela chega à thread principal.
def test_excecao_inesperada_na_abertura_chega_a_thread_principal(tmp_path):
    def abrir(request, timeout):
        raise KeyError("falha de teste")

    c = cliente()
    c._opener.open = abrir
    with pytest.raises(KeyError):
        c.download("http://127.0.0.1:9/a.zip", tmp_path / "a.zip")
    assert esperar_sem_threads_de_abertura()


# Se o prazo é infinito, a thread principal espera a abertura sem limite de tempo.
def test_prazo_infinito_espera_a_abertura_sem_limite():
    handoff = http_client._Handoff()
    threading.Timer(0.2, handoff.run, args=(lambda _url: (None, 200, None, False), "u")).start()
    assert handoff.wait(None) is True


# Se o host responde normal, não sobra thread de abertura (http).
def test_download_normal_http_nao_deixa_thread_de_abertura(gotejador, tmp_path):
    servidor = gotejador(HEADERS + b"abcd", b"")
    cliente().download(servidor.url, tmp_path / "a.zip")
    assert esperar_sem_threads_de_abertura()


# Se uma thread de abertura abandonada acorda depois, o socket dela é registrado no watchdog da
# SUA requisição (já vencido: corta antes do envio), não no de um download posterior.
def test_socket_e_registrado_no_watchdog_da_propria_requisicao(gotejador):
    servidor = gotejador(HEADERS + b"abcd", b"")
    velho = http_client._Watchdog(math.inf)
    velho.expire()
    c = cliente()
    with pytest.raises((OSError, http.client.HTTPException)):
        c._opener.open(c._new_request(servidor.url, velho), timeout=2)
    assert velho._sock is not None


# Se não dá para criar a thread de abertura (falta de recurso), é falha de rede, não erro cru.
def test_falha_ao_criar_a_thread_de_abertura_vira_falha_de_rede(tmp_path, monkeypatch):
    original = threading.Thread.start

    def start(self):
        if self.name == http_client.OPEN_THREAD_NAME:
            raise RuntimeError("can't start new thread")
        return original(self)

    monkeypatch.setattr(threading.Thread, "start", start)
    with pytest.raises(DownloadError) as erro:
        cliente().download("http://127.0.0.1:9/a.zip", tmp_path / "a.zip")
    assert str(erro.value) == "Falha de rede ao acessar 127.0.0.1."


# Se a principal é interrompida (Ctrl-C) na espera, a thread fica abandonada e fecha a resposta.
def test_interrupcao_na_espera_abandona_a_thread_e_a_resposta_e_fechada():
    class EsperaInterrompida:
        def wait(self, timeout):
            raise KeyboardInterrupt

        def set(self):
            pass

    handoff = http_client._Handoff()
    handoff._done = EsperaInterrompida()
    with pytest.raises(KeyboardInterrupt):
        handoff.wait(1)
    resposta = RespostaQueFecha()
    handoff.run(lambda: (resposta, None, None, False))
    assert resposta.fechada
