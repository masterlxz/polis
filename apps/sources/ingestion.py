"""Carga de um Dataset: baixa, lê só a allowlist, grava a camada bruta e registra a execução.

Liga o cliente HTTP (`PoliteClient`), o leitor (`ZipCsvReader`), o `Dataset`, o `RawRecord` e o
`IngestionRun`. Decisões que este módulo aplica:
- ADR 0005, decisão 6 (falha fechada): qualquer problema de esquema ou linha rejeitada desfaz a
  carga inteira (transação); nada é gravado. Tolerância de linhas rejeitadas: zero.
- ADR 0005, decisão 9: falha técnica nunca apaga a carga anterior.
- ADR 0005, decisão 11: depois de uma carga bem-sucedida, só as 3 últimas que gravaram linhas
  mantêm os `RawRecord`; as execuções continuam.
- ADR 0008, decisão 5: 403, 401 e 451 pausam a `Source` (a coleta daquele host para; o dono
  reativa no admin).
- ADR 0008, decisão 2: antes do arquivo, a licença declarada no CKAN precisa ser a registrada no
  `Dataset`; diferente, vazia ou não confirmada vira `license` (falha fechada, sem pausar a fonte).
- ADR 0008, decisão 6: arquivo com o mesmo SHA-256 da última carga bem-sucedida não é relido.

A execução é criada antes (`running`) e fechada uma única vez no fim, fora da transação da carga
(o `IngestionRun` é imutável depois de concluído, e o rollback não pode levar o registro da
falha junto). A falha vira `error_code`; o texto só é guardado (`error_detail`, até 200
caracteres) nos erros de download e bloqueio, cuja mensagem o `PoliteClient` escreve citando só
host e status.

Segurança dos erros: os demais, e todo erro inesperado, não guardam texto: um erro inesperado
vira `other` e `IngestionError` sem causa nem contexto, porque a mensagem de um erro do banco
cita valores da linha (ADR 0005, decisões 7 e 8).

Atenção para quem consome:
- Duas cargas simultâneas do mesmo `Dataset` não são barradas aqui: o agendador
  (`apps/sources/scheduling.py`) reserva o conjunto antes de chamar `ingest`, mas uma coleta
  manual (`ingest_dataset`) ao mesmo tempo continua possível.
- O ZIP baixado não é guardado; só a camada filtrada.
"""

import tempfile
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from .ckan import CkanError, read_license_id
from .http_client import BlockedError, DownloadError
from .json_list import JsonListError, JsonListReader, fetch_pages
from .json_senado import fetch_senate_list
from .json_senado_votacoes import MAX_VOTES, fetch_senate_votings
from .models import IngestionRun, RawRecord, Source
from .zip_csv import DuplicateColumnError, InvalidFormatError, MissingColumnError, ZipCsvReader

KEEP_LOADS = 3
BATCH_SIZE = 1000
ERROR_DETAIL_MAX = 200


class IngestionError(Exception):
    """Erro inesperado na carga. A mensagem nunca cita dados; o detalhe não é guardado."""


class _MalformedRows(Exception):
    """Interna: o leitor rejeitou linhas; desfaz a transação da carga."""


def ingest(dataset, client, *, batch_size=BATCH_SIZE, keep_loads=KEEP_LOADS):
    """Coleta `dataset` com `client` e devolve a `IngestionRun` fechada.

    Falha esperada (bloqueio, download, esquema, linha rejeitada) volta como execução `failed`.
    Levanta `ValueError` se o portão recusar (nada é criado) e `IngestionError` num erro
    inesperado (a execução fica `failed` com `other`).
    """
    _check_gate(dataset)
    run = IngestionRun.objects.create(dataset=dataset, source_url=dataset.url)
    fields = {}
    error_code = ""
    unexpected = False
    with tempfile.TemporaryDirectory(prefix="polis-") as workdir:
        try:
            fields, error_code = _execute(
                dataset, client, run, Path(workdir) / "download.zip", batch_size, keep_loads
            )
        except Exception:
            # Qualquer falha fora do previsto: o texto do erro pode citar valores de linha.
            error_code = IngestionRun.ErrorCode.OTHER
            unexpected = True
    if error_code == IngestionRun.ErrorCode.BLOCKED:
        dataset.source.status = Source.Status.PAUSED
        dataset.source.save(update_fields=["status"])
    _close(run, fields, error_code)
    if unexpected:
        raise IngestionError(f"A carga de {dataset} falhou de forma inesperada.") from None
    return run


def _check_gate(dataset):
    dataset.refresh_from_db(fields=["enabled"])
    dataset.source.refresh_from_db(fields=["status"])
    if not dataset.enabled:
        raise ValueError(f"O conjunto {dataset} não está habilitado.")
    status = dataset.source.status
    if status == Source.Status.PAUSED:
        raise ValueError("A fonte está pausada (bloqueio ou decisão do dono); reative-a no admin.")
    if status not in (Source.Status.INTEGRATING, Source.Status.ACTIVE):
        raise ValueError("A fonte não está em integração nem ativa.")


def _execute(dataset, client, run, destination, batch_size, keep_loads):
    try:
        if _must_check_license(dataset):
            declared = read_license_id(client, dataset.license_check_url, destination.parent)
            if declared != dataset.license_id:
                return {}, IngestionRun.ErrorCode.LICENSE
        if dataset.format == dataset.Format.JSON:
            result = fetch_pages(client, dataset.url, destination)
        elif dataset.format == dataset.Format.JSON_SENADO:
            result = fetch_senate_list(client, dataset.url, destination)
        elif dataset.format == dataset.Format.JSON_SENADO_VOTACOES:
            result = fetch_senate_votings(client, dataset.url, destination)
        else:
            result = client.download(dataset.url, destination)
    except BlockedError as error:
        return _detail(error), IngestionRun.ErrorCode.BLOCKED
    except DownloadError as error:
        return _detail(error), IngestionRun.ErrorCode.DOWNLOAD
    except CkanError:
        return {}, IngestionRun.ErrorCode.LICENSE
    except JsonListError:
        return {}, IngestionRun.ErrorCode.SCHEMA
    fields = {
        "sha256_original": result.sha256,
        "size_bytes": result.size_bytes,
        "etag": result.etag,
    }
    if _same_as_last_load(dataset, result.sha256):
        return fields, ""
    return _load(dataset, run, destination, fields, batch_size, keep_loads)


def _detail(error):
    """Mensagem do cliente HTTP, a única que se guarda: ela cita só host e status."""
    return {"error_detail": str(error)[:ERROR_DETAIL_MAX]}


def _must_check_license(dataset):
    """Só licença `declared` com endereço de checagem é comparada (ADR 0008, decisão 2)."""
    return bool(dataset.license_check_url) and (
        dataset.license_basis == dataset.LicenseBasis.DECLARED
    )


def _same_as_last_load(dataset, sha256):
    last = (
        IngestionRun.objects.filter(dataset=dataset, state=IngestionRun.State.SUCCEEDED)
        .order_by("-started_at", "-pk")
        .values_list("sha256_original", flat=True)
        .first()
    )
    return last == sha256


def _load(dataset, run, path, fields, batch_size, keep_loads):
    if dataset.format == dataset.Format.JSON_SENADO_VOTACOES:
        # Um ano são ~7 mil linhas (uma por voto): o teto padrão de 10 mil é apertado.
        reader = JsonListReader(path, dataset.allowed_columns, max_items=MAX_VOTES)
    elif dataset.format in (dataset.Format.JSON, dataset.Format.JSON_SENADO):
        reader = JsonListReader(path, dataset.allowed_columns)
    else:
        reader = ZipCsvReader(path, dataset.allowed_columns)
    loaded = 0
    error_code = ""
    try:
        with transaction.atomic():
            loaded = _store(reader, run, batch_size)
            if reader.rejected_rows:
                raise _MalformedRows
            _apply_retention(dataset, run, keep_loads)
    except _MalformedRows:
        error_code = IngestionRun.ErrorCode.MALFORMED_ROW
    except MissingColumnError, DuplicateColumnError, InvalidFormatError, JsonListError:
        error_code = IngestionRun.ErrorCode.SCHEMA
    fields["rows_read"] = reader.rows_read
    fields["dropped_columns"] = sorted(reader.ignored_columns)
    fields["rows_loaded"] = 0 if error_code else loaded
    return fields, error_code


def _store(reader, run, batch_size):
    batch = []
    loaded = 0
    for item_name, values in reader.rows():
        batch.append(RawRecord(run=run, item_name=item_name, values=values))
        if len(batch) >= batch_size:
            RawRecord.objects.bulk_create(batch)
            loaded += len(batch)
            batch = []
    if batch:
        RawRecord.objects.bulk_create(batch)
        loaded += len(batch)
    return loaded


def _apply_retention(dataset, run, keep_loads):
    previous = (
        IngestionRun.objects.filter(dataset=dataset, rows_loaded__gt=0)
        .order_by("-started_at", "-pk")
        .values_list("pk", flat=True)[: keep_loads - 1]
    )
    keep = [*previous, run.pk]
    RawRecord.objects.filter(run__dataset=dataset).exclude(run_id__in=keep).delete()


def _close(run, fields, error_code):
    for name, value in fields.items():
        setattr(run, name, value)
    run.finished_at = timezone.now()
    if error_code:
        run.state = IngestionRun.State.FAILED
        run.error_code = error_code
    else:
        run.state = IngestionRun.State.SUCCEEDED
    run.save()
