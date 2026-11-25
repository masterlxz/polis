"""O teto de bytes do download por formato (ADR 0031, "limites conhecidos").

O formato `csv` (arquivos anuais da Câmara) tem teto de `plain_csv.MAX_BYTES` (100 MB) no leitor,
e a ingestão passa o mesmo valor ao `download` do cliente, para recusar antes de baixar 2 GiB. Os
demais formatos não passam limite (`None`: vale o teto do cliente). O cliente é o falso de
`test_ingestion.py`, que recusa com `DownloadError` quando recebe `max_bytes` menor que o arquivo.

Para não alocar 100 MB, os testes trocam `plain_csv.MAX_BYTES` por um valor pequeno. A ingestão lê
o valor em tempo de execução (`plain_csv.MAX_BYTES`), então a troca chega até o cliente; o leitor
não é afetado, porque o padrão do `PlainCsvReader` foi fixado na definição da classe.
"""

import pytest
from test_ingestion import FakeClient, csv_ok, dataset_csv, make_dataset, zip_ok

from apps.sources import plain_csv
from apps.sources.ingestion import ingest
from apps.sources.models import IngestionRun, RawRecord

pytestmark = pytest.mark.django_db

LINHAS_CSV = ("2641546-7;Sim;204379;X", "2641546-7;Não;160976;Y")


def test_conjunto_csv_passa_o_teto_do_leitor_ao_download():
    cliente = FakeClient(csv_ok(*LINHAS_CSV))
    run = ingest(dataset_csv(), cliente)
    assert run.state == IngestionRun.State.SUCCEEDED
    assert cliente.max_bytes_usados == [plain_csv.MAX_BYTES]


def test_conjunto_csv_recusa_download_acima_do_teto_e_nao_grava_nada(monkeypatch):
    dados = csv_ok(*LINHAS_CSV)
    monkeypatch.setattr(plain_csv, "MAX_BYTES", len(dados) - 1)
    cliente = FakeClient(dados)
    run = ingest(dataset_csv(), cliente)
    assert cliente.max_bytes_usados == [len(dados) - 1]
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.DOWNLOAD
    assert run.rows_loaded == 0
    assert RawRecord.objects.count() == 0


def test_conjunto_csv_com_arquivo_exatamente_no_teto_e_aceito(monkeypatch):
    dados = csv_ok(*LINHAS_CSV)
    monkeypatch.setattr(plain_csv, "MAX_BYTES", len(dados))
    run = ingest(dataset_csv(), FakeClient(dados))
    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.rows_loaded == len(LINHAS_CSV)


def test_conjunto_zip_csv_do_mesmo_tamanho_nao_e_recusado_nem_recebe_limite(monkeypatch):
    # Discrimina o ramo: o mesmo teto que recusaria um conjunto `csv` não alcança o `zip_csv`.
    dados = zip_ok("1;ANA", "2;BIA")
    monkeypatch.setattr(plain_csv, "MAX_BYTES", len(dados) - 1)
    cliente = FakeClient(dados)
    run = ingest(make_dataset(), cliente)
    assert cliente.max_bytes_usados == [None]
    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.rows_loaded == 2
