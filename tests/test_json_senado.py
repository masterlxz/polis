"""Coleta da lista de senadores (API do Senado, uma resposta aninhada) para a camada bruta.

ADR 0005 (allowlist, falha fechada, falha técnica nunca apaga), ADR 0008 (portão de licença) e
ADR 0028. O cliente é falso: escreve a resposta combinada no destino ou levanta o erro combinado,
sem rede. Dados sintéticos, no formato medido em `/senador/lista/atual.json` em 2026-11-12:
`ListaParlamentarEmExercicio.Parlamentares.Parlamentar[].IdentificacaoParlamentar`, com o código
do parlamentar como TEXTO.

O último teste é ponta a ponta (coleta, depois normalização) de propósito: é o que prova que o que
o leitor grava é o que o parser aceita.
"""

import hashlib
import json
from pathlib import Path

import pytest

from apps.sources import catalog
from apps.sources.http_client import BlockedError, DownloadError, DownloadResult
from apps.sources.ingestion import ingest
from apps.sources.json_list import DuplicateItemError, InvalidJsonError
from apps.sources.json_senado import fetch_senate_list
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

API = "https://legis.example.org/dadosabertos/senador/lista/atual.json"
PERMITIDAS = ["CodigoParlamentar", "NomeParlamentar", "SiglaPartidoParlamentar", "UfParlamentar"]
EMAIL = "sen.exemplo@example.org"
NOME_CIVIL = "Ana Maria do Senado da Silva"


def identificacao(codigo, **extra):
    base = {
        "CodigoParlamentar": str(codigo),
        "CodigoPublicoNaLegAtual": str(codigo + 1000),
        "NomeParlamentar": f"Senador {codigo}",
        "NomeCompletoParlamentar": NOME_CIVIL,
        "SexoParlamentar": "Feminino",
        "SiglaPartidoParlamentar": "XYZ",
        "UfParlamentar": "SP",
        "EmailParlamentar": EMAIL,
        "UrlFotoParlamentar": f"http://example.org/foto/{codigo}.jpg",
        "Telefones": {"Telefone": [{"NumeroTelefone": "30000000"}]},
    }
    return {**base, **extra}


def corpo(*identificacoes, envelope=None):
    parlamentares = [
        {"IdentificacaoParlamentar": i, "Mandato": {"Suplentes": {"Suplente": []}}}
        for i in identificacoes
    ]
    return json.dumps(
        envelope
        if envelope is not None
        else {
            "ListaParlamentarEmExercicio": {
                "Metadados": {"Versao": "x"},
                "Parlamentares": {"Parlamentar": parlamentares},
            }
        }
    ).encode()


class FakeApi:
    """Escreve o corpo combinado no destino ou levanta o erro combinado."""

    def __init__(self, dados=None, erro=None):
        self.dados = dados
        self.erro = erro
        self.calls = []

    def download(self, url, destination):
        self.calls.append(url)
        if self.erro:
            raise self.erro
        Path(destination).write_bytes(self.dados)
        return DownloadResult(
            path=Path(destination),
            sha256=hashlib.sha256(self.dados).hexdigest(),
            size_bytes=len(self.dados),
            etag="",
            last_modified="",
        )


def make_dataset(status=Source.Status.INTEGRATING, **kwargs):
    fonte = Source.objects.create(
        slug="senado",
        name="Senado Federal: Dados Abertos",
        institution="Senado Federal",
        official_url="https://legis.example.org/dadosabertos",
        access_type=Source.AccessType.API,
        status=status,
    )
    kwargs.setdefault("allowed_columns", PERMITIDAS)
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("license_basis", Dataset.LicenseBasis.OWNER_DECISION)
    kwargs.setdefault("license_justification", "Decisão do dono em 2026-11-12.")
    return Dataset.objects.create(
        source=fonte,
        slug="senadores",
        name="Senadores em exercício",
        url=API,
        format=Dataset.Format.JSON_SENADO,
        **kwargs,
    )


def valores_gravados(run):
    return [r.values for r in RawRecord.objects.filter(run=run)]


# --- carga bem-sucedida ------------------------------------------------------------------------


def test_tres_senadores_gravam_3_registros_so_com_as_colunas_da_allowlist():
    dataset = make_dataset()
    api = FakeApi(corpo(*[identificacao(i) for i in (3, 1, 2)]))

    run = ingest(dataset, api)

    assert run.state == IngestionRun.State.SUCCEEDED
    assert (run.rows_read, run.rows_loaded) == (3, 3)
    assert api.calls == [API], "uma requisição só, sem paginação"
    assert all(set(v) == set(PERMITIDAS) for v in valores_gravados(run))
    assert {v["CodigoParlamentar"] for v in valores_gravados(run)} == {"1", "2", "3"}


def test_nome_civil_email_telefone_foto_e_suplentes_nunca_chegam_ao_banco():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi(corpo(identificacao(1))))

    texto = json.dumps(valores_gravados(run), ensure_ascii=False)
    assert run.state == IngestionRun.State.SUCCEEDED, "controle: a carga aconteceu"
    assert EMAIL not in texto and NOME_CIVIL not in texto
    assert "Telefone" not in texto and "foto" not in texto and "Suplente" not in texto
    assert "NomeCompletoParlamentar" in run.dropped_columns
    assert "EmailParlamentar" in run.dropped_columns


def test_o_codigo_vira_texto_no_bruto_como_nas_outras_fontes():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi(corpo(identificacao(5895))))

    assert valores_gravados(run)[0]["CodigoParlamentar"] == "5895"


def test_mesmo_conteudo_em_outra_ordem_da_o_mesmo_sha256(tmp_path):
    a = fetch_senate_list(FakeApi(corpo(identificacao(1), identificacao(2))), API, tmp_path / "a")
    b = fetch_senate_list(FakeApi(corpo(identificacao(2), identificacao(1))), API, tmp_path / "b")

    assert a.sha256 == b.sha256
    assert a.size_bytes == b.size_bytes


def test_arquivo_igual_ao_da_ultima_carga_nao_grava_de_novo():
    dataset = make_dataset()
    api = FakeApi(corpo(identificacao(1), identificacao(2)))
    primeira = ingest(dataset, api)
    assert primeira.rows_loaded == 2, "controle"

    segunda = ingest(dataset, api)

    assert segunda.state == IngestionRun.State.SUCCEEDED
    assert segunda.rows_loaded == 0


# --- falha fechada -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dados",
    [
        b"",
        b"nao e json",
        b"[]",
        b'{"ListaParlamentarEmExercicio": null}',
        b'{"ListaParlamentarEmExercicio": {}}',
        b'{"ListaParlamentarEmExercicio": {"Parlamentares": {}}}',
        b'{"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": []}}}',
        b'{"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": {"a": 1}}}}',
        b'{"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": [1]}}}',
        b'{"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": [{}]}}}',
        b'{"DetalheParlamentar": {"Metadados": {}}}',
        b'{"ListaParlamentarEmExercicio": NaN}',
    ],
    ids=[
        "vazio",
        "nao_json",
        "lista_na_raiz",
        "envelope_nulo",
        "sem_parlamentares",
        "sem_parlamentar",
        "lista_vazia",
        "parlamentar_objeto_unico",
        "item_nao_objeto",
        "item_sem_identificacao",
        "outro_envelope_200_sem_dados",
        "constante_nan",
    ],
)
def test_resposta_fora_do_formato_para_a_carga_sem_gravar_nada(dados):
    dataset = make_dataset()

    run = ingest(dataset, FakeApi(dados))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 0


def test_lista_vazia_e_recusada_e_nao_um_arquivo_igual_de_zero_linhas(tmp_path):
    vazio = corpo(envelope={"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": []}}})

    with pytest.raises(InvalidJsonError):
        fetch_senate_list(FakeApi(vazio), API, tmp_path / "x")


def test_codigo_repetido_e_recusado(tmp_path):
    with pytest.raises(DuplicateItemError):
        fetch_senate_list(
            FakeApi(corpo(identificacao(1), identificacao(1, NomeParlamentar="Outro"))),
            API,
            tmp_path / "x",
        )


def test_campo_permitido_ausente_para_a_carga():
    dataset = make_dataset()
    sem_uf = {k: v for k, v in identificacao(1).items() if k != "UfParlamentar"}

    run = ingest(dataset, FakeApi(corpo(sem_uf)))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA


def test_valor_composto_num_campo_permitido_rejeita_a_linha_e_a_carga():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi(corpo(identificacao(1, NomeParlamentar={"a": 1}))))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.MALFORMED_ROW
    assert RawRecord.objects.count() == 0


def test_resposta_grande_demais_e_recusada(tmp_path, monkeypatch):
    from apps.sources import json_senado

    monkeypatch.setattr(json_senado, "MAX_BYTES", 100)

    with pytest.raises(InvalidJsonError):
        fetch_senate_list(
            FakeApi(corpo(*[identificacao(i) for i in range(1, 6)])), API, tmp_path / "x"
        )


def test_itens_demais_sao_recusados(tmp_path, monkeypatch):
    from apps.sources import json_senado

    monkeypatch.setattr(json_senado, "MAX_ITEMS", 2)

    with pytest.raises(InvalidJsonError):
        fetch_senate_list(
            FakeApi(corpo(*[identificacao(i) for i in range(1, 4)])), API, tmp_path / "x"
        )


def test_falha_de_rede_nao_apaga_a_carga_anterior():
    dataset = make_dataset()
    primeira = ingest(dataset, FakeApi(corpo(identificacao(1))))
    assert primeira.rows_loaded == 1, "controle"

    run = ingest(dataset, FakeApi(erro=DownloadError("falha")))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.DOWNLOAD
    assert RawRecord.objects.filter(run=primeira).count() == 1


def test_bloqueio_403_pausa_a_fonte():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi(erro=BlockedError("bloqueado")))

    assert run.error_code == IngestionRun.ErrorCode.BLOCKED
    dataset.source.refresh_from_db()
    assert dataset.source.status == Source.Status.PAUSED


def test_a_mensagem_de_erro_nunca_cita_valores(tmp_path):
    segredo = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"
    dados = corpo(identificacao(1), identificacao(1, NomeParlamentar=segredo))

    with pytest.raises(DuplicateItemError) as erro:
        fetch_senate_list(FakeApi(dados), API, tmp_path / "x")

    assert segredo not in str(erro.value)


# --- cadastro ----------------------------------------------------------------------------------


def test_o_catalogo_traz_o_conjunto_do_senado_com_a_allowlist_de_4_campos():
    definicao = next(d for d in catalog.DATASETS if d["source"] == "senado")

    assert definicao["slug"] == "senadores"
    assert definicao["format"] == "json_senado"
    assert definicao["allowed_columns"] == PERMITIDAS
    assert definicao["license_basis"] == "owner_decision"
    assert definicao["url"].endswith("/senador/lista/atual.json")
    assert definicao["schedule_interval_hours"] == 24


# --- ponta a ponta -----------------------------------------------------------------------------


def test_o_que_a_coleta_grava_a_normalizacao_aceita():
    from apps.legislature import senate_normalization
    from apps.legislature.models import Senator

    dataset = make_dataset()
    ingest(dataset, FakeApi(corpo(*[identificacao(i) for i in (5895, 6000)])))

    resultado = senate_normalization.normalize_latest(dataset)

    assert resultado is not None, "controle: havia carga para normalizar"
    assert set(Senator.objects.values_list("senate_id", flat=True)) == {5895, 6000}
    assert Senator.objects.get(senate_id=5895).name == "Senador 5895"
