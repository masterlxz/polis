"""API interna do histórico de votos de um senador (ADR 0029; formato na emenda 7 do ADR 0030).

`GET /internal/v1/senadores/<codigo>/votos/?pagina=`. Dados sintéticos. O que mais importa: o item
de votação secreta sai com `participacao` e nunca com `voto` (`Votou` é participação, não posição),
e o de votação aberta sai com `voto` e nunca com `participacao`; partido e UF são os do momento do
voto; só saem campos de listas explícitas, com a atribuição da fonte. Os testes de 404, 400 e 405
pedem antes um 200 de controle: sem isso, uma rota que não existe passaria por "erro esperado".
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

SENADOR = 5500
OUTRO = 5501
COLETADO_EM = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
URL_ORIGEM = "https://example.org/dadosabertos/votacao.json"


def _url(codigo=SENADOR):
    return f"/internal/v1/senadores/{codigo}/votos/"


CHAVES_RESPOSTA = {"senador", "votos", "pagina", "total_paginas", "atribuicao"}
CHAVES_SENADOR = {"id_senado", "nome"}
CHAVES_ITEM_ABERTA = {
    "codigo",
    "data",
    "identificacao",
    "ementa",
    "resultado",
    "secreta",
    "partido",
    "uf",
    "voto",
}
CHAVES_ITEM_SECRETA = (CHAVES_ITEM_ABERTA - {"voto"}) | {"participacao"}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}


def _criar_run(started_at=COLETADO_EM):
    source, _ = Source.objects.get_or_create(
        slug="senado",
        defaults={
            "name": "Senado Federal: Dados Abertos",
            "institution": "Senado Federal",
            "official_url": "https://example.org",
            "access_type": Source.AccessType.API,
        },
    )
    dataset, _ = Dataset.objects.get_or_create(
        source=source,
        slug="votacoes",
        defaults={
            "name": "Votações do Senado",
            "url": URL_ORIGEM,
            "format": Dataset.Format.JSON_SENADO_VOTACOES,
            "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
            "license_justification": "Decisão do dono de teste.",
        },
    )
    return IngestionRun.objects.create(
        dataset=dataset, source_url=dataset.url, started_at=started_at
    )


@pytest.fixture
def run():
    return _criar_run()


def _senador(run, senate_id=SENADOR, **extra):
    from apps.legislature.models import Senator

    campos = {
        "senate_id": senate_id,
        "name": f"Senador {senate_id}",
        "party_acronym": "HOJE",
        "state": "RJ",
        "ingestion_run": run,
        **extra,
    }
    return Senator.objects.create(**campos)


def _votacao(run, codigo, **extra):
    from apps.legislature.models import SenateVoting

    campos = {
        "session_voting_code": codigo,
        "voted_on": date(2026, 11, 12),
        "type_acronym": "PL",
        "number": "1",
        "year": 2026,
        "identification": f"PL 1/2026 ({codigo})",
        "summary": "Dispõe sobre um assunto de teste.",
        "result": "A",
        "secret": False,
        "process_id": 100,
        "matter_id": 200,
        "ingestion_run": run,
        **extra,
    }
    return SenateVoting.objects.create(**campos)


def _voto(votacao, senate_id, sigla, **extra):
    from apps.legislature.models import SenateVote

    campos = {
        "voting": votacao,
        "senate_id": senate_id,
        "name": f"Nome do voto {senate_id}",
        "party_acronym": "EPOCA",
        "state": "SP",
        "vote_code": sigla,
        "ingestion_run": votacao.ingestion_run,
        **extra,
    }
    return SenateVote.objects.create(**campos)


def _ok(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def _todas_as_chaves(valor):
    if isinstance(valor, dict):
        for chave, filho in valor.items():
            yield chave
            yield from _todas_as_chaves(filho)
    elif isinstance(valor, list):
        for filho in valor:
            yield from _todas_as_chaves(filho)


@pytest.fixture
def historico(run):
    """Senador com um voto aberto e um secreto; outro senador votou nas mesmas votações."""
    _senador(run)
    _senador(run, OUTRO)
    aberta = _votacao(run, 7001, voted_on=date(2026, 11, 10))
    secreta = _votacao(
        run, 7002, voted_on=date(2026, 11, 12), secret=True, identification="MSF 9/2026"
    )
    _voto(aberta, SENADOR, "Sim")
    _voto(aberta, OUTRO, "Não")
    _voto(secreta, SENADOR, "Votou")
    _voto(secreta, OUTRO, "Votou")
    return aberta, secreta


# --- Forma ---------------------------------------------------------------------------------------


def test_resposta_so_com_as_chaves_da_lista_explicita(client, historico):
    corpo = _ok(client, _url())

    assert set(corpo) == CHAVES_RESPOSTA
    assert set(corpo["senador"]) == CHAVES_SENADOR
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO


def test_item_de_votacao_aberta_sai_com_voto_e_sem_participacao(client, historico):
    item = next(i for i in _ok(client, _url())["votos"] if i["codigo"] == 7001)

    assert set(item) == CHAVES_ITEM_ABERTA
    assert item["voto"] == "Sim"
    assert item["secreta"] is False


def test_item_de_votacao_secreta_sai_com_participacao_e_nunca_com_voto(client, historico):
    corpo = _ok(client, _url())
    item = next(i for i in corpo["votos"] if i["codigo"] == 7002)

    assert set(item) == CHAVES_ITEM_SECRETA
    assert item["participacao"] == "Votou"
    assert item["secreta"] is True
    assert "voto" not in item


def test_nenhuma_chave_participacao_nos_itens_abertos(client, historico):
    corpo = _ok(client, _url())

    abertos = [i for i in corpo["votos"] if not i["secreta"]]
    assert abertos and all("participacao" not in i for i in abertos)


def test_nada_de_id_interno_nem_execucao_nem_voto_de_outro_senador(client, historico):
    corpo = _ok(client, _url())
    internos = {"id", "voting", "voting_id", "ingestion_run", "ingestion_run_id", "vote_code"}

    assert not set(_todas_as_chaves(corpo)) & internos
    assert str(OUTRO) not in str(corpo)


def test_senador_traz_codigo_e_nome_do_perfil(client, historico):
    corpo = _ok(client, _url())

    assert corpo["senador"] == {"id_senado": SENADOR, "nome": f"Senador {SENADOR}"}


# --- Conteúdo ------------------------------------------------------------------------------------


def test_so_saem_os_votos_do_senador_pedido(client, historico):
    corpo = _ok(client, _url())

    assert sorted(i["codigo"] for i in corpo["votos"]) == [7001, 7002]
    assert [i["voto"] for i in corpo["votos"] if not i["secreta"]] == ["Sim"]
    assert [i["voto"] for i in _ok(client, _url(OUTRO))["votos"] if not i["secreta"]] == ["Não"]


def test_partido_e_uf_sao_os_do_momento_do_voto_e_nao_os_do_perfil(client, historico):
    for item in _ok(client, _url())["votos"]:
        assert (item["partido"], item["uf"]) == ("EPOCA", "SP")


def test_partido_vazio_sai_null_e_s_partido_sai_como_vem(client, run):
    _senador(run)
    primeira = _votacao(run, 1, voted_on=date(2026, 1, 2))
    segunda = _votacao(run, 2, voted_on=date(2026, 1, 1))
    _voto(primeira, SENADOR, "Sim", party_acronym="")
    _voto(segunda, SENADOR, "Sim", party_acronym="S/Partido")

    partidos = [i["partido"] for i in _ok(client, _url())["votos"]]

    assert partidos == [None, "S/Partido"]


def test_sigla_da_fonte_sai_como_veio(client, run):
    _senador(run)
    votacao = _votacao(run, 1)
    _voto(votacao, SENADOR, "P-NRV")

    assert _ok(client, _url())["votos"][0]["voto"] == "P-NRV"


def test_itens_com_os_campos_da_votacao(client, historico):
    item = next(i for i in _ok(client, _url())["votos"] if i["codigo"] == 7001)

    assert item["data"] == "2026-11-10"
    assert item["identificacao"] == "PL 1/2026 (7001)"
    assert item["ementa"] == "Dispõe sobre um assunto de teste."
    assert item["resultado"] == "A"


def test_mais_recente_primeiro_e_codigo_desempata(client, run):
    _senador(run)
    for codigo, dia in ((10, 5), (11, 5), (12, 9), (13, 1)):
        _voto(_votacao(run, codigo, voted_on=date(2026, 3, dia)), SENADOR, "Sim")

    codigos = [i["codigo"] for i in _ok(client, _url())["votos"]]

    assert codigos == [12, 11, 10, 13]


def test_senador_sem_votos_devolve_lista_vazia_e_sem_atribuicao(client, run):
    _senador(run)

    corpo = _ok(client, _url())

    assert corpo["votos"] == []
    assert corpo["atribuicao"] is None
    assert (corpo["pagina"], corpo["total_paginas"]) == (1, 0)


def test_senador_fora_da_lista_de_exercicio_ainda_tem_historico(client, run):
    _senador(run, in_office=False)
    _voto(_votacao(run, 1), SENADOR, "Sim")

    assert len(_ok(client, _url())["votos"]) == 1


def test_atribuicao_e_a_da_coleta_mais_recente_da_pagina(client, run):
    nova = _criar_run(started_at=datetime(2026, 11, 14, 9, 0, tzinfo=UTC))
    _senador(run)
    _voto(_votacao(run, 1, voted_on=date(2026, 1, 1)), SENADOR, "Sim")
    _voto(_votacao(nova, 2, voted_on=date(2025, 1, 1)), SENADOR, "Sim")

    atribuicao = _ok(client, _url())["atribuicao"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == nova.started_at


# --- Erros ---------------------------------------------------------------------------------------


def test_senador_sem_perfil_da_404_mesmo_com_votos(client, run, historico):
    _voto(_votacao(run, 9000), 9999, "Sim")  # votou, mas não está em `Senator`
    _ok(client, _url())  # controle

    resposta = client.get(_url(9999))

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "não encontrado"}


@pytest.mark.parametrize("codigo", ["abc", "1234567890", "-1", "1.5", "٣"])
def test_codigo_malformado_da_404_sem_consultar_o_banco(
    client, historico, codigo, django_assert_num_queries
):
    _ok(client, _url())  # controle

    with django_assert_num_queries(0):
        assert client.get(f"/internal/v1/senadores/{codigo}/votos/").status_code == 404


@pytest.mark.parametrize("pagina", ["0", "-1", "abc", "", "12345", "1.5", "٢"])
def test_pagina_malformada_da_400(client, historico, pagina):
    _ok(client, _url())  # controle

    resposta = client.get(_url(), {"pagina": pagina})

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "página inválida"}


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, historico, metodo):
    _ok(client, _url())  # controle

    assert getattr(client, metodo)(_url()).status_code == 405


# --- Paginação e consultas -----------------------------------------------------------------------


def test_pagina_de_50_em_50(client, run):
    _senador(run)
    for codigo in range(1, 52):  # 51 votações, uma por dia
        dia = date(2026, 1, 1) + timedelta(days=codigo)
        _voto(_votacao(run, codigo, voted_on=dia), SENADOR, "Sim")

    primeira = _ok(client, _url())
    segunda = _ok(client, f"{_url()}?pagina=2")

    assert (primeira["pagina"], primeira["total_paginas"]) == (1, 2)
    assert len(primeira["votos"]) == 50
    assert [i["codigo"] for i in segunda["votos"]] == [1]  # o mais antigo
    assert segunda["pagina"] == 2


def test_pagina_alem_da_ultima_devolve_lista_vazia(client, historico):
    corpo = _ok(client, f"{_url()}?pagina=9")

    assert corpo["votos"] == []
    assert corpo["pagina"] == 9
    assert corpo["atribuicao"] is None


def test_o_historico_custa_tres_consultas_mesmo_com_muitos_votos(
    client, run, django_assert_num_queries
):
    _senador(run)
    for codigo in range(1, 40):
        secreta = bool(codigo % 2)
        _voto(_votacao(run, codigo, secret=secreta), SENADOR, "Votou" if secreta else "Sim")
    _ok(client, _url())  # controle (e aquece o que o Django guarda em cache)

    # o senador, a contagem e a página com votação e atribuição num JOIN (sem N+1)
    with django_assert_num_queries(3):
        client.get(_url())
