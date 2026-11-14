"""Envio do alerta por webhook (Etapa 0, plano da Sessão 76).

`post_text(url, texto)` manda o texto puro por POST. O que mais importa: só `https` por padrão
(o servidor de teste é http, então os testes pedem `allowed_schemes` de propósito), redirecionamento
recusado (um 3xx mandaria o texto para outro lugar), tempo limite, e NENHUM erro cita a URL, que
costuma carregar o segredo (token do Telegram, tópico do ntfy). Servidor local, sem rede externa.
"""

import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

SEGREDO = "segredo-do-topico-123"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", "0"))
        corpo = self.rfile.read(tamanho)
        self.server.requests.append(
            {"path": self.path, "headers": dict(self.headers), "body": corpo}
        )
        resposta = self.server.script[0]
        if resposta.get("delay"):
            time.sleep(resposta["delay"])
        self.send_response(resposta["status"])
        for nome, valor in resposta.get("headers", {}).items():
            self.send_header(nome, valor)
        self.send_header("Content-Length", "0")
        self.end_headers()


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.requests = []
    srv.script = [{"status": 200}]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def _url(server, caminho=f"/{SEGREDO}"):
    return f"http://127.0.0.1:{server.server_address[1]}{caminho}"


def _postar(url, texto="olá", **extra):
    from apps.sources import webhook

    return webhook.post_text(url, texto, allowed_schemes=("http",), **extra)


def test_manda_o_texto_puro_em_utf8_por_post(server):
    _postar(_url(server), "ALERTA fonte/x: Atrasado, não coletou")

    pedido = server.requests[0]
    assert pedido["path"] == f"/{SEGREDO}"
    assert pedido["body"] == "ALERTA fonte/x: Atrasado, não coletou".encode()
    assert pedido["headers"]["Content-Type"].startswith("text/plain")
    assert "utf-8" in pedido["headers"]["Content-Type"].lower()


def test_resposta_2xx_e_sucesso_sem_retorno(server):
    server.script = [{"status": 204}]

    assert _postar(_url(server)) is None


def test_erro_do_servidor_levanta_webhookerror_sem_a_url(server):
    from apps.sources.webhook import WebhookError

    server.script = [{"status": 500}]

    with pytest.raises(WebhookError) as erro:
        _postar(_url(server))

    assert "500" in str(erro.value)
    assert SEGREDO not in str(erro.value)
    assert "127.0.0.1" not in str(erro.value)


def test_redirecionamento_e_recusado_e_o_destino_nao_recebe_nada(server):
    from apps.sources.webhook import WebhookError

    server.script = [{"status": 302, "headers": {"Location": _url(server, "/destino")}}]

    with pytest.raises(WebhookError) as erro:
        _postar(_url(server))

    assert "302" in str(erro.value)
    assert [pedido["path"] for pedido in server.requests] == [f"/{SEGREDO}"]


def test_so_https_por_padrao_e_nao_chega_a_conectar(server):
    from apps.sources import webhook

    with pytest.raises(webhook.WebhookError) as erro:
        webhook.post_text(_url(server), "olá")

    assert server.requests == []
    assert SEGREDO not in str(erro.value)


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.org/x", "javascript:alert(1)"]
)
def test_outros_esquemas_sao_recusados(url):
    from apps.sources import webhook

    with pytest.raises(webhook.WebhookError):
        webhook.post_text(url, "olá", allowed_schemes=("http", "https"))


def test_url_sem_host_e_recusada():
    from apps.sources import webhook

    with pytest.raises(webhook.WebhookError):
        webhook.post_text("https:///so-caminho", "olá")


def test_falha_de_rede_levanta_webhookerror_sem_a_url():
    from apps.sources.webhook import WebhookError

    with pytest.raises(WebhookError) as erro:
        _postar(f"http://127.0.0.1:9/{SEGREDO}")

    assert SEGREDO not in str(erro.value)
    assert erro.value.__cause__ is None
    assert erro.value.__context__ is None


def test_tempo_limite_estoura_em_webhookerror(server):
    from apps.sources.webhook import WebhookError

    server.script = [{"status": 200, "delay": 3}]
    antes = time.monotonic()

    with pytest.raises(WebhookError):
        _postar(_url(server), timeout=0.3)

    assert time.monotonic() - antes < 2.5
