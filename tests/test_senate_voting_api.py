"""API interna das votações do Senado (ADR 0029; formato no ADR 0030).

`GET /internal/v1/senado/votacoes/` (lista paginada) e `GET /internal/v1/senado/votacoes/<codigo>/`
(detalhe com os votos). Dados sintéticos. O que mais importa: na votação secreta a lista sai como
`participacao`, nunca como `votos` (`Votou` é participação, não posição); a contagem por sigla é
calculada dos votos e fica separada dos totais da fonte; só saem campos de listas explícitas, com a
atribuição da fonte. Os testes de 404, 400 e 405 pedem antes um 200 de controle: sem isso, uma rota
que não existe passaria por "erro esperado".
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LISTA = "/internal/v1/senado/votacoes/"
ABERTA = 7001
SECRETA = 7002
COLETADO_EM = datetime(2026, 11, 13, 9, 0, tzinfo=UTC)
URL_ORIGEM = "https://example.org/dadosabertos/votacao.json"

CHAVES_LISTA = {"votacoes", "pagina", "total_paginas", "atribuicao"}
CHAVES_ITEM_DA_LISTA = {"codigo", "data", "identificacao", "ementa", "resultado", "secreta"}
CHAVES_DETALHE_ABERTA = {"votacao", "contagem_por_sigla", "votos", "atribuicao"}
CHAVES_DETALHE_SECRETA = {"votacao", "contagem_por_sigla", "participacao", "atribuicao"}
CHAVES_VOTACAO = {
    "codigo",
    "data",
    "sigla",
    "numero",
    "ano",
    "identificacao",
    "ementa",
    "resultado",
    "secreta",
    "id_processo",
    "codigo_materia",
    "totais_da_fonte",
}
CHAVES_TOTAIS = {"sim", "nao", "abstencao"}
CHAVES_VOTO = {"id_senado", "nome", "partido", "uf", "sigla", "tem_perfil"}
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


def _voto(votacao, senate_id, nome, sigla, **extra):
    from apps.legislature.models import SenateVote

    campos = {
        "voting": votacao,
        "senate_id": senate_id,
        "name": nome,
        "party_acronym": "XYZ",
        "state": "SP",
        "vote_code": sigla,
        "ingestion_run": votacao.ingestion_run,
        **extra,
    }
    return SenateVote.objects.create(**campos)


@pytest.fixture
def aberta(run):
    votacao = _votacao(run, ABERTA)
    _voto(votacao, 3, "Carla", "Não")
    _voto(votacao, 1, "Ana", "Sim")
    _voto(votacao, 4, "Davi", "AP")
    _voto(votacao, 2, "Bruno", "Sim")
    return votacao


@pytest.fixture
def secreta(run):
    votacao = _votacao(
        run,
        SECRETA,
        secret=True,
        total_yes=43,
        total_no=2,
        total_abstention=1,
        identification="MSF 9/2026",
    )
    _voto(votacao, 1, "Ana", "Votou")
    _voto(votacao, 2, "Bruno", "Votou")
    _voto(votacao, 3, "Carla", "Votou")
    _voto(votacao, 4, "Davi", "AP")
    return votacao


def _senador(run, senate_id, **extra):
    from apps.legislature.models import Senator

    campos = {
        "senate_id": senate_id,
        "name": f"Senador {senate_id}",
        "party_acronym": "XYZ",
        "state": "SP",
        "ingestion_run": run,
        **extra,
    }
    return Senator.objects.create(**campos)


def _ok(client, url):
    resposta = client.get(url)
    assert resposta.status_code == 200, f"controle: esperava 200 em {url}"
    return resposta.json()


def _detalhe(client, codigo):
    return _ok(client, f"{LISTA}{codigo}/")


def _todas_as_chaves(valor):
    if isinstance(valor, dict):
        for chave, filho in valor.items():
            yield chave
            yield from _todas_as_chaves(filho)
    elif isinstance(valor, list):
        for filho in valor:
            yield from _todas_as_chaves(filho)


# --- Detalhe -------------------------------------------------------------------------------------


def test_aberta_sai_com_votos_e_sem_participacao(client, aberta):
    corpo = _detalhe(client, ABERTA)

    assert set(corpo) == CHAVES_DETALHE_ABERTA


def test_secreta_sai_com_participacao_e_nunca_com_votos(client, secreta):
    corpo = _detalhe(client, SECRETA)

    assert set(corpo) == CHAVES_DETALHE_SECRETA
    assert "votos" not in set(_todas_as_chaves(corpo))
    assert "voto" not in set(_todas_as_chaves(corpo))


def test_so_saem_as_chaves_das_listas_explicitas(client, aberta, secreta):
    for codigo, lista in ((ABERTA, "votos"), (SECRETA, "participacao")):
        corpo = _detalhe(client, codigo)

        assert set(corpo["votacao"]) == CHAVES_VOTACAO
        assert set(corpo["votacao"]["totais_da_fonte"]) == CHAVES_TOTAIS
        assert all(set(item) == CHAVES_VOTO for item in corpo[lista])
        assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO


def test_votacao_aberta_com_os_campos_da_fonte(client, aberta):
    assert _detalhe(client, ABERTA)["votacao"] == {
        "codigo": ABERTA,
        "data": "2026-11-12",
        "sigla": "PL",
        "numero": "1",
        "ano": 2026,
        "identificacao": f"PL 1/2026 ({ABERTA})",
        "ementa": "Dispõe sobre um assunto de teste.",
        "resultado": "A",
        "secreta": False,
        "id_processo": 100,
        "codigo_materia": 200,
        "totais_da_fonte": {"sim": None, "nao": None, "abstencao": None},
    }


def test_secreta_traz_os_totais_da_fonte_como_vieram(client, secreta):
    votacao = _detalhe(client, SECRETA)["votacao"]

    assert votacao["secreta"] is True
    assert votacao["totais_da_fonte"] == {"sim": 43, "nao": 2, "abstencao": 1}


def test_contagem_por_sigla_vem_dos_votos_na_aberta(client, aberta):
    assert _detalhe(client, ABERTA)["contagem_por_sigla"] == {"Sim": 2, "Não": 1, "AP": 1}


def test_contagem_da_secreta_vem_dos_itens_e_nao_dos_totais_da_fonte(client, secreta):
    # Totais da fonte: 43, 2 e 1. A contagem é do que o polis tem: 3 "Votou" e 1 "AP".
    assert _detalhe(client, SECRETA)["contagem_por_sigla"] == {"Votou": 3, "AP": 1}


def test_votos_saem_ordenados_por_nome(client, aberta):
    votos = _detalhe(client, ABERTA)["votos"]

    assert [v["nome"] for v in votos] == ["Ana", "Bruno", "Carla", "Davi"]
    assert votos[0] == {"id_senado": 1, "nome": "Ana", "partido": "XYZ", "uf": "SP", "sigla": "Sim"}


def test_participacao_na_secreta_traz_a_sigla_da_fonte(client, secreta):
    participacao = _detalhe(client, SECRETA)["participacao"]

    assert [(p["nome"], p["sigla"]) for p in participacao] == [
        ("Ana", "Votou"),
        ("Bruno", "Votou"),
        ("Carla", "Votou"),
        ("Davi", "AP"),
    ]


def test_partido_vazio_sai_null_e_s_partido_sai_como_vem(client, run):
    votacao = _votacao(run, ABERTA)
    _voto(votacao, 1, "Ana", "Sim", party_acronym="")
    _voto(votacao, 2, "Bruno", "Sim", party_acronym="S/Partido")

    votos = _detalhe(client, ABERTA)["votos"]

    assert [v["partido"] for v in votos] == [None, "S/Partido"]


def test_nada_de_id_interno_nem_execucao_no_detalhe(client, aberta):
    corpo = _detalhe(client, ABERTA)
    # `atribuicao.licenca.id` é o id da licença (contrato de todas as APIs, fixado em outro teste),
    # não id interno; por isso a busca é fora da atribuição.
    chaves = set(_todas_as_chaves({k: v for k, v in corpo.items() if k != "atribuicao"}))
    texto = client.get(f"{LISTA}{ABERTA}/").content.decode()

    assert not chaves & {"id", "pk", "voting", "voting_id", "ingestion_run"}
    assert f'"id": {aberta.pk}' not in texto


def test_atribuicao_do_detalhe_traz_fonte_conjunto_data_origem_e_licenca_nula(client, aberta):
    atribuicao = _detalhe(client, ABERTA)["atribuicao"]

    assert atribuicao["fonte"] == "Senado Federal: Dados Abertos"
    assert atribuicao["conjunto"] == "Votações do Senado"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM
    assert atribuicao["url_origem"] == URL_ORIGEM
    assert atribuicao["licenca"] == {"id": None, "url": None}


@pytest.mark.parametrize("codigo", ["999999", "1"])
def test_votacao_inexistente_da_404(client, aberta, codigo):
    _detalhe(client, ABERTA)  # controle

    assert client.get(f"{LISTA}{codigo}/").status_code == 404


@pytest.mark.parametrize(
    "codigo", ["abc", "-1", "0x1", "1234567890", "70-01", "7001-", "7_001", "7001/1"]
)
def test_codigo_malformado_da_404_sem_consultar_o_banco(
    client, aberta, codigo, django_assert_num_queries
):
    _detalhe(client, ABERTA)  # controle

    with django_assert_num_queries(0):
        resposta = client.get(f"{LISTA}{codigo}/")

    assert resposta.status_code == 404


def test_o_detalhe_custa_tres_consultas_mesmo_com_muitos_votos(
    client, run, django_assert_num_queries
):
    votacao = _votacao(run, ABERTA)
    for codigo in range(1, 82):
        _voto(votacao, codigo, f"Parlamentar {codigo:02d}", "Sim")
        if codigo % 2:
            _senador(run, codigo)
    _detalhe(client, ABERTA)  # controle (e aquece o que o Django guarda em cache)

    # votação com a atribuição, votos, e os códigos que têm perfil (uma consulta só, sem N+1)
    with django_assert_num_queries(3):
        client.get(f"{LISTA}{ABERTA}/")


# --- Link para o perfil do senador (`tem_perfil`) ------------------------------------------------


def _tem_perfil_por_codigo(corpo):
    lista = corpo["participacao"] if "participacao" in corpo else corpo["votos"]
    return {item["id_senado"]: item["tem_perfil"] for item in lista}


def test_tem_perfil_so_para_quem_esta_em_senator(client, run, aberta):
    _senador(run, 1)
    _senador(run, 3)

    assert _tem_perfil_por_codigo(_detalhe(client, ABERTA)) == {
        1: True,
        2: False,
        3: True,
        4: False,
    }


def test_tem_perfil_tambem_na_votacao_secreta(client, run, secreta):
    _senador(run, 2)

    assert _tem_perfil_por_codigo(_detalhe(client, SECRETA)) == {
        1: False,
        2: True,
        3: False,
        4: False,
    }


def test_senador_fora_da_lista_de_exercicio_ainda_tem_perfil(client, run, aberta):
    _senador(run, 1, in_office=False, left_list_at=COLETADO_EM)

    assert _tem_perfil_por_codigo(_detalhe(client, ABERTA))[1] is True


def test_sem_nenhum_senator_ninguem_tem_perfil(client, aberta):
    assert not any(_tem_perfil_por_codigo(_detalhe(client, ABERTA)).values())


# --- Lista ---------------------------------------------------------------------------------------


def test_lista_mais_recente_primeiro_e_codigo_desempata(client, run):
    _votacao(run, 10, voted_on=date(2026, 1, 5))
    _votacao(run, 11, voted_on=date(2026, 3, 1))
    _votacao(run, 12, voted_on=date(2026, 3, 1))
    _votacao(run, 9, voted_on=date(2025, 12, 1))

    corpo = _ok(client, LISTA)

    assert [v["codigo"] for v in corpo["votacoes"]] == [12, 11, 10, 9]


def test_lista_so_com_as_chaves_explicitas(client, aberta, secreta):
    corpo = _ok(client, LISTA)

    assert set(corpo) == CHAVES_LISTA
    assert all(set(item) == CHAVES_ITEM_DA_LISTA for item in corpo["votacoes"])
    assert set(corpo["atribuicao"]) == CHAVES_ATRIBUICAO


def test_item_da_lista_traz_a_marca_de_secreta(client, aberta, secreta):
    itens = {v["codigo"]: v for v in _ok(client, LISTA)["votacoes"]}

    assert itens[ABERTA] == {
        "codigo": ABERTA,
        "data": "2026-11-12",
        "identificacao": f"PL 1/2026 ({ABERTA})",
        "ementa": "Dispõe sobre um assunto de teste.",
        "resultado": "A",
        "secreta": False,
    }
    assert itens[SECRETA]["secreta"] is True


def test_lista_pagina_de_50_em_50(client, run):
    for codigo in range(1, 52):  # 51 votações, uma por dia
        _votacao(run, codigo, voted_on=date(2026, 1, 1) + timedelta(days=codigo))

    primeira = _ok(client, LISTA)
    segunda = _ok(client, f"{LISTA}?pagina=2")

    assert (primeira["pagina"], primeira["total_paginas"]) == (1, 2)
    assert len(primeira["votacoes"]) == 50
    assert [v["codigo"] for v in segunda["votacoes"]] == [1]  # a mais antiga
    assert segunda["pagina"] == 2


def test_pagina_alem_da_ultima_devolve_lista_vazia(client, aberta):
    corpo = _ok(client, f"{LISTA}?pagina=9")

    assert corpo["votacoes"] == []
    assert (corpo["pagina"], corpo["total_paginas"]) == (9, 1)


def test_sem_nenhuma_votacao_lista_vazia_e_sem_atribuicao(client, run):
    corpo = _ok(client, LISTA)

    assert corpo == {"votacoes": [], "pagina": 1, "total_paginas": 0, "atribuicao": None}


@pytest.mark.parametrize("pagina", ["0", "-1", "abc", "1.5", "12345", "", " 2"])
def test_pagina_malformada_da_400(client, aberta, pagina):
    _ok(client, LISTA)  # controle

    resposta = client.get(LISTA, {"pagina": pagina})

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "página inválida"}


def test_atribuicao_da_lista_e_a_da_coleta_mais_recente_da_pagina(client, run):
    nova = _criar_run(started_at=datetime(2026, 11, 14, 9, 0, tzinfo=UTC))
    _votacao(run, 1, voted_on=date(2026, 1, 1))
    _votacao(nova, 2, voted_on=date(2025, 1, 1))  # mais antiga, mas vista pela coleta mais nova

    atribuicao = _ok(client, LISTA)["atribuicao"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == nova.started_at


def test_a_lista_custa_duas_consultas(client, run, django_assert_num_queries):
    for codigo in range(1, 30):
        _votacao(run, codigo)
    _ok(client, LISTA)  # controle

    with django_assert_num_queries(2):
        client.get(LISTA)


# --- As duas rotas -------------------------------------------------------------------------------


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, aberta, metodo):
    for url in (LISTA, f"{LISTA}{ABERTA}/"):
        _ok(client, url)  # controle

        assert getattr(client, metodo)(url).status_code == 405
