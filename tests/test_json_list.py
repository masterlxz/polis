"""Coleta da lista de deputados da Câmara (API paginada, JSON) para a camada bruta.

ADR 0005 (allowlist, falha fechada, tolerância zero, falha técnica nunca apaga), ADR 0008
(portão de licença, série, 403 pausa a fonte). O cliente é falso: escreve a página combinada no
destino ou levanta o erro combinado, sem rede. Dados todos sintéticos, no formato medido na
`/deputados` em 2026-11-10 (9 chaves por item, valores escalares, 513 itens em 6 páginas).
"""

import hashlib
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.exceptions import ValidationError

from apps.sources import catalog, json_list
from apps.sources.http_client import BlockedError, DownloadError, DownloadResult
from apps.sources.ingestion import ingest
from apps.sources.json_list import (
    DuplicateItemError,
    InvalidJsonError,
    JsonListReader,
    TooManyPagesError,
    fetch_pages,
)
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

API = "https://dadosabertos.example.org/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=id"
PERMITIDAS = ["id", "uri", "nome", "siglaPartido", "siglaUf", "idLegislatura"]
EMAIL = "dep.exemplo@example.org"


def item(i, **extra):
    base = {
        "id": i,
        "uri": f"https://dadosabertos.example.org/api/v2/deputados/{i}",
        "nome": f"DEPUTADO {i}",
        "siglaPartido": "XYZ",
        "siglaUf": "SP",
        "idLegislatura": 57,
        "email": EMAIL,
        "urlFoto": f"https://example.org/foto/{i}.jpg",
        "uriPartido": "https://dadosabertos.example.org/api/v2/partidos/1",
    }
    return {**base, **extra}


def pagina(*itens):
    return json.dumps({"dados": list(itens), "links": []}).encode()


class FakeApi:
    """Responde por número de `pagina=` (uma página vazia além das combinadas) ou levanta erro."""

    def __init__(self, paginas, erros=None):
        self.paginas = paginas
        self.erros = erros or {}
        self.calls = []

    def download(self, url, destination):
        self.calls.append(url)
        numero = int(parse_qs(urlparse(url).query)["pagina"][0])
        if numero in self.erros:
            raise self.erros[numero]
        dados = self.paginas.get(numero, pagina())
        Path(destination).write_bytes(dados)
        return DownloadResult(
            path=Path(destination),
            sha256=hashlib.sha256(dados).hexdigest(),
            size_bytes=len(dados),
            etag="",
            last_modified="",
        )


def tres_paginas():
    return {
        1: pagina(*[item(i) for i in range(1, 101)]),
        2: pagina(*[item(i) for i in range(101, 201)]),
        3: pagina(*[item(i) for i in range(201, 214)]),
    }


def make_dataset(status=Source.Status.INTEGRATING, **kwargs):
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://dadosabertos.example.org",
        access_type=Source.AccessType.API,
        status=status,
    )
    kwargs.setdefault("allowed_columns", PERMITIDAS)
    kwargs.setdefault("enabled", True)
    kwargs.setdefault("license_basis", Dataset.LicenseBasis.OWNER_DECISION)
    kwargs.setdefault("license_justification", "Decisão do dono em 2026-11-10.")
    return Dataset.objects.create(
        source=fonte,
        slug="deputados",
        name="Deputados em exercício",
        url=API,
        format=Dataset.Format.JSON,
        **kwargs,
    )


def valores_gravados(run):
    return [r.values for r in RawRecord.objects.filter(run=run)]


# --- carga bem-sucedida ------------------------------------------------------------------------


def test_tres_paginas_gravam_213_registros_so_com_as_colunas_da_allowlist():
    dataset = make_dataset()
    api = FakeApi(tres_paginas())

    run = ingest(dataset, api)

    assert run.state == IngestionRun.State.SUCCEEDED
    assert (run.rows_read, run.rows_loaded) == (213, 213)
    assert len(api.calls) == 3, "a terceira página tem menos de 100: não pede a quarta"
    assert [parse_qs(urlparse(u).query)["pagina"] for u in api.calls] == [["1"], ["2"], ["3"]]
    assert all(set(v) == set(PERMITIDAS) for v in valores_gravados(run))
    assert {v["id"] for v in valores_gravados(run)} == {str(i) for i in range(1, 214)}
    assert run.error_code == ""
    assert run.sha256_original and run.size_bytes


def test_pagina_cheia_na_ponta_pede_a_seguinte_e_para_na_vazia():
    dataset = make_dataset()
    api = FakeApi({1: pagina(*[item(i) for i in range(1, 101)])})

    run = ingest(dataset, api)

    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.rows_loaded == 100
    assert len(api.calls) == 2


def test_valores_viram_texto_e_nulo_vira_vazio():
    dataset = make_dataset()
    api = FakeApi({1: pagina(item(7, idLegislatura=57, siglaPartido=None))})

    run = ingest(dataset, api)

    [valores] = valores_gravados(run)
    assert valores["id"] == "7" and valores["idLegislatura"] == "57"
    assert valores["siglaPartido"] == ""


# --- o que nunca entra (ADR 0005, decisões 1 e 6) -----------------------------------------------


def test_email_foto_e_uri_do_partido_sao_descartados_na_leitura():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi({1: pagina(item(1), item(2))}))

    assert run.dropped_columns == ["email", "uriPartido", "urlFoto"]
    textos = json.dumps(valores_gravados(run), ensure_ascii=False)
    assert EMAIL not in textos and "foto" not in textos.lower()
    assert all(set(v) == set(PERMITIDAS) for v in valores_gravados(run))


def test_chave_nova_fora_da_allowlist_e_ignorada_e_contada():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi({1: pagina(item(1, campoNovo="x"))}))

    assert run.state == IngestionRun.State.SUCCEEDED
    assert "campoNovo" in run.dropped_columns
    assert "campoNovo" not in json.dumps(valores_gravados(run))


def test_item_sem_campo_permitido_falha_fechada_e_nao_grava_nada():
    dataset = make_dataset()
    sem_uf = item(2)
    del sem_uf["siglaUf"]

    run = ingest(dataset, FakeApi({1: pagina(item(1), sem_uf)}))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 0


@pytest.mark.parametrize("valor", [{"a": 1}, [1, 2], True])
def test_valor_que_nao_e_escalar_rejeita_a_carga_inteira(valor):
    dataset = make_dataset()

    run = ingest(dataset, FakeApi({1: pagina(item(1), item(2, nome=valor))}))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.MALFORMED_ROW
    assert RawRecord.objects.count() == 0


def test_valor_gigante_rejeita_a_carga_inteira():
    dataset = make_dataset()

    run = ingest(dataset, FakeApi({1: pagina(item(1), item(2, nome="A" * 1_000_000))}))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.MALFORMED_ROW
    assert RawRecord.objects.count() == 0


def test_mesmo_id_em_duas_paginas_falha_fechado():
    dataset = make_dataset()
    paginas = {
        1: pagina(*[item(i) for i in range(1, 101)]),
        2: pagina(item(100), item(101)),
    }

    run = ingest(dataset, FakeApi(paginas))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 0


@pytest.mark.parametrize(
    "corpo",
    [
        b"",
        b"nao e json",
        b'{"dados": [',
        b"[]",
        b'{"outra": []}',
        b'{"dados": "x"}',
        b'{"dados": [1, 2]}',
        b'{"dados": [[1]]}',
    ],
)
def test_resposta_que_nao_e_a_lista_esperada_falha_fechada(corpo):
    dataset = make_dataset()
    controle = ingest(dataset, FakeApi({1: pagina(item(1))}))
    assert controle.state == IngestionRun.State.SUCCEEDED, "controle: o formato válido funciona"
    RawRecord.objects.all().delete()

    run = ingest(dataset, FakeApi({1: corpo}))

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 0


# --- falha técnica e etiqueta (ADR 0005 decisão 9; ADR 0008 decisão 5) ---------------------------


def test_erro_de_download_numa_pagina_do_meio_nao_grava_e_nao_apaga_a_carga_anterior():
    dataset = make_dataset()
    primeira = ingest(dataset, FakeApi({1: pagina(item(1), item(2))}))
    assert primeira.state == IngestionRun.State.SUCCEEDED

    paginas = {1: pagina(*[item(i) for i in range(1, 101)])}
    segunda = ingest(dataset, FakeApi(paginas, erros={2: DownloadError("500")}))

    assert segunda.state == IngestionRun.State.FAILED
    assert segunda.error_code == IngestionRun.ErrorCode.DOWNLOAD
    assert RawRecord.objects.filter(run=segunda).count() == 0
    assert RawRecord.objects.filter(run=primeira).count() == 2


def test_bloqueio_em_qualquer_pagina_pausa_a_fonte_e_para():
    dataset = make_dataset()
    api = FakeApi({1: pagina(*[item(i) for i in range(1, 101)])}, erros={2: BlockedError("403")})

    run = ingest(dataset, api)

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.BLOCKED
    assert len(api.calls) == 2, "parou na página bloqueada"
    dataset.source.refresh_from_db()
    assert dataset.source.status == Source.Status.PAUSED


def test_mais_paginas_que_o_teto_falha_fechado(monkeypatch):
    monkeypatch.setattr(json_list, "MAX_PAGES", 2)
    dataset = make_dataset()
    paginas = {
        n: pagina(*[item(i) for i in range((n - 1) * 100 + 1, n * 100 + 1)]) for n in (1, 2, 3)
    }
    api = FakeApi(paginas)

    run = ingest(dataset, api)

    assert run.state == IngestionRun.State.FAILED
    assert run.error_code == IngestionRun.ErrorCode.SCHEMA
    assert len(api.calls) <= 3, "não segue pedindo páginas sem fim"
    assert RawRecord.objects.count() == 0


def test_teto_de_paginas_no_fetch_levanta_erro_proprio(tmp_path):
    paginas = {n: pagina(item(2 * n - 1), item(2 * n)) for n in range(1, 10)}

    with pytest.raises(TooManyPagesError):
        fetch_pages(FakeApi(paginas), API, tmp_path / "juntas.json", page_size=2, max_pages=3)


# --- mesma carga, portão e cadastro --------------------------------------------------------------


def test_mesmo_conteudo_da_ultima_carga_nao_e_relido():
    dataset = make_dataset()
    primeira = ingest(dataset, FakeApi(tres_paginas()))

    segunda = ingest(dataset, FakeApi(tres_paginas()))

    assert segunda.state == IngestionRun.State.SUCCEEDED
    assert (segunda.rows_read, segunda.rows_loaded) == (0, 0)
    assert segunda.sha256_original == primeira.sha256_original
    assert RawRecord.objects.count() == 213


def test_a_ordem_das_paginas_nao_muda_o_sha256(tmp_path):
    a = {1: pagina(item(1), item(2)), 2: pagina(item(3))}
    b = {1: pagina(item(2), item(1)), 2: pagina(item(3))}

    um = fetch_pages(FakeApi(a), API, tmp_path / "a.json", page_size=2)
    dois = fetch_pages(FakeApi(b), API, tmp_path / "b.json", page_size=2)

    assert um.sha256 == dois.sha256


def test_conjunto_nao_habilitado_nao_e_coletado():
    dataset = make_dataset(enabled=False)
    api = FakeApi(tres_paginas())

    with pytest.raises(ValueError, match="não está habilitado"):
        ingest(dataset, api)

    assert api.calls == []
    assert IngestionRun.objects.count() == 0


def test_fonte_pausada_nao_recebe_requisicao():
    dataset = make_dataset(status=Source.Status.PAUSED)
    api = FakeApi(tres_paginas())

    with pytest.raises(ValueError, match="pausada"):
        ingest(dataset, api)

    assert api.calls == []


def test_decisao_do_dono_sem_justificativa_nao_habilita():
    dataset = make_dataset(enabled=False, license_justification="")
    dataset.enabled = True

    with pytest.raises(ValidationError):
        dataset.full_clean()


def test_o_catalogo_cadastra_deputados_so_com_a_allowlist_e_sem_habilitar():
    [entrada] = [d for d in catalog.DATASETS if d["source"] == "camara"]

    assert entrada["slug"] == "deputados"
    assert entrada["format"] == "json"
    assert entrada["allowed_columns"] == PERMITIDAS
    assert not {"email", "urlFoto", "cpf", "nomeCivil", "dataNascimento"} & set(
        entrada["allowed_columns"]
    )
    assert entrada["license_basis"] == "owner_decision"
    assert "itens=100" in entrada["url"]
    assert not entrada.get("enabled"), "quem habilita é o dono, no admin"


# --- leitor sozinho -------------------------------------------------------------------------------


def test_leitor_devolve_so_a_allowlist_e_conta_o_que_ignorou(tmp_path):
    caminho = tmp_path / "juntas.json"
    caminho.write_bytes(pagina(item(1), item(2)))
    leitor = JsonListReader(caminho, PERMITIDAS)

    linhas = list(leitor.rows())

    assert len(linhas) == 2 and leitor.rows_read == 2 and leitor.rejected_rows == 0
    assert all(set(valores) == set(PERMITIDAS) for _, valores in linhas)
    assert leitor.ignored_columns == {"email", "urlFoto", "uriPartido"}


def test_leitor_recusa_allowlist_vazia_ou_em_texto(tmp_path):
    caminho = tmp_path / "juntas.json"
    caminho.write_bytes(pagina(item(1)))

    with pytest.raises(ValueError):
        JsonListReader(caminho, [])
    with pytest.raises(ValueError):
        JsonListReader(caminho, "id")


def test_leitor_nao_aceita_json_fora_do_formato(tmp_path):
    caminho = tmp_path / "juntas.json"
    caminho.write_bytes(b'{"dados": "x"}')

    with pytest.raises(InvalidJsonError):
        list(JsonListReader(caminho, PERMITIDAS).rows())


def test_fetch_barra_id_repetido_com_erro_proprio(tmp_path):
    paginas = {1: pagina(item(1), item(2)), 2: pagina(item(2))}

    with pytest.raises(DuplicateItemError):
        fetch_pages(FakeApi(paginas), API, tmp_path / "juntas.json", page_size=2)
