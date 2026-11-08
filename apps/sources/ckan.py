"""Leitura da licença declarada num pacote do CKAN (ADR 0008, decisão 2).

Usa o mesmo `PoliteClient.download` da carga (pausa, recuo, bloqueio e teto de tamanho), que
grava a resposta num arquivo; aqui só se lê esse arquivo. A resposta é dado externo: tamanho
limitado, formato conferido, e a mensagem de erro nunca cita o conteúdo.
"""

import json
from pathlib import Path

MAX_BYTES = 5 * 1024**2


class CkanError(Exception):
    """A resposta do CKAN não tem o formato esperado. A mensagem nunca cita a resposta."""


def read_license_id(client, url, workdir, *, max_bytes=MAX_BYTES):
    """Devolve o `license_id` do pacote em `url` ("" se vazio ou ausente).

    Erros de rede e de bloqueio (`DownloadError`, `BlockedError`) passam sem tratamento.
    Levanta `CkanError` se a resposta for grande demais ou não for um `package_show` válido.
    """
    destination = Path(workdir) / "ckan.json"
    client.download(url, destination)
    if destination.stat().st_size > max_bytes:
        raise CkanError("A resposta do CKAN passa do tamanho permitido.")
    try:
        payload = json.loads(destination.read_bytes())
    except ValueError:
        raise CkanError("A resposta do CKAN não é JSON.") from None
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise CkanError("O CKAN não confirmou a consulta.")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise CkanError("A resposta do CKAN não traz o pacote.")
    license_id = result.get("license_id")
    if license_id is None:
        return ""
    if not isinstance(license_id, str):
        raise CkanError("O license_id do CKAN não é texto.")
    return license_id
