"""Testes da carga de um Dataset (ADR 0005, decisões 1, 5, 6, 9 e 11; ADR 0008, decisão 5).

O cliente é falso: escreve um ZIP pequeno no destino ou levanta o erro combinado, sem rede.
"""

import hashlib
import io
import zipfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command

from apps.sources.http_client import BlockedError, DownloadError, DownloadResult
from apps.sources.ingestion import IngestionError, ingest
from apps.sources.management.commands import ingest_dataset
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

CABECALHO = "SQ_CANDIDATO;NM_URNA_CANDIDATO"


def make_zip(items):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in items.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def zip_ok(*linhas, nome="cand_AC.csv"):
    return make_zip({nome: CABECALHO + "\n" + "".join(f"{linha}\n" for linha in linhas)})


class FakeClient:
    def __init__(self, *arquivos, error=None):
        self.arquivos = list(arquivos)
        self.error = error
        self.calls = []
        self.destinos = []

    def download(self, url, destination):
        self.calls.append(url)
        self.destinos.append(Path(destination))
        if self.error is not None:
            raise self.error
        dados = self.arquivos.pop(0) if len(self.arquivos) > 1 else self.arquivos[0]
        Path(destination).write_bytes(dados)
        return DownloadResult(
            path=Path(destination),
            sha256=hashlib.sha256(dados).hexdigest(),
            size_bytes=len(dados),
            etag='"abc"',
            last_modified="",
        )


def make_dataset(status=Source.Status.INTEGRATING, **kwargs):
    fonte = Source.objects.create(
        slug="tse",
        name="TSE",
        institution="Tribunal Superior Eleitoral",
        official_url="https://dadosabertos.tse.jus.br",
        access_type=Source.AccessType.DOWNLOAD,
        status=status,
    )
    kwargs.setdefault("allowed_columns", ["SQ_CANDIDATO", "NM_URNA_CANDIDATO"])
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("license_basis", Dataset.LicenseBasis.DECLARED)
    kwargs.setdefault("license_id", "cc-by")
    return Dataset.objects.create(
        source=fonte,
        slug="consulta-cand",
        name="Consulta de candidatos",
        url="https://cdn.example.org/consulta_cand_2026.zip",
        format=Dataset.Format.ZIP_CSV,
        **kwargs,
    )


# --- Carga bem-sucedida ---


def test_carga_grava_as_linhas_e_fecha_a_execucao_com_sucesso():
    dataset = make_dataset()
    dados = make_zip(
        {
            "cand_AC.csv": f"{CABECALHO}\n1;ANA\n2;BIA\n",
            "cand_SP.csv": f"{CABECALHO}\n3;CAIO\n",
        }
    )
    run = ingest(dataset, FakeClient(dados))
    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.error_code == ""
    assert (run.rows_read, run.rows_loaded) == (3, 3)
    assert run.sha256_original == hashlib.sha256(dados).hexdigest()
    assert run.size_bytes == len(dados)
    assert run.etag == '"abc"'
    assert run.source_url == dataset.url
    assert run.finished_at is not None
    gravados = {
        (r.item_name, r.values["SQ_CANDIDATO"], r.values["NM_URNA_CANDIDATO"], len(r.values))
        for r in RawRecord.objects.filter(run=run)
    }
    assert gravados == {
        ("cand_AC.csv", "1", "ANA", 2),
        ("cand_AC.csv", "2", "BIA", 2),
        ("cand_SP.csv", "3", "CAIO", 2),
    }


def test_carga_em_lotes_pequenos_grava_todas_as_linhas():
    dataset = make_dataset()
    dados = zip_ok("1;A", "2;B", "3;C", "4;D", "5;E")
    run = ingest(dataset, FakeClient(dados), batch_size=2)
    assert run.rows_loaded == 5
    assert RawRecord.objects.filter(run=run).count() == 5


def test_coluna_fora_da_allowlist_nunca_chega_ao_banco():
    dataset = make_dataset()
    dados = make_zip(
        {"cand_AC.csv": f"{CABECALHO};NR_CPF_CANDIDATO\n1;ANA;12345678909\n"},
    )
    run = ingest(dataset, FakeClient(dados))
    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.dropped_columns == ["NR_CPF_CANDIDATO"]
    texto = repr(list(RawRecord.objects.values_list("values", flat=True)))
    assert "12345678909" not in texto
    assert "NR_CPF_CANDIDATO" not in texto


def test_o_arquivo_baixado_nao_fica_no_disco():
    dataset = make_dataset()
    cliente = FakeClient(zip_ok("1;ANA"))
    ingest(dataset, cliente)
    assert not cliente.destinos[0].exists()
    assert not cliente.destinos[0].parent.exists()


# --- Falha fechada: nada é gravado (ADR 0005, decisão 6) ---


@pytest.mark.parametrize(
    "conteudo",
    [
        "SQ_CANDIDATO\n1\n",
        "SQ_CANDIDATO;SQ_CANDIDATO;NM_URNA_CANDIDATO\n1;1;ANA\n",
    ],
    ids=["coluna_permitida_ausente", "coluna_permitida_duplicada"],
)
def test_esquema_diferente_falha_com_schema_e_nao_grava_nada(conteudo):
    dataset = make_dataset()
    cliente = FakeClient(make_zip({"cand_AC.csv": conteudo}))
    run = ingest(dataset, cliente)
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert run.rows_loaded == 0
    assert RawRecord.objects.count() == 0
    assert not cliente.destinos[0].parent.exists()


def test_arquivo_que_nao_e_zip_falha_com_schema():
    run = ingest(make_dataset(), FakeClient(b"isto nao e um zip"))
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 0


def test_uma_linha_rejeitada_falha_a_carga_inteira_com_malformed_row():
    dataset = make_dataset()
    dados = make_zip({"cand_AC.csv": f"{CABECALHO}\n1;ANA\n2;BIA;sobra\n3;CAIO\n"})
    run = ingest(dataset, FakeClient(dados))
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.MALFORMED_ROW
    assert run.rows_loaded == 0
    assert RawRecord.objects.count() == 0


def test_falha_de_carga_nao_apaga_a_carga_anterior():
    dataset = make_dataset()
    boa = ingest(dataset, FakeClient(zip_ok("1;ANA", "2;BIA")))
    ruim = ingest(dataset, FakeClient(make_zip({"cand_AC.csv": "SQ_CANDIDATO\n1\n"})))
    assert ruim.state == IngestionRun.State.FAILED
    assert RawRecord.objects.filter(run=boa).count() == 2


def test_erro_inesperado_vira_other_e_nao_vaza_dado_da_linha(monkeypatch):
    dataset = make_dataset()

    def explode(*args, **kwargs):
        raise RuntimeError("falha na linha com CPF 123.456.789-09")

    monkeypatch.setattr(RawRecord.objects, "bulk_create", explode)
    with pytest.raises(IngestionError) as erro:
        ingest(dataset, FakeClient(zip_ok("1;ANA")))
    assert "123.456.789-09" not in str(erro.value)
    assert erro.value.__cause__ is None
    assert erro.value.__context__ is None
    run = IngestionRun.objects.get()
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.OTHER
    assert RawRecord.objects.count() == 0


# --- Falhas de rede e bloqueio (ADR 0008, decisão 5) ---


def test_falha_de_download_registra_download_e_mantem_a_fonte_ativa():
    dataset = make_dataset()
    run = ingest(dataset, FakeClient(error=DownloadError("falha")))
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.DOWNLOAD
    assert run.finished_at is not None
    dataset.source.refresh_from_db()
    assert dataset.source.status == Source.Status.INTEGRATING


def test_bloqueio_registra_blocked_e_pausa_a_fonte():
    dataset = make_dataset()
    run = ingest(dataset, FakeClient(error=BlockedError("403")))
    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.BLOCKED
    dataset.source.refresh_from_db()
    assert dataset.source.status == Source.Status.PAUSED


def test_depois_do_bloqueio_a_fonte_pausada_nao_recebe_nova_requisicao():
    dataset = make_dataset()
    ingest(dataset, FakeClient(error=BlockedError("403")))
    cliente = FakeClient(zip_ok("1;ANA"))
    dataset.source.refresh_from_db()
    with pytest.raises(ValueError, match="pausada"):
        ingest(dataset, cliente)
    assert cliente.calls == []
    assert IngestionRun.objects.count() == 1


# --- Portão antes de qualquer rede ---


def test_conjunto_nao_habilitado_nao_e_coletado():
    dataset = make_dataset(enabled=False)
    cliente = FakeClient(zip_ok("1;ANA"))
    with pytest.raises(ValueError, match="habilitado"):
        ingest(dataset, cliente)
    assert cliente.calls == []
    assert IngestionRun.objects.count() == 0


@pytest.mark.parametrize("status", [Source.Status.MEASURED, Source.Status.PAUSED])
def test_fonte_fora_de_integracao_ou_ativa_nao_e_coletada(status):
    dataset = make_dataset(status=status)
    cliente = FakeClient(zip_ok("1;ANA"))
    with pytest.raises(ValueError, match="fonte"):
        ingest(dataset, cliente)
    assert cliente.calls == []
    assert IngestionRun.objects.count() == 0


@pytest.mark.parametrize("status", [Source.Status.INTEGRATING, Source.Status.ACTIVE])
def test_fonte_em_integracao_ou_ativa_e_coletada(status):
    dataset = make_dataset(status=status)
    run = ingest(dataset, FakeClient(zip_ok("1;ANA")))
    assert run.state == IngestionRun.State.SUCCEEDED


# --- Arquivo igual ao anterior e retenção de 3 cargas (decisões 6 e 11) ---


def test_arquivo_igual_ao_da_ultima_carga_nao_e_relido():
    dataset = make_dataset()
    dados = zip_ok("1;ANA", "2;BIA")
    primeira = ingest(dataset, FakeClient(dados))
    segunda = ingest(dataset, FakeClient(dados))
    assert segunda.state == IngestionRun.State.SUCCEEDED
    assert (segunda.rows_read, segunda.rows_loaded) == (0, 0)
    assert segunda.sha256_original == primeira.sha256_original
    assert RawRecord.objects.count() == 2
    assert RawRecord.objects.filter(run=segunda).count() == 0


def test_arquivo_diferente_gera_nova_carga_e_mantem_a_anterior():
    dataset = make_dataset()
    primeira = ingest(dataset, FakeClient(zip_ok("1;ANA")))
    segunda = ingest(dataset, FakeClient(zip_ok("1;ANA", "2;BIA")))
    assert RawRecord.objects.filter(run=primeira).count() == 1
    assert RawRecord.objects.filter(run=segunda).count() == 2


def test_so_as_3_ultimas_cargas_ficam_na_camada_bruta():
    dataset = make_dataset()
    runs = [ingest(dataset, FakeClient(zip_ok(f"{i};PESSOA{i}"))) for i in range(1, 5)]
    assert IngestionRun.objects.count() == 4
    com_linhas = [RawRecord.objects.filter(run=run).count() for run in runs]
    assert com_linhas == [0, 1, 1, 1]


def test_execucao_sem_linhas_nao_conta_na_retencao():
    dataset = make_dataset()
    a, b, c = (zip_ok(f"{i};P{i}") for i in (1, 2, 3))
    run_a = ingest(dataset, FakeClient(a))
    run_b = ingest(dataset, FakeClient(b))
    run_c = ingest(dataset, FakeClient(c))
    repetida = ingest(dataset, FakeClient(c))
    assert RawRecord.objects.filter(run=repetida).count() == 0
    for run in (run_a, run_b, run_c):
        assert RawRecord.objects.filter(run=run).count() == 1


# --- Comando ---


@pytest.fixture
def cliente_falso(monkeypatch):
    cliente = FakeClient(zip_ok("1;ANA", "2;BIA"))
    monkeypatch.setattr(ingest_dataset, "PoliteClient", lambda *args, **kwargs: cliente)
    return cliente


def test_comando_carrega_o_conjunto_e_resume_so_com_contagens(cliente_falso):
    make_dataset()
    saida = StringIO()
    call_command("ingest_dataset", "tse/consulta-cand", stdout=saida)
    texto = saida.getvalue()
    assert "succeeded" in texto
    assert "2" in texto
    assert "ANA" not in texto
    assert RawRecord.objects.count() == 2


def test_comando_com_conjunto_inexistente_e_erro_claro(cliente_falso):
    with pytest.raises(CommandError, match="não encontrado"):
        call_command("ingest_dataset", "tse/nao-existe")
    assert cliente_falso.calls == []


def test_comando_com_argumento_sem_barra_e_erro_claro(cliente_falso):
    with pytest.raises(CommandError, match="fonte/conjunto"):
        call_command("ingest_dataset", "tse")


def test_comando_repassa_a_recusa_do_portao_como_erro_de_comando(cliente_falso):
    make_dataset(enabled=False)
    with pytest.raises(CommandError, match="habilitado"):
        call_command("ingest_dataset", "tse/consulta-cand")
    assert cliente_falso.calls == []
