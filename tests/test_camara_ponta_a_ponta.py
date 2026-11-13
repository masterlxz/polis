"""Câmara ponta a ponta: a coleta grava o bruto e a normalização o aceita (ADR 0021 e 0022).

O leitor JSON grava TODO valor como texto (`id` vira "204554"). Os testes do parser e da
normalização usavam inteiros no bruto, então as duas metades passavam sem nunca se encontrar. Aqui
o bruto vem do leitor de verdade; o cliente HTTP é falso e os dados são sintéticos.
"""

import hashlib
import json
from pathlib import Path

import pytest

from apps.legislature import normalization
from apps.legislature.models import Deputy
from apps.sources.http_client import DownloadResult
from apps.sources.ingestion import ingest
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

API = "https://dadosabertos.example.org/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=id"
PERMITIDAS = ["id", "uri", "nome", "siglaPartido", "siglaUf", "idLegislatura"]


def item(i, **extra):
    base = {
        "id": i,
        "uri": f"https://dadosabertos.example.org/api/v2/deputados/{i}",
        "nome": f"Deputado {i}",
        "siglaPartido": "XYZ",
        "siglaUf": "SP",
        "idLegislatura": 57,
        "email": "dep@example.org",
    }
    return {**base, **extra}


class FakeApi:
    def __init__(self, itens):
        self.itens = itens

    def download(self, url, destination):
        dados = json.dumps({"dados": self.itens if "pagina=1" in url else []}).encode()
        Path(destination).write_bytes(dados)
        return DownloadResult(
            path=Path(destination),
            sha256=hashlib.sha256(dados).hexdigest(),
            size_bytes=len(dados),
            etag="",
            last_modified="",
        )


@pytest.fixture
def dataset():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://dadosabertos.example.org",
        access_type=Source.AccessType.API,
        status=Source.Status.INTEGRATING,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="deputados",
        name="Deputados em exercício",
        url=API,
        format=Dataset.Format.JSON,
        allowed_columns=PERMITIDAS,
        enabled=True,
        license_basis=Dataset.LicenseBasis.OWNER_DECISION,
        license_justification="Decisão do dono de teste.",
    )


def test_o_bruto_do_leitor_guarda_o_id_como_texto(dataset):
    run = ingest(dataset, FakeApi([item(204554)]))

    assert run.state == IngestionRun.State.SUCCEEDED, "controle: a coleta aconteceu"
    valores = RawRecord.objects.get(run=run).values
    assert valores["id"] == "204554" and valores["idLegislatura"] == "57"


def test_o_que_a_coleta_grava_a_normalizacao_aceita(dataset):
    ingest(dataset, FakeApi([item(204554), item(204555, siglaPartido=None)]))

    resultado = normalization.normalize_latest(dataset)

    assert resultado is not None, "controle: havia carga para normalizar"
    assert Deputy.objects.count() == 2
    ana = Deputy.objects.get(legislature_id=57, camara_id=204554)
    assert (ana.name, ana.party_acronym, ana.state) == ("Deputado 204554", "XYZ", "SP")
    assert Deputy.objects.get(camara_id=204555).party_acronym == ""
