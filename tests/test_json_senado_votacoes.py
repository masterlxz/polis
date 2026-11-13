"""Coleta das votações do Senado (API `/votacao`, uma resposta com votos embutidos) para o bruto.

ADR 0005 (allowlist, falha fechada, falha técnica nunca apaga), ADR 0008 (portão de licença) e
ADR 0029. O cliente é falso: escreve a resposta combinada no destino ou levanta o erro combinado,
sem rede. Dados sintéticos, no formato medido em 2026-11-13 (Rodada 3 de `fontes/senado.md`): o
corpo é uma LISTA de votações, cada uma com `votos` (81 itens medidos), `codigoSessaoVotacao`
inteiro e único, `informeLegislativo` objeto ou nulo e totais nulos nas votações abertas.

O bruto é achatado: uma linha por voto, com os campos da votação repetidos. O último teste é
ponta a ponta (coleta, depois normalização), de propósito: prova que o que o leitor grava é o que
o parser aceita.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from apps.sources.http_client import BlockedError, DownloadError, DownloadResult
from apps.sources.ingestion import ingest
from apps.sources.json_list import DuplicateItemError, InvalidJsonError
from apps.sources.json_senado_votacoes import fetch_senate_votings
from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

API = "https://legis.example.org/dadosabertos/votacao"
HOJE = date(2026, 11, 13)
PERMITIDAS = [
    "codigoSessaoVotacao",
    "dataSessao",
    "sigla",
    "numero",
    "ano",
    "identificacao",
    "ementa",
    "resultadoVotacao",
    "votacaoSecreta",
    "totalVotosSim",
    "totalVotosNao",
    "totalVotosAbstencao",
    "idProcesso",
    "codigoMateria",
    "codigoParlamentar",
    "nomeParlamentar",
    "siglaPartidoParlamentar",
    "siglaUFParlamentar",
    "siglaVotoParlamentar",
]
SEGREDO_DA_EMENTA = "ementa-com-valor-que-nao-pode-vazar"


@pytest.fixture(autouse=True)
def hoje_fixo(monkeypatch):
    monkeypatch.setattr("apps.sources.json_senado_votacoes._today", lambda: HOJE)


def voto(codigo, sigla="Sim", **extra):
    base = {
        "codigoParlamentar": codigo,
        "nomeParlamentar": f"Senador {codigo}",
        "sexoParlamentar": "F",
        "siglaPartidoParlamentar": "XYZ",
        "siglaUFParlamentar": "SP",
        "siglaVotoParlamentar": sigla,
        "descricaoVotoParlamentar": "texto livre do voto",
    }
    return {**base, **extra}


def votacao(codigo, votos, **extra):
    base = {
        "codigoSessaoVotacao": codigo,
        "codigoSessao": 9000 + codigo,
        "dataSessao": "2026-11-12",
        "dataApresentacao": "2026-10-01",
        "sigla": "PL",
        "numero": "123",
        "ano": 2026,
        "identificacao": "PL 123/2026",
        "ementa": "Dispõe sobre algo.",
        "descricaoVotacao": "Votação do projeto",
        "resultadoVotacao": "A",
        "votacaoSecreta": "N",
        "totalVotosSim": None,
        "totalVotosNao": None,
        "totalVotosAbstencao": None,
        "idProcesso": 5000 + codigo,
        "codigoMateria": 7000 + codigo,
        "informeLegislativo": {"id": 1, "texto": "algo"},
        "votos": votos,
    }
    return {**base, **extra}


def corpo(*votacoes):
    return json.dumps(list(votacoes)).encode()


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
    kwargs.setdefault("license_justification", "Decisão do dono em 2026-11-13.")
    return Dataset.objects.create(
        source=fonte,
        slug="votacoes",
        name="Votações do Senado",
        url=API,
        format=Dataset.Format.JSON_SENADO_VOTACOES,
        **kwargs,
    )


def buscar(tmp_path, dados):
    api = FakeApi(dados)
    resultado = fetch_senate_votings(api, API, tmp_path / "votacoes.json")
    linhas = json.loads(Path(resultado.path).read_text())["dados"]
    return api, resultado, linhas


# --- janela de datas ---------------------------------------------------------------------------


def test_pede_os_ultimos_360_dias_numa_unica_requisicao(tmp_path):
    api, _, _ = buscar(tmp_path, corpo(votacao(1, [voto(10)])))
    assert api.calls == [f"{API}?dataInicio=2025-11-18&dataFim=2026-11-13"]


def test_a_janela_cabe_no_limite_de_um_ano_da_api(tmp_path):
    api, _, _ = buscar(tmp_path, corpo(votacao(1, [voto(10)])))
    parametros = api.calls[0].split("?")[1].split("&")
    inicio, fim = (date.fromisoformat(p.split("=")[1]) for p in parametros)
    assert (fim - inicio).days <= 365


# --- achatamento -------------------------------------------------------------------------------


def test_duas_votacoes_de_tres_votos_viram_seis_linhas_com_a_votacao_repetida(tmp_path):
    corpo_api = corpo(
        votacao(2, [voto(30), voto(10), voto(20)]),
        votacao(1, [voto(10), voto(20), voto(30)], ementa="Outra ementa."),
    )
    _, _, linhas = buscar(tmp_path, corpo_api)
    assert len(linhas) == 6
    assert {(r["codigoSessaoVotacao"], r["codigoParlamentar"]) for r in linhas} == {
        (v, p) for v in (1, 2) for p in (10, 20, 30)
    }
    da_primeira = [r for r in linhas if r["codigoSessaoVotacao"] == 1]
    assert {r["ementa"] for r in da_primeira} == {"Outra ementa."}
    assert all(r["identificacao"] == "PL 123/2026" for r in linhas)


def test_o_achatado_nao_carrega_estruturas_aninhadas(tmp_path):
    _, _, linhas = buscar(tmp_path, corpo(votacao(1, [voto(10)])))
    assert "votos" not in linhas[0]
    assert "informeLegislativo" not in linhas[0]


def test_ordem_e_sha256_nao_dependem_da_ordem_da_fonte(tmp_path):
    a = corpo(votacao(1, [voto(10), voto(20)]), votacao(2, [voto(20), voto(10)]))
    b = corpo(votacao(2, [voto(10), voto(20)]), votacao(1, [voto(20), voto(10)]))
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    _, resultado_a, linhas = buscar(tmp_path / "a", a)
    _, resultado_b, _ = buscar(tmp_path / "b", b)
    chaves = [(r["codigoSessaoVotacao"], r["codigoParlamentar"]) for r in linhas]
    assert chaves == sorted(chaves)
    assert resultado_a.sha256 == resultado_b.sha256


def test_votacao_secreta_mantem_os_itens_e_os_totais(tmp_path):
    secreta = votacao(
        1,
        [voto(10, "Votou"), voto(20, "Votou"), voto(30, "AP")],
        votacaoSecreta="S",
        totalVotosSim=43,
        totalVotosNao=2,
        totalVotosAbstencao=1,
    )
    _, _, linhas = buscar(tmp_path, corpo(secreta))
    assert len(linhas) == 3
    assert {r["votacaoSecreta"] for r in linhas} == {"S"}
    assert {r["totalVotosSim"] for r in linhas} == {43}
    assert {r["siglaVotoParlamentar"] for r in linhas} == {"Votou", "AP"}


# --- falha fechada -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dados",
    [
        b"isto nao e json",
        b'{"votacoes": []}',
        b"[]",
        b'["texto"]',
        corpo({"sem": "codigo", "votos": [voto(1)]}),
        corpo(votacao(1, [])),
        corpo({**votacao(1, [voto(1)]), "votos": "nao e lista"}),
        corpo(votacao(1, ["nao e objeto"])),
        corpo(votacao(1, [{"nomeParlamentar": "sem codigo"}])),
        corpo(votacao(1, [voto(7), voto(7, "Não")])),
        corpo(votacao(1, [voto(7)]), votacao(1, [voto(8)])),
        corpo({**votacao(1, [voto(1)]), "codigoSessaoVotacao": True}),
        corpo({**votacao(1, [voto(1)]), "codigoSessaoVotacao": None}),
    ],
    ids=[
        "nao-json",
        "objeto-no-lugar-da-lista",
        "lista-vazia",
        "item-nao-objeto",
        "votacao-sem-codigo",
        "votacao-sem-votos",
        "votos-nao-lista",
        "voto-nao-objeto",
        "voto-sem-codigo",
        "parlamentar-repetido-na-votacao",
        "votacao-repetida",
        "codigo-booleano",
        "codigo-nulo",
    ],
)
def test_corpo_fora_do_formato_recusa_a_carga(tmp_path, dados):
    with pytest.raises((InvalidJsonError, DuplicateItemError)):
        fetch_senate_votings(FakeApi(dados), API, tmp_path / "votacoes.json")
    assert not (tmp_path / "votacoes.json").exists()


def test_resposta_grande_demais_recusa(tmp_path):
    grande = corpo(votacao(1, [voto(1)], ementa="x" * (21 * 1024 * 1024)))
    with pytest.raises(InvalidJsonError):
        fetch_senate_votings(FakeApi(grande), API, tmp_path / "votacoes.json")


def test_a_mensagem_do_erro_nunca_cita_valores(tmp_path):
    dados = corpo(
        votacao(1, [voto(7), voto(7, "Não")], ementa=SEGREDO_DA_EMENTA, identificacao="PL 999/2026")
    )
    with pytest.raises(DuplicateItemError) as erro:
        fetch_senate_votings(FakeApi(dados), API, tmp_path / "votacoes.json")
    assert SEGREDO_DA_EMENTA not in str(erro.value)
    assert "PL 999/2026" not in str(erro.value)


@pytest.mark.parametrize("erro", [DownloadError("falhou"), BlockedError("bloqueado")])
def test_erro_de_download_passa_sem_mudanca_e_nao_deixa_arquivo(tmp_path, erro):
    with pytest.raises(type(erro)):
        fetch_senate_votings(FakeApi(erro=erro), API, tmp_path / "votacoes.json")
    assert list(tmp_path.iterdir()) == []


# --- ingestão: bruto filtrado ------------------------------------------------------------------


def test_ingestao_grava_uma_linha_por_voto_so_com_as_colunas_da_allowlist(tmp_path):
    dataset = make_dataset()
    api = FakeApi(corpo(votacao(1, [voto(10), voto(20), voto(30)])))
    run = ingest(dataset, api)
    assert run.state == IngestionRun.State.SUCCEEDED
    assert (run.rows_read, run.rows_loaded) == (3, 3)
    valores = [r.values for r in RawRecord.objects.filter(run=run)]
    assert all(set(v) == set(PERMITIDAS) for v in valores)
    texto = json.dumps(valores, ensure_ascii=False)
    assert "texto livre do voto" not in texto, "descricaoVotoParlamentar fica de fora"
    assert "Votação do projeto" not in texto, "descricaoVotacao fica de fora"
    assert '"sexoParlamentar"' not in texto


def test_o_bruto_guarda_tudo_como_texto_e_o_total_nulo_vira_vazio():
    dataset = make_dataset()
    run = ingest(dataset, FakeApi(corpo(votacao(1, [voto(10)]))))
    valores = RawRecord.objects.get(run=run).values
    assert valores["codigoSessaoVotacao"] == "1"
    assert valores["codigoParlamentar"] == "10"
    assert valores["ano"] == "2026"
    assert valores["totalVotosSim"] == ""


def test_um_ano_de_votacoes_cabe_no_teto_de_itens():
    """87 votações x 81 votos = 7.047 linhas (medido); 130 x 81 = 10.530 passa do teto padrão."""
    dataset = make_dataset()
    votacoes = [votacao(n, [voto(p) for p in range(1, 82)]) for n in range(1, 131)]
    run = ingest(dataset, FakeApi(corpo(*votacoes)))
    assert run.state == IngestionRun.State.SUCCEEDED
    assert run.rows_loaded == 10_530


def test_carga_igual_a_anterior_nao_regrava():
    dataset = make_dataset()
    api = FakeApi(corpo(votacao(1, [voto(10), voto(20)])))
    ingest(dataset, api)
    segunda = ingest(dataset, api)
    assert segunda.state == IngestionRun.State.SUCCEEDED
    assert segunda.rows_loaded == 0
    assert RawRecord.objects.count() == 2


def test_corpo_invalido_vira_execucao_falha_de_esquema_e_nao_apaga_a_carga_anterior():
    dataset = make_dataset()
    ingest(dataset, FakeApi(corpo(votacao(1, [voto(10)]))))
    ruim = ingest(dataset, FakeApi(b"[]"))
    assert ruim.state == IngestionRun.State.FAILED
    assert ruim.error_code == IngestionRun.ErrorCode.SCHEMA
    assert RawRecord.objects.count() == 1


def test_fonte_so_medida_continua_recusando_a_coleta():
    dataset = make_dataset(status=Source.Status.MEASURED)
    with pytest.raises(ValueError, match="integração"):
        ingest(dataset, FakeApi(corpo(votacao(1, [voto(10)]))))


# --- ponta a ponta -----------------------------------------------------------------------------


def test_o_que_o_leitor_grava_e_o_que_a_normalizacao_aceita():
    from apps.legislature import senate_voting_normalization as normalizacao
    from apps.legislature.models import SenateVote, SenateVoting

    dataset = make_dataset()
    corpo_api = corpo(
        votacao(1, [voto(10), voto(20, "Não")]),
        votacao(
            2,
            [voto(10, "Votou"), voto(20, "Votou")],
            votacaoSecreta="S",
            totalVotosSim=2,
            totalVotosNao=0,
            totalVotosAbstencao=0,
        ),
    )
    run = ingest(dataset, FakeApi(corpo_api))
    resultado = normalizacao.normalize(run)
    assert (resultado.rows_read, resultado.unique, resultado.created, resultado.existing) == (
        4,
        4,
        4,
        0,
    )
    assert SenateVoting.objects.count() == 2
    assert SenateVote.objects.count() == 4
    assert SenateVoting.objects.get(session_voting_code=2).secret is True
