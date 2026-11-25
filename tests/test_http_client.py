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
    # Gotejamento: manda o corpo 1 byte por vez e, antes de cada byte, adianta `drip_clock` em
    # `drip_step` segundos (relógio falso, sem espera real). Simula um host que entrega 1 byte a
    # cada `drip_step` s; o adiantamento vem ANTES da escrita para que o cliente, ao ler o byte
    # `n`, já veja `n * drip_step` s passados (sem corrida entre as duas threads).
    drip_clock: object = None
    drip_step: float = 0.0


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
                if resposta.drip_clock is not None:
                    for i in range(len(resposta.body)):
                        resposta.drip_clock.now += resposta.drip_step
                        self.wfile.write(resposta.body[i : i + 1])
                else:
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


# --- Limite por chamada (`max_bytes` em `download`; ADR 0031, "limites conhecidos") ---
# O cliente destes testes tem o teto padrão de 2 GiB, folgado: quem recusa é o limite da chamada.


def test_limite_por_chamada_recusa_tamanho_declarado_acima_dele_e_nao_deixa_arquivo(
    server, clock, tmp_path
):
    # CORPO tem 1000 bytes e o servidor declara Content-Length: 1000; o limite é 999.
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server), tmp_path / "a.zip", max_bytes=len(CORPO) - 1)
    assert "limite de 999 bytes" in str(erro.value)
    assert list(tmp_path.iterdir()) == []


def test_limite_por_chamada_vale_tambem_sem_content_length_e_nao_deixa_arquivo(
    server, clock, tmp_path
):
    server.script = [Resposta(body=b"x" * 5000, chunked=True)]
    with pytest.raises(DownloadError) as erro:
        make_client(clock).download(url(server), tmp_path / "a.zip", max_bytes=4999)
    assert "limite de 4999 bytes" in str(erro.value)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("chunked", [False, True], ids=["com_tamanho", "em_fluxo"])
def test_arquivo_exatamente_no_limite_por_chamada_e_aceito(server, clock, tmp_path, chunked):
    server.script = [Resposta(chunked=chunked)]
    destino = tmp_path / "a.zip"
    resultado = make_client(clock).download(url(server), destino, max_bytes=len(CORPO))
    assert destino.read_bytes() == CORPO
    assert resultado.size_bytes == len(CORPO)


@pytest.mark.parametrize("argumentos", [{}, {"max_bytes": None}], ids=["omitido", "none"])
def test_sem_limite_por_chamada_vale_so_o_teto_do_cliente(server, clock, tmp_path, argumentos):
    # Teto do cliente = 1000 bytes (o tamanho de CORPO): aceita 1000 e recusa 1001.
    cliente = make_client(clock, max_bytes=len(CORPO))
    resultado = cliente.download(url(server), tmp_path / "a.zip", **argumentos)
    assert resultado.size_bytes == len(CORPO)
    server.script = [Resposta(body=CORPO + b"x")]
    with pytest.raises(DownloadError):
        cliente.download(url(server), tmp_path / "b.zip", **argumentos)
    assert [p.name for p in tmp_path.iterdir()] == ["a.zip"]


def test_teto_do_cliente_continua_valendo_quando_o_limite_por_chamada_e_maior(
    server, clock, tmp_path
):
    # O limite por chamada só reduz o teto: 10_000 não alarga os 500 do cliente.
    with pytest.raises(DownloadError) as erro:
        make_client(clock, max_bytes=500).download(
            url(server), tmp_path / "a.zip", max_bytes=10_000
        )
    assert "limite de 500 bytes" in str(erro.value)
    assert list(tmp_path.iterdir()) == []


def test_limite_por_chamada_continua_valendo_depois_de_um_429(server, clock, tmp_path):
    server.script = [Resposta(status=429, body=b""), Resposta()]
    with pytest.raises(DownloadError):
        make_client(clock).download(url(server), tmp_path / "a.zip", max_bytes=len(CORPO) - 1)
    assert len(server.requests) == 2
    assert clock.sleeps == [3.0]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("invalido", [0, -1, True, False, 1.5, "10"])
def test_limite_por_chamada_invalido_levanta_value_error_antes_de_abrir_rede(
    server, clock, tmp_path, invalido
):
    with pytest.raises(ValueError):
        make_client(clock).download(url(server), tmp_path / "a.zip", max_bytes=invalido)
    assert server.requests == []
    assert list(tmp_path.iterdir()) == []


# --- Prazo total por download (`total_timeout`; nota em "Consequências" do ADR 0008) ---
# O `timeout` por operação de socket (30 s) não limita um host que manda 1 byte a cada 29 s: cada
# `recv` volta antes de estourar. Estes testes usam o gotejamento de `Resposta` (relógio falso
# adiantado pelo servidor) e conferem que o relógio injetado do cliente corta o download. Os que
# precisam contar as leituras ou isolar a leitura final usam uma resposta falsa injetada em
# `_opener.open` (`RespostaFalsa`), sem rede.

TIMEOUT_POR_OPERACAO = 30.0
PASSO_LENTO = 29.0  # menor que o timeout por operação: nenhuma leitura estoura sozinha


def gotejamento(clock, bytes_, passo=PASSO_LENTO):
    return Resposta(body=b"x" * bytes_, drip_clock=clock, drip_step=passo)


class RespostaFalsa:
    """Resposta que o cliente lê só por `read1`; cada passo é (segundos a adiantar, bytes)."""

    def __init__(self, clock, passos=()):
        self.headers = {}
        self.chamadas_read1 = 0
        self._clock = clock
        self._passos = iter(passos)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        pass

    def read(self, *args):
        raise AssertionError("o cliente deve ler com read1: read encadeia leituras de socket")

    def read1(self, tamanho=-1):
        self.chamadas_read1 += 1
        avanco, dados = next(self._passos, (0.0, b""))
        self._clock.now += avanco
        return dados


def cliente_com_resposta_falsa(clock, resposta, *, avanco_na_abertura=0.0, **kwargs):
    """`resposta` pode ser uma lista (uma por abertura; a última se repete). Cada abertura
    adianta o relógio em `avanco_na_abertura` s (conexão, TLS e cabeçalhos lentos)."""
    respostas = list(resposta) if isinstance(resposta, list) else [resposta]
    cliente = make_client(clock, **kwargs)
    cliente.timeouts_pedidos = []

    def abrir(request, timeout):
        cliente.timeouts_pedidos.append(timeout)
        clock.now += avanco_na_abertura
        return respostas.pop(0) if len(respostas) > 1 else respostas[0]

    cliente._opener.open = abrir
    return cliente


URL_FALSA = "http://127.0.0.1:9/a.zip"


def test_gotejamento_abaixo_do_timeout_por_operacao_e_cortado_pelo_prazo_total(
    server, clock, tmp_path
):
    assert PASSO_LENTO < TIMEOUT_POR_OPERACAO
    server.script = [gotejamento(clock, 20)]  # 20 bytes x 29 s = 580 s, prazo de 100 s
    cliente = make_client(clock, timeout=TIMEOUT_POR_OPERACAO, total_timeout=100)
    with pytest.raises(DownloadError) as erro:
        cliente.download(url(server, "/a.zip?token=segredo"), tmp_path / "a.zip")
    texto = str(erro.value)
    assert texto == "Download de 127.0.0.1 acima do prazo de 100 segundos."
    assert "segredo" not in texto
    assert erro.value.__context__ is None
    assert len(server.requests) == 1
    assert list(tmp_path.iterdir()) == []


def test_prazo_vencido_nao_altera_o_arquivo_anterior_nem_deixa_part(server, clock, tmp_path):
    destino = tmp_path / "a.zip"
    destino.write_bytes(b"versao antiga")
    server.script = [gotejamento(clock, 20)]
    with pytest.raises(DownloadError):
        make_client(clock, total_timeout=100).download(url(server), destino)
    assert destino.read_bytes() == b"versao antiga"
    assert [p.name for p in tmp_path.iterdir()] == ["a.zip"]


@pytest.mark.parametrize(
    ("bytes_", "aceito"), [(60, True), (61, False)], ids=["1800s_exatos", "1830s"]
)
def test_prazo_padrao_e_de_1800_segundos_exatos(server, clock, tmp_path, bytes_, aceito):
    # Sem `total_timeout`: 60 bytes x 30 s = 1800 s passa (e o conteúdo sai íntegro);
    # 61 bytes x 30 s = 1830 s estoura.
    server.script = [gotejamento(clock, bytes_, 30.0)]
    destino = tmp_path / "a.zip"
    if aceito:
        resultado = make_client(clock).download(url(server), destino)
        assert destino.read_bytes() == b"x" * bytes_
        assert resultado.sha256 == hashlib.sha256(b"x" * bytes_).hexdigest()
    else:
        with pytest.raises(DownloadError) as erro:
            make_client(clock).download(url(server), destino)
        assert "acima do prazo de 1800 segundos" in str(erro.value)
        assert list(tmp_path.iterdir()) == []


def test_le_a_resposta_por_read1_e_corta_na_primeira_checagem_depois_do_prazo(clock, tmp_path):
    # Cada read1 devolve 1 byte e custa 29 s; prazo de 100 s: 29, 58, 87 passam e a 4a (116 s)
    # corta. Com `read` (mutação) o fake levanta AssertionError; sem checar a cada volta, leria
    # os 1000 passos do fim.
    resposta = RespostaFalsa(clock, [(29.0, b"x")] * 1000)
    cliente = cliente_com_resposta_falsa(clock, resposta, total_timeout=100)
    with pytest.raises(DownloadError) as erro:
        cliente.download(URL_FALSA, tmp_path / "a.zip")
    assert "acima do prazo de 100 segundos" in str(erro.value)
    assert resposta.chamadas_read1 == 4
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("avanco_no_fim", "aceito"), [(100.0, True), (101.0, False)], ids=["no_prazo", "estoura_no_eof"]
)
def test_a_leitura_que_devolve_o_fim_tambem_conta_no_prazo(clock, tmp_path, avanco_no_fim, aceito):
    # Os dados chegam no relógio inicial; só a leitura que devolve b"" avança o relógio. Um
    # download completo cuja leitura final passa do prazo falha (intencional).
    resposta = RespostaFalsa(clock, [(0.0, b"abc"), (avanco_no_fim, b"")])
    cliente = cliente_com_resposta_falsa(clock, resposta, total_timeout=100)
    destino = tmp_path / "a.zip"
    if aceito:
        assert cliente.download(URL_FALSA, destino).size_bytes == 3
    else:
        with pytest.raises(DownloadError) as erro:
            cliente.download(URL_FALSA, destino)
        assert "acima do prazo de 100 segundos" in str(erro.value)
        assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("avanco_no_corpo", "aceito"), [(30.0, True), (50.0, False)], ids=["90s", "110s"]
)
def test_o_prazo_comeca_antes_da_abertura_e_conta_conexao_e_cabecalhos(
    clock, tmp_path, avanco_no_corpo, aceito
):
    # A abertura (conexão, TLS, cabeçalhos) leva 60 s; o prazo é de 100 s. Corpo em +30 s soma
    # 90 s (passa); em +50 s soma 110 s (estoura). Se `started` fosse lido depois de `_open`, os
    # dois casos passariam.
    resposta = RespostaFalsa(clock, [(avanco_no_corpo, b"x")])
    cliente = cliente_com_resposta_falsa(
        clock, resposta, avanco_na_abertura=60.0, total_timeout=100
    )
    destino = tmp_path / "a.zip"
    if aceito:
        assert cliente.download(URL_FALSA, destino).size_bytes == 1
    else:
        with pytest.raises(DownloadError) as erro:
            cliente.download(URL_FALSA, destino)
        assert "acima do prazo de 100 segundos" in str(erro.value)
        assert list(tmp_path.iterdir()) == []


def test_pausa_de_cortesia_antes_da_abertura_nao_conta_no_prazo(clock, tmp_path):
    # Segunda chamada ao mesmo host espera 1000 s de pausa (o `sleep` falso adianta o relógio);
    # o prazo é de 100 s e o corpo leva 50 s: passa, porque `started` vem depois da pausa.
    respostas = [RespostaFalsa(clock), RespostaFalsa(clock, [(50.0, b"x")])]
    cliente = cliente_com_resposta_falsa(clock, respostas, min_interval=1000.0, total_timeout=100)
    cliente.download(URL_FALSA, tmp_path / "a.zip")
    resultado = cliente.download(URL_FALSA, tmp_path / "b.zip")
    assert clock.sleeps == [1000.0]
    assert resultado.size_bytes == 1


@pytest.mark.parametrize(
    ("timeout", "total_timeout", "esperado"),
    [
        (30, 0.2, 0.2),
        (30, 5, 5),
        (30, 1800, 30),
        (30, float("inf"), 30),
        (0.5, 100, 0.5),
    ],
    ids=["prazo_menor", "prazo_inteiro_menor", "prazo_maior", "prazo_infinito", "timeout_menor"],
)
def test_timeout_da_abertura_e_o_menor_entre_o_por_operacao_e_o_prazo_total(
    clock, tmp_path, timeout, total_timeout, esperado
):
    cliente = cliente_com_resposta_falsa(
        clock, RespostaFalsa(clock), timeout=timeout, total_timeout=total_timeout
    )
    cliente.download(URL_FALSA, tmp_path / "a.zip")
    assert cliente.timeouts_pedidos == [esperado]


def test_prazo_infinito_desliga_o_prazo(clock, tmp_path):
    resposta = RespostaFalsa(clock, [(1e9, b"x")] * 3)
    cliente = cliente_com_resposta_falsa(clock, resposta, total_timeout=float("inf"))
    assert cliente.download(URL_FALSA, tmp_path / "a.zip").size_bytes == 3


@pytest.mark.parametrize(
    ("total_timeout", "texto"), [(1_000_000, "1000000"), (0.5, "0.5"), (1800.0, "1800")]
)
def test_mensagem_do_prazo_nao_usa_notacao_cientifica(clock, tmp_path, total_timeout, texto):
    resposta = RespostaFalsa(clock, [(2_000_000.0, b"x")])
    cliente = cliente_com_resposta_falsa(clock, resposta, total_timeout=total_timeout)
    with pytest.raises(DownloadError) as erro:
        cliente.download(URL_FALSA, tmp_path / "a.zip")
    assert str(erro.value) == f"Download de 127.0.0.1 acima do prazo de {texto} segundos."


@pytest.mark.parametrize(
    ("passo", "aceito"), [(25.0, True), (26.0, False)], ids=["no_prazo_exato", "um_pouco_acima"]
)
def test_prazo_exato_passa_e_acima_dele_falha(server, clock, tmp_path, passo, aceito):
    # 4 bytes x 25 s = 100 s (= prazo, aceito); 4 bytes x 26 s = 104 s (> prazo, recusado).
    server.script = [gotejamento(clock, 4, passo)]
    cliente = make_client(clock, total_timeout=100)
    if aceito:
        assert cliente.download(url(server), tmp_path / "a.zip").size_bytes == 4
    else:
        with pytest.raises(DownloadError):
            cliente.download(url(server), tmp_path / "a.zip")
        assert list(tmp_path.iterdir()) == []


def test_espera_de_429_nao_conta_no_prazo_do_download(server, clock, tmp_path):
    # Retry-After de 90 s + download de 100 s: soma 190 s, mas o prazo (100 s) só vale para o
    # download da resposta que deu certo.
    server.script = [
        Resposta(status=429, headers={"Retry-After": "90"}, body=b""),
        gotejamento(clock, 4, 25.0),
    ]
    resultado = make_client(clock, total_timeout=100).download(url(server), tmp_path / "a.zip")
    assert clock.sleeps == [90.0]
    assert resultado.size_bytes == 4


def test_cada_download_tem_o_proprio_prazo(server, clock, tmp_path):
    server.script = [gotejamento(clock, 4, 25.0)]
    cliente = make_client(clock, total_timeout=100)
    cliente.download(url(server), tmp_path / "a.zip")
    cliente.download(url(server), tmp_path / "b.zip")  # 200 s no relógio, 100 s por download
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.zip", "b.zip"]


@pytest.mark.parametrize("invalido", [0, -1, 0.0, -0.5, True, False, "10", None, float("nan")])
def test_prazo_total_invalido_levanta_value_error_no_construtor(clock, invalido):
    with pytest.raises(ValueError):
        make_client(clock, total_timeout=invalido)


@pytest.mark.parametrize("valido", [5, 0.5, 1800.0, float("inf")])
def test_prazo_total_valido_e_aceito(clock, valido):
    make_client(clock, total_timeout=valido)


@pytest.mark.parametrize(
    "invalido", [None, 0, -1, 0.0, True, False, "30", float("nan"), float("inf")]
)
def test_timeout_por_operacao_invalido_levanta_value_error_no_construtor(clock, invalido):
    # Antes, `timeout=None` chegava ao `min` de `_open` como TypeError cru.
    with pytest.raises(ValueError):
        make_client(clock, timeout=invalido)


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
