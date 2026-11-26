"""API interna do histórico de votos de um deputado (ADR 0031 e 0032).

`GET /internal/v1/deputados/<legislatura>-<id>/votos/?pagina=`. Dados sintéticos. O que mais
importa: só saem os votos do par (legislatura, id da Câmara) pedido, nunca os de outro deputado nem
os de outra legislatura com o mesmo id; `voto` vazio sai `null` (é "sem posição", nunca string
vazia nem chave ausente); `partido` é o do momento do voto, não o do perfil; são duas atribuições
(ADR 0008, decisão 3), a do conjunto de VOTOS e a do de VOTAÇÕES (outro `Dataset`), cada uma pela
coleta mais recente entre os itens da página; só saem campos de listas explícitas. Os testes de
404, 400 e 405 pedem antes um 200 de controle: sem isso, uma rota que não existe passaria por
"erro esperado".

Valores de referência lidos do código: 50 por página (`VOTINGS_PER_PAGE` em `apps/legislature/
views.py`), ordem `-voting__voted_on`, `-voting__camara_voting_id` (a mesma da lista da Câmara; o
id da votação é ordenado como TEXTO, não como número) e o índice de `CamaraVote` em
`apps/legislature/models.py`.
"""

from datetime import UTC, date, datetime, timedelta

import pytest
from django.db import connection

from apps.legislature.models import CamaraVote, CamaraVoting, Deputy
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

LEGISLATURA = 57
DEPUTADO = 204554
OUTRO = 204555
COLETADO_EM = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
COLETADO_EM_DOS_VOTOS = datetime(2026, 11, 24, 15, 30, tzinfo=UTC)
URL_ORIGEM = "https://example.org/arquivos/votacoes/csv/votacoes-2026.csv"
URL_ORIGEM_DOS_VOTOS = "https://example.org/arquivos/votacoesVotos/csv/votacoesVotos-2026.csv"


def _url(legislatura=LEGISLATURA, camara_id=DEPUTADO):
    return f"/internal/v1/deputados/{legislatura}-{camara_id}/votos/"


CHAVES_RESPOSTA = {
    "deputado",
    "votos",
    "pagina",
    "total_paginas",
    "atribuicao_das_votacoes",
    "atribuicao_dos_votos",
}
CHAVES_DEPUTADO = {"legislatura", "id_camara", "nome"}
CHAVES_ITEM = {
    "id",
    "data",
    "orgao",
    "descricao",
    "aprovacao",
    "id_proposicao",
    "partido",
    "voto",
}
CHAVES_ATRIBUICAO = {"fonte", "conjunto", "coletado_em", "url_origem", "licenca"}


def _criar_run(
    started_at=COLETADO_EM,
    slug="votacoes-2026",
    nome="Votações da Câmara em 2026",
    url=URL_ORIGEM,
):
    source, _ = Source.objects.get_or_create(
        slug="camara",
        defaults={
            "name": "Câmara dos Deputados: Dados Abertos",
            "institution": "Câmara dos Deputados",
            "official_url": "https://example.org",
            "access_type": Source.AccessType.FILE,
        },
    )
    dataset, _ = Dataset.objects.get_or_create(
        source=source,
        slug=slug,
        defaults={
            "name": nome,
            "url": url,
            "format": Dataset.Format.CSV,
            "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
            "license_justification": "Decisão do dono de teste.",
        },
    )
    return IngestionRun.objects.create(
        dataset=dataset, source_url=dataset.url, started_at=started_at
    )


def _criar_run_dos_votos(started_at=COLETADO_EM_DOS_VOTOS):
    """Execução do conjunto de votos (`camara/votos-2026`), outro `Dataset` que o das votações."""
    return _criar_run(
        started_at,
        slug="votos-2026",
        nome="Votos da Câmara em 2026",
        url=URL_ORIGEM_DOS_VOTOS,
    )


@pytest.fixture
def run():
    return _criar_run()


@pytest.fixture
def run_dos_votos():
    return _criar_run_dos_votos()


def _deputado(run, camara_id=DEPUTADO, legislatura=LEGISLATURA, **extra):
    campos = {
        "legislature_id": legislatura,
        "camara_id": camara_id,
        "name": f"Deputado {legislatura}-{camara_id}",
        "party_acronym": "HOJE",
        "state": "SP",
        "ingestion_run": run,
        **extra,
    }
    return Deputy.objects.create(**campos)


def _votacao(run, codigo, **extra):
    campos = {
        "camara_voting_id": codigo,
        "voted_on": date(2026, 3, 10),
        "organ_acronym": "PLEN",
        "approval": "1",
        "total_yes": 300,
        "total_no": 150,
        "total_other": 2,
        "description": "Aprovada a Emenda nº 1.",
        "proposition_id": 2651254,
        "ingestion_run": run,
        **extra,
    }
    return CamaraVoting.objects.create(**campos)


def _voto(votacao, camara_id, texto, legislatura=LEGISLATURA, **extra):
    campos = {
        "voting": votacao,
        "camara_id": camara_id,
        "legislature_id": legislatura,
        "party_acronym": "EPOCA",
        "vote": texto,
        "ingestion_run": votacao.ingestion_run,
        **extra,
    }
    return CamaraVote.objects.create(**campos)


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


def _todos_os_valores(valor):
    """Cada valor escalar do JSON, em qualquer profundidade (as chaves não entram)."""
    if isinstance(valor, dict):
        for filho in valor.values():
            yield from _todos_os_valores(filho)
    elif isinstance(valor, list):
        for filho in valor:
            yield from _todos_os_valores(filho)
    else:
        yield valor


@pytest.fixture
def historico(run, run_dos_votos):
    """Dois deputados da mesma legislatura que votaram nas mesmas duas votações."""
    _deputado(run, DEPUTADO, name="Ana Exemplo")
    _deputado(run, OUTRO, name="Beto Exemplo")
    primeira = _votacao(run, "2641546-7", voted_on=date(2026, 3, 10))
    segunda = _votacao(
        run,
        "2641546-8",
        voted_on=date(2026, 3, 11),
        organ_acronym="CCJC",
        approval="",
        description="Rejeitado o Requerimento nº 7.",
        proposition_id=2651999,
    )
    _voto(primeira, DEPUTADO, "Sim", ingestion_run=run_dos_votos)
    _voto(primeira, OUTRO, "Não", ingestion_run=run_dos_votos)
    _voto(segunda, DEPUTADO, "", ingestion_run=run_dos_votos)
    _voto(segunda, OUTRO, "Sim", ingestion_run=run_dos_votos)
    return primeira, segunda


# --- Forma ---------------------------------------------------------------------------------------


def test_resposta_so_com_as_chaves_da_lista_explicita(client, historico):
    corpo = _ok(client, _url())

    assert set(corpo) == CHAVES_RESPOSTA
    assert set(corpo["deputado"]) == CHAVES_DEPUTADO
    assert all(set(item) == CHAVES_ITEM for item in corpo["votos"])
    assert set(corpo["atribuicao_das_votacoes"]) == CHAVES_ATRIBUICAO
    assert set(corpo["atribuicao_dos_votos"]) == CHAVES_ATRIBUICAO


def test_deputado_traz_legislatura_id_e_nome_do_perfil(client, historico):
    corpo = _ok(client, _url())

    assert corpo["deputado"] == {
        "legislatura": LEGISLATURA,
        "id_camara": DEPUTADO,
        "nome": "Ana Exemplo",
    }


def test_item_com_os_campos_da_votacao_e_o_voto(client, historico):
    corpo = _ok(client, _url())

    assert corpo["votos"][1] == {
        "id": "2641546-7",
        "data": "2026-03-10",
        "orgao": "PLEN",
        "descricao": "Aprovada a Emenda nº 1.",
        "aprovacao": "1",
        "id_proposicao": 2651254,
        "partido": "EPOCA",
        "voto": "Sim",
    }


def test_nada_de_id_interno_totais_nem_dado_de_outro_deputado(client, historico):
    corpo = _ok(client, _url())
    # `id` fica de fora: é a chave da licença dentro da atribuição e o id da votação nos itens.
    internos = {
        "pk",
        "voting",
        "voting_id",
        "ingestion_run",
        "ingestion_run_id",
        "uri",
        "foto",
        "uf",
        "totais_da_fonte",
        "tem_perfil",
    }

    assert not set(_todas_as_chaves(corpo)) & internos
    assert "Beto Exemplo" not in str(corpo)
    # Por valor inteiro, não por substring de `str(corpo)`: um id curto casaria com datas e outros
    # ids. Os itens não carregam o id do deputado, então a varredura é no corpo todo, em número e
    # em texto.
    assert corpo["deputado"]["id_camara"] == DEPUTADO
    valores = list(_todos_os_valores(corpo))
    assert OUTRO not in valores
    assert str(OUTRO) not in valores


# --- Conteúdo ------------------------------------------------------------------------------------


def test_so_saem_os_votos_do_deputado_pedido(client, historico):
    ana = _ok(client, _url(camara_id=DEPUTADO))["votos"]
    beto = _ok(client, _url(camara_id=OUTRO))["votos"]

    assert [(i["id"], i["voto"]) for i in ana] == [("2641546-8", None), ("2641546-7", "Sim")]
    assert [(i["id"], i["voto"]) for i in beto] == [("2641546-8", "Sim"), ("2641546-7", "Não")]


def test_o_nome_de_um_deputado_nao_vaza_na_resposta_de_outro(client, historico):
    resposta_de_ana = client.get(_url(camara_id=DEPUTADO))
    resposta_de_beto = client.get(_url(camara_id=OUTRO))

    assert resposta_de_ana.status_code == resposta_de_beto.status_code == 200
    assert "Ana Exemplo" in resposta_de_ana.content.decode()
    assert "Beto Exemplo" not in resposta_de_ana.content.decode()
    assert "Beto Exemplo" in resposta_de_beto.content.decode()
    assert "Ana Exemplo" not in resposta_de_beto.content.decode()


def test_mesmo_id_em_outra_legislatura_e_outro_deputado(client, run):
    _deputado(run, DEPUTADO, legislatura=57, name="Ana da 57")
    _deputado(run, DEPUTADO, legislatura=56, name="Ana da 56")
    votacao = _votacao(run, "10-1")
    outra = _votacao(run, "10-2", voted_on=date(2026, 3, 11))
    _voto(votacao, DEPUTADO, "Sim", legislatura=57)
    _voto(outra, DEPUTADO, "Não", legislatura=56)

    da_57 = _ok(client, _url(57, DEPUTADO))
    da_56 = _ok(client, _url(56, DEPUTADO))

    assert [(i["id"], i["voto"]) for i in da_57["votos"]] == [("10-1", "Sim")]
    assert [(i["id"], i["voto"]) for i in da_56["votos"]] == [("10-2", "Não")]
    assert (da_57["deputado"]["nome"], da_56["deputado"]["nome"]) == ("Ana da 57", "Ana da 56")


def test_voto_vazio_sai_null_nunca_string_vazia_nem_chave_ausente(client, historico):
    resposta = client.get(_url())
    votos = resposta.json()["votos"]

    assert [v["voto"] for v in votos] == [None, "Sim"]
    assert all("voto" in v for v in votos)
    assert '"voto": ""' not in resposta.content.decode()


def test_aprovacao_vazia_sai_null_e_zero_sai_como_vem(client, run):
    _deputado(run)
    _voto(_votacao(run, "10-1", approval="", voted_on=date(2026, 3, 2)), DEPUTADO, "Sim")
    _voto(
        _votacao(run, "10-2", approval="0", proposition_id=0, voted_on=date(2026, 3, 1)),
        DEPUTADO,
        "Sim",
    )

    votos = _ok(client, _url())["votos"]

    assert [(v["aprovacao"], v["id_proposicao"]) for v in votos] == [(None, 2651254), ("0", 0)]


def test_partido_e_o_do_momento_do_voto_e_nao_o_do_perfil(client, historico):
    for item in _ok(client, _url())["votos"]:
        assert item["partido"] == "EPOCA"
    assert Deputy.objects.get(camara_id=DEPUTADO).party_acronym == "HOJE"


def test_partido_vazio_sai_null_e_s_partido_sai_como_vem(client, run):
    _deputado(run)
    primeira = _votacao(run, "1-1", voted_on=date(2026, 1, 2))
    segunda = _votacao(run, "1-2", voted_on=date(2026, 1, 1))
    _voto(primeira, DEPUTADO, "Sim", party_acronym="")
    _voto(segunda, DEPUTADO, "Sim", party_acronym="S/Partido")

    partidos = [i["partido"] for i in _ok(client, _url())["votos"]]

    assert partidos == [None, "S/Partido"]


def test_voto_da_fonte_sai_como_veio(client, run):
    _deputado(run)
    _voto(_votacao(run, "1-1"), DEPUTADO, "Obstrução")

    assert _ok(client, _url())["votos"][0]["voto"] == "Obstrução"


def test_mais_recente_primeiro_e_o_id_da_votacao_desempata_como_texto(client, run):
    _deputado(run)
    # No dia 5 há três votações: como TEXTO, `2641546-9` > `2641546-7` > `2641546-10` (o "1" vem
    # antes do "7"); como número, a ordem seria outra.
    for codigo, dia in (
        ("2641546-7", 5),
        ("2641546-10", 5),
        ("2641546-9", 5),
        ("2641546-1", 9),
        ("2641546-2", 1),
    ):
        _voto(_votacao(run, codigo, voted_on=date(2026, 3, dia)), DEPUTADO, "Sim")

    ids = [i["id"] for i in _ok(client, _url())["votos"]]

    assert ids == ["2641546-1", "2641546-9", "2641546-7", "2641546-10", "2641546-2"]


def test_deputado_sem_votos_devolve_lista_vazia_e_sem_atribuicao(client, run):
    _deputado(run)

    corpo = _ok(client, _url())

    assert corpo["votos"] == []
    assert corpo["atribuicao_das_votacoes"] is None
    assert corpo["atribuicao_dos_votos"] is None
    assert (corpo["pagina"], corpo["total_paginas"]) == (1, 0)


def test_deputado_fora_da_lista_de_exercicio_ainda_tem_historico(client, run):
    _deputado(run, in_office=False)
    _voto(_votacao(run, "1-1"), DEPUTADO, "Sim")

    assert len(_ok(client, _url())["votos"]) == 1


# --- Atribuição ----------------------------------------------------------------------------------


def test_atribuicao_dos_votos_e_a_do_conjunto_de_votos(client, historico):
    atribuicao = _ok(client, _url())["atribuicao_dos_votos"]

    assert atribuicao["fonte"] == "Câmara dos Deputados: Dados Abertos"
    assert atribuicao["conjunto"] == "Votos da Câmara em 2026"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM_DOS_VOTOS
    assert atribuicao["url_origem"] == URL_ORIGEM_DOS_VOTOS
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_atribuicao_das_votacoes_e_a_do_conjunto_de_votacoes(client, historico):
    # Data, órgão, descrição e aprovação de cada item vêm de `votacoes-2026`: a citação é dele.
    atribuicao = _ok(client, _url())["atribuicao_das_votacoes"]

    assert atribuicao["fonte"] == "Câmara dos Deputados: Dados Abertos"
    assert atribuicao["conjunto"] == "Votações da Câmara em 2026"
    assert datetime.fromisoformat(atribuicao["coletado_em"]) == COLETADO_EM
    assert atribuicao["url_origem"] == URL_ORIGEM
    assert atribuicao["licenca"] == {"id": None, "url": None}


def test_as_duas_atribuicoes_sao_de_conjuntos_diferentes(client, historico):
    corpo = _ok(client, _url())

    assert corpo["atribuicao_das_votacoes"] != corpo["atribuicao_dos_votos"]
    assert "atribuicao" not in corpo, "a chave antiga, ambígua, não pode ficar ao lado das novas"


def test_atribuicao_e_a_da_coleta_de_votos_mais_recente_da_pagina(client, run):
    antiga = _criar_run_dos_votos(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    nova = _criar_run_dos_votos(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    _deputado(run)
    _voto(_votacao(run, "1-1", voted_on=date(2026, 1, 1)), DEPUTADO, "Sim", ingestion_run=antiga)
    _voto(_votacao(run, "1-2", voted_on=date(2025, 1, 1)), DEPUTADO, "Sim", ingestion_run=nova)

    atribuicao = _ok(client, _url())["atribuicao_dos_votos"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == nova.started_at


def test_atribuicao_das_votacoes_e_a_da_coleta_de_votacoes_mais_recente_da_pagina(client, run):
    antiga = _criar_run(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    nova = _criar_run(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    dos_votos = _criar_run_dos_votos()
    _deputado(run)
    velha = _votacao(antiga, "1-1", voted_on=date(2026, 1, 1))
    recente = _votacao(nova, "1-2", voted_on=date(2025, 1, 1))
    _voto(velha, DEPUTADO, "Sim", ingestion_run=dos_votos)
    _voto(recente, DEPUTADO, "Sim", ingestion_run=dos_votos)

    atribuicao = _ok(client, _url())["atribuicao_das_votacoes"]

    assert datetime.fromisoformat(atribuicao["coletado_em"]) == nova.started_at


def test_atribuicao_so_considera_os_itens_da_propria_pagina(client, run):
    antiga = _criar_run_dos_votos(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    nova = _criar_run_dos_votos(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    _deputado(run)
    # 51 votações, uma por dia; a mais antiga (número 1) é a única da página 2
    for numero in range(1, 52):
        dia = date(2026, 1, 1) + timedelta(days=numero)
        coleta = nova if numero == 1 else antiga
        _voto(_votacao(run, f"1-{numero}", voted_on=dia), DEPUTADO, "Sim", ingestion_run=coleta)

    primeira = _ok(client, _url())["atribuicao_dos_votos"]
    segunda = _ok(client, f"{_url()}?pagina=2")["atribuicao_dos_votos"]

    assert datetime.fromisoformat(primeira["coletado_em"]) == antiga.started_at
    assert datetime.fromisoformat(segunda["coletado_em"]) == nova.started_at


def test_atribuicao_das_votacoes_so_considera_os_itens_da_propria_pagina(client, run):
    antiga = _criar_run(datetime(2026, 11, 20, 9, 0, tzinfo=UTC))
    nova = _criar_run(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    dos_votos = _criar_run_dos_votos()
    _deputado(run)
    for numero in range(1, 52):
        dia = date(2026, 1, 1) + timedelta(days=numero)
        coleta = nova if numero == 1 else antiga
        votacao = _votacao(coleta, f"1-{numero}", voted_on=dia)
        _voto(votacao, DEPUTADO, "Sim", ingestion_run=dos_votos)

    primeira = _ok(client, _url())["atribuicao_das_votacoes"]
    segunda = _ok(client, f"{_url()}?pagina=2")["atribuicao_das_votacoes"]

    assert datetime.fromisoformat(primeira["coletado_em"]) == antiga.started_at
    assert datetime.fromisoformat(segunda["coletado_em"]) == nova.started_at


# --- Erros ---------------------------------------------------------------------------------------


def test_deputado_sem_perfil_da_404_mesmo_com_votos(client, run, historico):
    # votou, mas não há `Deputy` para o par 58-999999
    _voto(_votacao(run, "9-9"), 999999, "Sim", legislatura=58)
    _ok(client, _url())  # controle

    resposta = client.get(_url(58, 999999))

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "não encontrado"}


def test_perfil_so_em_outra_legislatura_nao_basta(client, run, historico):
    # Há `Deputy` 57-DEPUTADO e votos dele; o par 58-DEPUTADO não tem perfil, nem que tenha voto.
    _voto(_votacao(run, "9-9"), DEPUTADO, "Sim", legislatura=58)
    _ok(client, _url())  # controle

    assert client.get(_url(58, DEPUTADO)).status_code == 404


@pytest.mark.parametrize(
    "legislatura, camara_id",
    [
        ("057", DEPUTADO),  # zero à esquerda: o int() leria 57 (outra URL para o mesmo deputado)
        (LEGISLATURA, f"0{DEPUTADO}"),
        ("0", DEPUTADO),
        (LEGISLATURA, "0"),
        ("1234567890", DEPUTADO),  # 10 dígitos: não cabe no int32 do parser
        (LEGISLATURA, "1234567890"),
        ("-1", DEPUTADO),
        (LEGISLATURA, "1.5"),
        ("abc", DEPUTADO),
        (LEGISLATURA, "٣"),  # dígito de outra escrita, que o \d do Python casaria
        # não casam com a fixture: o 404 vem da rota, não da ausência do registro
        ("0999999", "0999999"),
    ],
)
def test_id_fora_do_padrao_da_404_sem_consultar_o_banco(
    client, historico, legislatura, camara_id, django_assert_num_queries
):
    _ok(client, _url())  # controle

    with django_assert_num_queries(0):
        assert client.get(_url(legislatura, camara_id)).status_code == 404


@pytest.mark.parametrize(
    "pagina", ["0", "-1", "abc", "", "12345", "1.5", "٢", "00", "01", "0001", "09", "007"]
)
def test_pagina_malformada_da_400(client, historico, pagina):
    _ok(client, _url())  # controle

    resposta = client.get(_url(), {"pagina": pagina})

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "página inválida"}


@pytest.mark.parametrize("pagina", ["abc", "0"])
def test_pagina_malformada_de_deputado_inexistente_da_400_e_nao_404(client, historico, pagina):
    """Fixa a ordem "página inválida (400) antes de procurar o deputado (404)".

    Essa ordem é HERDADA de `senator_votes`; não foi decisão do dono, e mudá-la (procurar o
    `Deputy` antes de validar a página) é decisão aberta: se for tomada, este teste muda junto.
    Hoje a ordem está em `deputy_votes`: o `_PAGE_PATTERN.fullmatch` vem antes do
    `Deputy.objects.filter`. O par 58-999 não tem `Deputy`; o controle mostra que, sem `pagina`,
    ele dá 404, então o 400 abaixo só pode vir da validação da página.
    """
    _ok(client, _url())  # controle: a rota existe para um deputado que existe
    # controle: o par não tem perfil, e o 404 vem da view (corpo dela), não da rota
    sem_perfil = client.get(_url(58, 999))
    assert sem_perfil.status_code == 404
    assert sem_perfil.json() == {"erro": "não encontrado"}

    resposta = client.get(_url(58, 999), {"pagina": pagina})

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "página inválida"}


@pytest.mark.parametrize(
    "legislatura, camara_id", [(999999999, DEPUTADO), (LEGISLATURA, 999999999)]
)
def test_id_de_9_digitos_e_valido_e_chega_ao_banco(client, run, legislatura, camara_id):
    # 9 dígitos é o maior que a rota aceita (`{0,8}` depois do primeiro): cabe no int32 do parser.
    _deputado(run, camara_id, legislatura=legislatura, name="Deputado de 9 dígitos")
    _voto(_votacao(run, "5-1"), camara_id, "Sim", legislatura=legislatura)

    corpo = _ok(client, _url(legislatura, camara_id))

    assert corpo["deputado"] == {
        "legislatura": legislatura,
        "id_camara": camara_id,
        "nome": "Deputado de 9 dígitos",
    }
    assert [(i["id"], i["voto"]) for i in corpo["votos"]] == [("5-1", "Sim")]


@pytest.mark.parametrize("pagina", ["1", "2", "9999"])
def test_pagina_na_forma_canonica_segue_valida(client, historico, pagina):
    corpo = _ok(client, f"{_url()}?pagina={pagina}")

    assert corpo["pagina"] == int(pagina)


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_so_aceita_leitura(client, historico, metodo):
    _ok(client, _url())  # controle

    assert getattr(client, metodo)(_url()).status_code == 405


# --- Paginação e consultas -----------------------------------------------------------------------


def test_pagina_de_50_em_50(client, run):
    _deputado(run)
    for numero in range(1, 52):  # 51 votações, uma por dia
        dia = date(2026, 1, 1) + timedelta(days=numero)
        _voto(_votacao(run, f"1-{numero}", voted_on=dia), DEPUTADO, "Sim")

    primeira = _ok(client, _url())
    segunda = _ok(client, f"{_url()}?pagina=2")

    assert (primeira["pagina"], primeira["total_paginas"]) == (1, 2)
    assert len(primeira["votos"]) == 50
    assert primeira["votos"][0]["id"] == "1-51"  # o mais recente
    assert [i["id"] for i in segunda["votos"]] == ["1-1"]  # o mais antigo
    assert (segunda["pagina"], segunda["total_paginas"]) == (2, 2)


def _votar_em(run, quantidade):
    """`quantidade` votações, uma por dia, com o voto do `DEPUTADO` em cada uma."""
    for numero in range(1, quantidade + 1):
        dia = date(2025, 1, 1) + timedelta(days=numero)
        _voto(_votacao(run, f"2-{numero}", voted_on=dia), DEPUTADO, "Sim")


def test_exatamente_50_votos_cabem_em_1_pagina(client, run):
    # Borda da conta de `total_paginas`: 50 votos são 1 página, não 2 (`total // 50 + 1` erraria).
    _deputado(run)
    _votar_em(run, 50)

    primeira = _ok(client, _url())
    alem = _ok(client, f"{_url()}?pagina=2")

    assert (primeira["pagina"], primeira["total_paginas"]) == (1, 1)
    assert len(primeira["votos"]) == 50
    assert alem["votos"] == []
    assert (alem["pagina"], alem["total_paginas"]) == (2, 1)
    assert alem["atribuicao_das_votacoes"] is None
    assert alem["atribuicao_dos_votos"] is None


def test_exatamente_100_votos_sao_2_paginas(client, run):
    # Borda de múltiplo exato: 100 votos são 2 páginas, não 3 (`total // 50 + 1` erraria).
    _deputado(run)
    _votar_em(run, 100)

    segunda = _ok(client, f"{_url()}?pagina=2")
    terceira = _ok(client, f"{_url()}?pagina=3")

    assert (segunda["pagina"], segunda["total_paginas"]) == (2, 2)
    assert len(segunda["votos"]) == 50
    assert terceira["votos"] == []
    assert terceira["total_paginas"] == 2


def test_pagina_alem_da_ultima_devolve_lista_vazia(client, historico):
    corpo = _ok(client, f"{_url()}?pagina=9")

    assert corpo["votos"] == []
    assert (corpo["pagina"], corpo["total_paginas"]) == (9, 1)
    assert corpo["atribuicao_das_votacoes"] is None
    assert corpo["atribuicao_dos_votos"] is None


def test_o_historico_custa_tres_consultas_mesmo_com_muitos_votos(
    client, run, django_assert_num_queries
):
    _deputado(run)
    outra_coleta = _criar_run_dos_votos(datetime(2026, 11, 25, 9, 0, tzinfo=UTC))
    outra_coleta_das_votacoes = _criar_run(datetime(2026, 11, 25, 8, 0, tzinfo=UTC))
    for numero in range(1, 40):
        votacao = _votacao(outra_coleta_das_votacoes if numero % 3 else run, f"1-{numero}")
        _voto(votacao, DEPUTADO, "Sim", ingestion_run=outra_coleta if numero % 2 else run)
    _ok(client, _url())  # controle (e aquece o que o Django guarda em cache)

    # o deputado, a contagem e a página com votação e as duas atribuições num JOIN (sem N+1)
    with django_assert_num_queries(3):
        client.get(_url())


# --- Índice --------------------------------------------------------------------------------------


def test_voto_tem_indice_por_legislatura_e_id_do_deputado_no_modelo():
    indices = [i for i in CamaraVote._meta.indexes if i.fields == ["legislature_id", "camara_id"]]

    assert len(indices) == 1
    assert 0 < len(indices[0].name) <= 30  # o limite de nome de índice do Django (models.E034)


def test_voto_tem_indice_por_legislatura_e_id_do_deputado_no_banco():
    """No banco criado pelas migrações: a unique `(voting, camara_id)` não serve a esta busca."""
    with connection.cursor() as cursor:
        restricoes = connection.introspection.get_constraints(cursor, CamaraVote._meta.db_table)

    colunas = [r["columns"] for r in restricoes.values() if r["index"]]
    assert ["legislature_id", "camara_id"] in colunas
