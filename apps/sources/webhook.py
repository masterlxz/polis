"""Envio do alerta por webhook (Etapa 0, plano da Sessão 76): um POST de texto puro.

Texto puro (o corpo é a mensagem) porque é o que o ntfy aceita direto, sem conta e podendo ser
auto-hospedado; Slack, Discord e Telegram pedem JSON próprio e ficam para uma fatia à parte.

Regras que este módulo aplica, as mesmas do cliente de coleta (`http_client.py`):
- só os esquemas permitidos (https por padrão): `urllib` abriria `file:` e `ftp:` sozinho;
- redirecionamento (3xx) recusado: seguir um redirecionamento mandaria o texto para outro lugar;
- tempo limite curto, sem proxy do ambiente.

Segurança dos erros: a URL costuma carregar o segredo (token do Telegram, tópico do ntfy), então
nenhuma mensagem de `WebhookError` a cita, nem o host, o corpo da resposta ou o texto da exceção
original. Os erros são levantados fora de qualquer `except`, sem `__context__`.

O módulo não importa Django nem toca no banco.
"""

import http.client
import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlsplit

from .http_client import USER_AGENT

DEFAULT_TIMEOUT = 10.0


class WebhookError(Exception):
    """O envio falhou. A mensagem nunca cita a URL."""


def _build_opener():
    # Sem HTTPRedirectHandler (3xx vira erro), sem ProxyHandler, sem File/FTP.
    opener = urllib.request.OpenerDirector()
    for handler in (
        urllib.request.HTTPHandler(),
        urllib.request.HTTPSHandler(),
        urllib.request.HTTPDefaultErrorHandler(),
        urllib.request.HTTPErrorProcessor(),
    ):
        opener.add_handler(handler)
    return opener


def post_text(url, text, *, allowed_schemes=("https",), timeout=DEFAULT_TIMEOUT):
    """Manda `text` por POST para `url`. Devolve `None` em 2xx; senão levanta `WebhookError`."""
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        parts = host = None
    if parts is None:
        raise WebhookError("URL malformada.")
    if parts.scheme not in allowed_schemes:
        raise WebhookError(f"Esquema não permitido: {parts.scheme!r}.")
    if not host:
        raise WebhookError("URL sem host.")

    request = urllib.request.Request(  # noqa: S310
        url,
        data=text.encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "Title": "polis: alerta das fontes",
            "User-Agent": USER_AGENT,
        },
    )
    status = None
    network_failed = False
    try:
        with _build_opener().open(request, timeout=timeout) as response:
            status = response.status
    except HTTPError as error:
        status = error.code
        error.close()
    except OSError, http.client.HTTPException, ValueError:
        network_failed = True

    if network_failed:
        raise WebhookError("Falha de rede ao enviar o alerta.")
    if status is None or not 200 <= status < 300:
        raise WebhookError(f"O webhook respondeu {status}.")
