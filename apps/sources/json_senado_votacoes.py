"""Coleta das votações do Senado (API `/votacao`, ADR 0029) para a camada bruta.

A resposta é uma LISTA de votações, cada uma com `votos` embutidos (81 itens medidos em
2026-11-13). Aqui ela vira o arquivo `{"dados": [...]}` ACHATADO, uma linha por voto, com os
campos escalares da votação repetidos em cada linha (como o CSV desnormalizado da Câmara). O resto
do pipeline é o mesmo da Câmara (`JsonListReader`: leitura por nome de campo, só a allowlist,
tolerância zero, ADR 0005). Ordenado por (votação, parlamentar): o mesmo conteúdo dá o mesmo
SHA-256, mesmo se a fonte trocar a ordem.

A janela é móvel: os últimos `WINDOW_DAYS` dias, calculados pelo relógio, porque o endereço do
conjunto é fixo e a API exige datas (intervalo de até 1 ano). Votação que sai da janela some do
bruto, mas não da tabela normalizada (a normalização nunca apaga).

Falha fechada: corpo que não é lista, lista vazia (360 dias sem votação não existe), votação sem
código inteiro ou sem votos, voto sem código, votação ou voto repetidos, arquivo grande ou itens
demais recusam a carga (`JsonListError`), em vez de gravar um recorte silenciosamente menor. As
mensagens de erro nunca citam valores.
"""

import hashlib
import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

from django.utils import timezone

from .http_client import DownloadResult
from .json_list import DuplicateItemError, InvalidJsonError, _refuse_constant

WINDOW_DAYS = 360
MAX_BYTES = 20 * 1024 * 1024
MAX_VOTINGS = 2_000
MAX_VOTES = 50_000
VOTING_KEY = "codigoSessaoVotacao"
SENATOR_KEY = "codigoParlamentar"
NESTED = ("votos", "informeLegislativo")


def _today():
    return timezone.localdate()


def _window_url(url):
    today = _today()
    start = today - timedelta(days=WINDOW_DAYS)
    query = urlencode({"dataInicio": start.isoformat(), "dataFim": today.isoformat()})
    return f"{url}?{query}"


def _code(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidJsonError("item sem identificador inteiro")
    return value


def _load(path):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise InvalidJsonError("arquivo grande demais")
    try:
        body = json.loads(path.read_bytes(), parse_constant=_refuse_constant)
    except ValueError, RecursionError:
        raise InvalidJsonError("JSON inválido") from None
    if not isinstance(body, list) or not body:
        raise InvalidJsonError("esperava uma lista de votações")
    if len(body) > MAX_VOTINGS:
        raise InvalidJsonError("votações demais")
    return body


def _flatten(votings):
    rows = {}
    seen = set()
    for voting in votings:
        if not isinstance(voting, dict):
            raise InvalidJsonError("votação não é objeto")
        voting_code = _code(voting.get(VOTING_KEY))
        if voting_code in seen:
            raise DuplicateItemError("votação repetida")
        seen.add(voting_code)
        votes = voting.get("votos")
        if not isinstance(votes, list) or not votes:
            raise InvalidJsonError("votação sem votos")
        header = {k: v for k, v in voting.items() if k not in NESTED}
        for vote in votes:
            if not isinstance(vote, dict):
                raise InvalidJsonError("voto não é objeto")
            key = (voting_code, _code(vote.get(SENATOR_KEY)))
            if key in rows:
                raise DuplicateItemError("voto ou votação repetidos")
            rows[key] = {**header, **vote}
            if len(rows) > MAX_VOTES:
                raise InvalidJsonError("votos demais")
    return [rows[key] for key in sorted(rows)]


def fetch_senate_votings(client, url, destination):
    """Baixa as votações da janela e grava em `destination` o arquivo achatado (`dados`)."""
    destination = Path(destination)
    raw_file = destination.with_name(destination.name + ".bruto")
    client.download(_window_url(url), raw_file)
    try:
        rows = _flatten(_load(raw_file))
    finally:
        raw_file.unlink(missing_ok=True)
    data = json.dumps(
        {"dados": rows}, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    destination.write_bytes(data)
    return DownloadResult(
        path=destination,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        etag="",
        last_modified="",
    )
