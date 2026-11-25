"""Cliente HTTP com etiqueta de rede para a coleta (ADR 0008, decisões 4 e 5).

Regras que este módulo aplica:
- `User-Agent` próprio e honesto, fixo (`USER_AGENT`), sem parâmetro para trocá-lo (decisão 4);
- só os esquemas permitidos (https por padrão): `urllib` abriria `file:` e `ftp:` sozinho;
- redirecionamento (3xx) recusado: seguir um redirecionamento furaria a regra por host e a URL
  cadastrada no `Dataset`;
- em série, com pausa mínima entre requisições ao mesmo host (decisão 5);
- 429 e 503: recuo exponencial respeitando `Retry-After`, com teto e número máximo de tentativas;
- 403, 401 e 451: `BlockedError`, sem nova tentativa; a instância recusa novas requisições ao
  host (a coleta daquele host para; nunca se tenta de novo com outra identidade);
- qualquer outro erro HTTP ou de rede: `DownloadError`, sem nova tentativa;
- download em fluxo para um arquivo temporário ao lado do destino, conferindo `Content-Length` e
  `max_bytes` (o do cliente, que cada chamada pode só reduzir); só depois de íntegro é renomeado.
  Falha não deixa arquivo parcial nem altera um arquivo anterior (ADR 0005, decisão 9: falha
  técnica nunca apaga);
- prazo total por download (`total_timeout`, padrão 1800 s; `inf` o desliga). O `timeout` por
  operação de socket não basta: um host que manda 1 byte a cada 29 s nunca o estoura. O prazo é
  medido com o `clock` injetado e começa a contar ANTES da abertura da resposta (conexão, TLS e
  cabeçalhos entram na conta); as pausas de cortesia e a espera de 429 e 503 não contam (cada
  tentativa recomeça). O que o prazo cobre e o que NÃO cobre:
  - corpo com `Content-Length` (ou sem enquadramento): o corpo é lido por `read1` (uma leitura de
    socket por volta, em vez de `read`, que encadeia leituras) e o prazo é conferido depois de cada
    leitura, inclusive a que devolve o fim. O corte vem na primeira checagem depois do prazo, então
    pode vir até um `timeout` por operação depois dele. Um download completo cuja leitura final
    passa do prazo falha (intencional). Com `Content-Length`, o `read1` que completa o corpo já
    fecha a conexão e o seguinte devolve `b""` sem I/O, então um "fim lento" só ocorre em
    resposta chunked ou sem `Content-Length`;
  - watchdog (P-20): o `readline` do `http.client` (status, cabeçalhos, linha do tamanho de cada
    pedaço `chunked`, extensões e trailers) lê várias vezes por chamada e não devolve o controle
    a cada leitura. Por isso cada tentativa tem uma thread (`_Watchdog`, tempo REAL, não o `clock`
    injetado) que, ao vencer o prazo, faz `shutdown` do socket (o público `conn.sock`, registrado
    pela conexão ao ficar pronta); a leitura bloqueada acorda e o erro vira o do prazo. Vale para
    tudo depois que a conexão (e o TLS) fica pronta; a thread nasce antes da abertura e, se vencer
    antes, o socket é cortado ao ser registrado;
  - abertura (DNS, conexão TCP, aperto de mão TLS e cabeçalhos): o `opener.open` roda numa thread
    de trabalho (`_Handoff`, nome `polis-abertura`) e a principal espera no máximo `total_timeout`
    em tempo real. Estourou: o watchdog marca o prazo, corta o socket se já existir, e a thread é
    ABANDONADA (o `getaddrinfo` não tem timeout nem cancelamento; ela só termina quando o
    resolvedor do SO desistir, dezenas de segundos). Se ela terminar depois com uma resposta, é
    ela quem a fecha. Custo: uma thread a mais por download. O aperto de mão TLS, sozinho, já
    era limitado pelo `timeout` do socket como prazo ÚNICO do handshake inteiro (CPython; o teste
    de CI o confirma), então o ganho real desta thread é o DNS e a conexão TCP com vários
    endereços (N x `timeout`), que antes só tinham o teto do resolvedor do SO.

Segurança dos erros: as mensagens citam só o host e o status (e, quando o limite de bytes recusa,
o número do limite), nunca a URL completa (a query pode ter token), o corpo da resposta nem o
texto da exceção original. Os erros são levantados fora de qualquer `except`, então não carregam
`__context__`.

O módulo não importa Django nem toca no banco. Ligar o cliente ao `Dataset` e ao `IngestionRun`
(e mapear os erros para `error_code`) é da camada que o usa.

Atenção para quem consome:
- O cliente NÃO é seguro entre threads: o watchdog da tentativa em curso fica na instância
  (`_watchdog`). Use uma instância por thread.
- O bloqueio de host vale só para a instância; a persistência (`blocked` no `IngestionRun`) é de
  quem chama.
- Não há proxy do ambiente nem verificação de IP privado: a URL vem do cadastro do `Dataset`.
"""

import functools
import hashlib
import http.client
import math
import os
import socket
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit

USER_AGENT = "polis-coletor (+https://github.com/masterlxz/polis)"

BLOCKED_STATUSES = frozenset({401, 403, 451})
BACKOFF_STATUSES = frozenset({429, 503})
CHUNK_SIZE = 1024 * 1024
WATCHDOG_THREAD_NAME = "polis-prazo-total"
OPEN_THREAD_NAME = "polis-abertura"


class _Watchdog:
    """Prazo de tempo real de UM download (uma tentativa): ao vencer, desliga o socket.

    O `shutdown` acorda qualquer leitura bloqueada em outra thread (o `recv` devolve fim de
    arquivo), inclusive as que o `http.client` faz sozinho (status, cabeçalhos, tamanho do pedaço,
    trailers). Chama-se o método da classe base `socket.socket`: o `SSLSocket.shutdown` zera o
    objeto TLS enquanto a thread de leitura ainda está dentro dele. Sem prazo finito, não cria
    thread.
    """

    def __init__(self, seconds):
        self.expired = False
        self._lock = threading.Lock()
        self._sock = None
        self._timer = None
        if seconds != math.inf:
            self._timer = threading.Timer(min(seconds, threading.TIMEOUT_MAX), self.expire)
            self._timer.name = WATCHDOG_THREAD_NAME
            self._timer.daemon = True
            self._timer.start()

    def register(self, sock):
        """Chamado quando a conexão fica pronta; se o prazo já venceu, corta de uma vez."""
        with self._lock:
            self._sock = sock
            expired = self.expired
        if expired:
            self._cut(sock)

    def expire(self):
        """O prazo venceu: marca e corta o socket, se a conexão já existir."""
        with self._lock:
            self.expired = True
            sock = self._sock
        if sock is not None:
            self._cut(sock)

    @staticmethod
    def _cut(sock):
        try:
            socket.socket.shutdown(sock, socket.SHUT_RDWR)
        except OSError:
            pass  # já fechado ou desligado: o que se queria

    def stop(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer.join()


class _Handoff:
    """Entrega o resultado de uma thread de trabalho à principal, que pode desistir de esperar.

    `getaddrinfo` (DNS) é uma chamada de C bloqueante, sem timeout e sem como cancelar de fora:
    só dá para parar de esperar por ela. A principal chama `wait`; se o prazo estoura, a thread é
    marcada como abandonada e, se ela terminar depois com uma resposta, é ela quem a fecha (senão
    a conexão vazaria). A decisão "terminou a tempo" ou "foi abandonada" é tomada sob o mesmo lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._abandoned = False
        self._result = None
        self._error = None

    def run(self, function, argument):
        try:
            result = function(argument)
        except BaseException as error:  # a principal relança: um erro inesperado não some
            with self._lock:
                self._error = error
                self._done.set()
            return
        with self._lock:
            self._result = result
            abandoned = self._abandoned
            self._done.set()
        if abandoned and result[0] is not None:
            result[0].close()

    def wait(self, timeout):
        """True se a thread terminou a tempo; False se estourou (e agora está abandonada)."""
        self._done.wait(timeout)
        with self._lock:
            if self._done.is_set():
                return True
            self._abandoned = True
            return False

    def result(self):
        if self._error is not None:
            raise self._error
        return self._result


class _WatchedConnectionMixin:
    """Avisa o watchdog quando o socket (já com TLS, se houver) fica pronto."""

    def __init__(self, *args, on_connect, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_connect = on_connect

    def connect(self):
        super().connect()
        self._on_connect(self.sock)


class _WatchedHTTPConnection(_WatchedConnectionMixin, http.client.HTTPConnection):
    pass


class _WatchedHTTPSConnection(_WatchedConnectionMixin, http.client.HTTPSConnection):
    pass


class _WatchedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, on_connect):
        super().__init__()
        self._connection = functools.partial(_WatchedHTTPConnection, on_connect=on_connect)

    def http_open(self, req):
        return self.do_open(self._connection, req)


class _WatchedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, on_connect):
        # Sem `context=`: o contexto é o padrão do urllib (o de `http.client`, com ALPN http/1.1 e
        # verificação de certificado e de nome), que `https_open` original também usa.
        super().__init__()
        self._connection = functools.partial(_WatchedHTTPSConnection, on_connect=on_connect)

    def https_open(self, req):
        return self.do_open(self._connection, req, context=self._context)


class DownloadError(Exception):
    """Falha de download. A mensagem cita só host e status."""


class BlockedError(DownloadError):
    """A fonte recusou o coletor (403, 401, 451). Quem decide o que fazer é o dono."""


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    sha256: str
    size_bytes: int
    etag: str
    last_modified: str


class PoliteClient:
    def __init__(
        self,
        *,
        min_interval=3.0,
        max_attempts=4,
        backoff_base=3.0,
        backoff_cap=300.0,
        timeout=30.0,
        total_timeout=1800.0,
        max_bytes=2 * 1024**3,
        allowed_schemes=("https",),
        sleep=time.sleep,
        clock=time.monotonic,
        wall_clock=time.time,
    ):
        # `timeout` vai ao socket (finito) e `min(timeout, total_timeout)` precisa de números:
        # validar aqui mantém `_open` sem levantar. `total_timeout=inf` desliga o prazo.
        if type(timeout) not in (int, float) or not 0 < timeout < math.inf:
            raise ValueError("timeout deve ser um número positivo e finito (segundos).")
        if type(total_timeout) not in (int, float) or not total_timeout > 0:
            raise ValueError("total_timeout deve ser um número positivo (segundos).")
        self._min_interval = min_interval
        self._max_attempts = max_attempts
        self._backoff_base = backoff_base
        self._backoff_cap = backoff_cap
        self._timeout = timeout
        self._total_timeout = total_timeout
        self._max_bytes = max_bytes
        self._allowed_schemes = tuple(allowed_schemes)
        self._sleep = sleep
        self._clock = clock
        self._wall_clock = wall_clock
        self._last_request = {}
        self._blocked_hosts = set()
        self._watchdog = None
        self._opener = self._build_opener()

    def _register_socket(self, sock):
        self._watchdog.register(sock)

    def _build_opener(self):
        # Sem HTTPRedirectHandler (3xx vira erro), sem ProxyHandler, sem File/FTP.
        opener = urllib.request.OpenerDirector()
        for handler in (
            _WatchedHTTPHandler(self._register_socket),
            _WatchedHTTPSHandler(self._register_socket),
            urllib.request.HTTPDefaultErrorHandler(),
            urllib.request.HTTPErrorProcessor(),
        ):
            opener.add_handler(handler)
        return opener

    def download(self, url, destination, *, max_bytes=None):
        """Baixa `url` para `destination`.

        `max_bytes` (opcional) é o limite desta chamada; o efetivo é o menor entre ele e o teto do
        cliente, então a chamada só pode reduzir o teto, nunca alargá-lo. `None` usa o do cliente.
        """
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError("max_bytes deve ser um inteiro positivo ou None.")
        limit = self._max_bytes if max_bytes is None else min(max_bytes, self._max_bytes)
        try:
            parts = urlsplit(url)
            host = parts.hostname
        except ValueError:
            parts = host = None
        if parts is None:
            raise DownloadError("URL malformada.")
        if parts.scheme not in self._allowed_schemes:
            raise DownloadError(f"Esquema não permitido: {parts.scheme!r}.")
        if not host:
            raise DownloadError("URL sem host.")
        if host in self._blocked_hosts:
            raise BlockedError(f"{host} bloqueou o coletor; a coleta deste host está parada.")

        for attempt in range(1, self._max_attempts + 1):
            self._pause(host)
            started = self._clock()
            watchdog = self._watchdog = _Watchdog(self._total_timeout)
            try:
                response, status, retry_after, network_failed = self._open(url, watchdog)
                if response is not None:
                    return self._save(response, host, Path(destination), limit, started, watchdog)
            finally:
                watchdog.stop()
            if watchdog.expired:
                raise DownloadError(self._deadline_message(host))
            if network_failed:
                raise DownloadError(f"Falha de rede ao acessar {host}.")
            if status in BLOCKED_STATUSES:
                self._blocked_hosts.add(host)
                raise BlockedError(f"{host} respondeu {status}; a coleta deste host parou.")
            if status in BACKOFF_STATUSES and attempt < self._max_attempts:
                self._sleep(self._wait(attempt, retry_after))
                continue
            raise DownloadError(f"{host} respondeu {status} (tentativa {attempt}).")
        raise DownloadError(f"Sem tentativas disponíveis para {host}.")

    def _pause(self, host):
        last = self._last_request.get(host)
        if last is not None:
            wait = self._min_interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[host] = self._clock()

    def _open(self, url, watchdog):
        """Abre `url` numa thread e espera no máximo o prazo total (DNS, TCP, TLS e cabeçalhos).

        Estourou: o watchdog marca o prazo (e corta o socket, se já existir) e a thread é
        abandonada; `download` converte isso na mensagem do prazo.
        """
        handoff = _Handoff()
        threading.Thread(
            target=handoff.run, args=(self._open_blocking, url), name=OPEN_THREAD_NAME, daemon=True
        ).start()
        limit = None if self._total_timeout == math.inf else self._total_timeout
        if not handoff.wait(None if limit is not None else None):
            watchdog.expire()
            return None, None, None, True
        return handoff.result()

    def _open_blocking(self, url):
        """Devolve (resposta, status, Retry-After, falha de rede); nunca levanta."""
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
        response = status = retry_after = None
        network_failed = False
        try:
            response = self._opener.open(request, timeout=min(self._timeout, self._total_timeout))
        except HTTPError as error:
            status = error.code
            retry_after = error.headers.get("Retry-After")
            error.close()
        except OSError, http.client.HTTPException, ValueError:
            network_failed = True
        return response, status, retry_after, network_failed

    def _wait(self, attempt, retry_after):
        backoff = self._backoff_base * 2 ** (attempt - 1)
        requested = self._parse_retry_after(retry_after)
        wait = backoff if requested is None else max(backoff, requested)
        return min(wait, self._backoff_cap)

    def _parse_retry_after(self, value):
        if not value:
            return None
        value = value.strip()
        if value.isascii() and value.isdigit():
            return float(value)
        try:
            moment = parsedate_to_datetime(value)
        except TypeError, ValueError:
            return None
        return max(0.0, moment.timestamp() - self._wall_clock())

    def _deadline_message(self, host):
        # `.15g`: sem notação científica até 1e15 (`:g` daria "1e+06").
        return f"Download de {host} acima do prazo de {self._total_timeout:.15g} segundos."

    def _save(self, response, host, destination, limit, started, watchdog):
        declared = _parse_length(response.headers.get("Content-Length"))
        etag = response.headers.get("ETag", "")
        last_modified = response.headers.get("Last-Modified", "")
        if declared is not None and declared > limit:
            response.close()
            raise DownloadError(f"{host} anunciou arquivo acima do limite de {limit} bytes.")

        digest = hashlib.sha256()
        received = 0
        problem = None
        handle, temporary_name = tempfile.mkstemp(
            dir=destination.parent, prefix=f".{destination.name}.", suffix=".part"
        )
        temporary = Path(temporary_name)
        saved = False
        try:
            try:
                with response, os.fdopen(handle, "wb") as file:
                    while True:
                        # `read1`: no máximo uma leitura de socket por volta. `read(CHUNK_SIZE)`
                        # só volta com 1 MiB ou no fim e encadearia leituras: um host de 1 byte a
                        # cada 29 s nunca estouraria o `timeout` nem devolveria o controle aqui.
                        chunk = response.read1(CHUNK_SIZE)
                        if self._clock() - started > self._total_timeout:
                            problem = "prazo"
                            break
                        if not chunk:
                            break
                        received += len(chunk)
                        if received > limit:
                            problem = f"acima do limite de {limit} bytes"
                            break
                        digest.update(chunk)
                        file.write(chunk)
            except OSError, http.client.HTTPException:
                problem = "interrompido"
            if watchdog.expired and problem in (None, "interrompido"):
                # O watchdog desligou o socket: o fim da leitura (limpo ou com erro) é do prazo.
                # Vale também para o download que terminou no mesmo instante, como a regra do
                # relógio (a leitura final que passa do prazo falha).
                problem = "prazo"
            if problem is None and declared is not None and received != declared:
                problem = "cortado"
            if problem is None:
                temporary.replace(destination)
                saved = True
        finally:
            if not saved:
                temporary.unlink(missing_ok=True)
        if problem == "prazo":
            raise DownloadError(self._deadline_message(host))
        if problem is not None:
            raise DownloadError(f"Download de {host} {problem}.")
        return DownloadResult(
            path=destination,
            sha256=digest.hexdigest(),
            size_bytes=received,
            etag=etag,
            last_modified=last_modified,
        )


def _parse_length(value):
    if value is None:
        return None
    value = value.strip()
    return int(value) if value.isascii() and value.isdigit() else None
