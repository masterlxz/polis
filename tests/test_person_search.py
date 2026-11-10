"""Busca de pessoas por nome de urna (ADR 0016, ADR 0012, ADR 0009 fatia 4).

`GET /internal/v1/busca/?q=...`. Dados todos sintéticos, no formato dos nomes reais medidos em
2026-11-09 (21% com acento, 945 com ponto, 89 com hífen, 47 com espaço estranho, maior grupo de
homônimos com 6). O que mais importa: só o nome de urna é buscável (nunca o social), índice e
consulta tokenizam pela mesma regra, entrada do usuário nunca vira sintaxe do `to_tsquery`, e o
teto de tamanho e de resultados vale. Testes de 405 pedem antes um 200 de controle.
"""

import itertools
from datetime import date

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.elections import search
from apps.elections.models import Candidacy, Election, Person
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

URL = "/internal/v1/busca/"
NOME_SOCIAL_SECRETO = "Zz Social Interno"
CHAVES_RESULTADO = {"id", "nome", "ciclo", "uf", "partido", "aproximado"}

_sq = itertools.count(2_000_000_001)


def _pessoa(nome, **extra):
    return Person.objects.create(
        cycle_year=2026, tse_candidate_id=next(_sq), public_name=nome, **extra
    )


def _buscar(client, q):
    resposta = client.get(URL, {"q": q})
    assert resposta.status_code == 200, f"esperava 200 para q={q!r}, veio {resposta.status_code}"
    return resposta.json()["resultados"]


def _nomes(client, q):
    return [r["nome"] for r in _buscar(client, q)]


@pytest.fixture
def run():
    source = Source.objects.create(
        slug="tse",
        name="TSE",
        institution="Tribunal Superior Eleitoral",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    dataset = Dataset.objects.create(
        source=source,
        slug="consulta-cand-2026",
        name="Consulta de candidatos 2026",
        url="https://example.org/consulta_cand.zip",
        format=Dataset.Format.ZIP_CSV,
        license_basis=Dataset.LicenseBasis.DECLARED,
        license_id="cc-by",
        license_url="https://example.org/licencas/cc-by",
    )
    return IngestionRun.objects.create(dataset=dataset, source_url=dataset.url)


def _candidatura(run, pessoa, *, turno=1, data=date(2026, 10, 4), uf="SP", sigla="XYZ"):
    eleicao, _ = Election.objects.get_or_create(
        tse_code=6259,
        round=turno,
        defaults={
            "year": 2026,
            "kind_code": 2,
            "kind_name": "Eleição Ordinária",
            "description": "Eleições Gerais Estaduais 2026",
            "date": data,
        },
    )
    return Candidacy.objects.create(
        election=eleicao,
        person=pessoa,
        ballot_number=12345,
        office_code=6,
        office_name="DEPUTADO FEDERAL",
        scope="ESTADUAL",
        state=uf,
        electoral_unit_code=uf,
        electoral_unit_name="UNIDADE DE TESTE",
        party_number=12,
        party_acronym=sigla,
        party_name="Partido de Teste",
        ingestion_run=run,
        source_generated_at=timezone.now(),
    )


# --- achar pelo nome de urna -------------------------------------------------------------------


def test_acha_ignorando_palavras_do_meio(client):
    _pessoa("MARIA DA SILVA")

    assert _nomes(client, "maria silva") == ["MARIA DA SILVA"]


def test_acha_sem_acento_e_com_acento(client):
    _pessoa("JOÃO SOUZA")

    assert _nomes(client, "joao") == ["JOÃO SOUZA"]
    assert _nomes(client, "joão") == ["JOÃO SOUZA"]


def test_acha_enie_pelo_n(client):
    _pessoa("MUÑOZ LIMA")

    assert _nomes(client, "munoz") == ["MUÑOZ LIMA"]


def test_acha_por_prefixo(client):
    _pessoa("JOÃO SOUZA")
    _pessoa("JOANA LIMA")
    _pessoa("PEDRO LIMA")

    assert sorted(_nomes(client, "joa")) == ["JOANA LIMA", "JOÃO SOUZA"]


def test_hifen_vira_separador(client):
    _pessoa("ANA-MARIA")

    assert _nomes(client, "ana maria") == ["ANA-MARIA"]


def test_ponto_vira_separador_no_indice_e_na_consulta(client):
    """O parser do `to_tsvector` pode juntar `DR.JOAO` num token só; índice e consulta precisam
    usar a mesma regra (reduzir a [a-z0-9]+), senão 945 nomes reais com ponto somem da busca."""
    _pessoa("J.R. SILVA")
    _pessoa("DR.JOAO LIMA")

    assert _nomes(client, "j r silva") == ["J.R. SILVA"]
    assert _nomes(client, "silva") == ["J.R. SILVA"]
    assert _nomes(client, "joao") == ["DR.JOAO LIMA"]


def test_nome_com_digito(client):
    _pessoa("CABO 77")

    assert _nomes(client, "cabo 77") == ["CABO 77"]


def test_espacos_extras_na_consulta_e_no_nome(client):
    _pessoa("  MARIA   SILVA ")

    assert _nomes(client, "  maria   silva  ") == ["  MARIA   SILVA "]
    assert _nomes(client, "maria silva") == ["  MARIA   SILVA "]


# --- ordem, homônimos e teto -------------------------------------------------------------------


def test_nome_identico_a_consulta_vem_primeiro_depois_o_mais_curto(client):
    _pessoa("JOSÉ PEREIRA DOS SANTOS")
    _pessoa("JOSÉ PEREIRA")
    _pessoa("JOSÉ")

    assert _nomes(client, "jose") == ["JOSÉ", "JOSÉ PEREIRA", "JOSÉ PEREIRA DOS SANTOS"]


def test_homonimos_voltam_todos_cada_um_com_seu_id(client):
    pessoas = [_pessoa("CARLOS DA PADARIA") for _ in range(3)]

    resultados = _buscar(client, "carlos da padaria")

    assert sorted(r["id"] for r in resultados) == sorted(
        f"{p.cycle_year}-{p.tse_candidate_id}" for p in pessoas
    )


def test_no_maximo_20_resultados(client):
    for i in range(25):
        _pessoa(f"MARIA NUMERO {i}")

    assert len(_buscar(client, "maria")) == 20


# --- reserva por similaridade (pg_trgm) ---------------------------------------------------------


def test_erro_de_digitacao_cai_na_reserva_de_trigramas(client):
    _pessoa("MARIA SILVA")

    assert _nomes(client, "marai silva") == ["MARIA SILVA"]


def _aproximados(client, q):
    return {r["nome"]: r["aproximado"] for r in _buscar(client, q)}


def test_achado_pelo_indice_nao_e_aproximado(client):
    _pessoa("MARIA SILVA")

    assert _aproximados(client, "maria silva") == {"MARIA SILVA": False}


def test_achado_so_pela_reserva_e_aproximado(client):
    _pessoa("MARIA SILVA")

    assert _aproximados(client, "marai silva") == {"MARIA SILVA": True}


def test_prefixo_nao_e_aproximado(client):
    _pessoa("JOAO SILVA")

    assert _aproximados(client, "jo sil") == {"JOAO SILVA": False}


def test_mistura_exatos_sem_marca_e_parecidos_com_marca(client):
    _pessoa("MARIA SILVA")
    _pessoa("MARCIA SILVA")

    assert _aproximados(client, "maria silva") == {"MARIA SILVA": False, "MARCIA SILVA": True}


def _limiar_do_banco():
    # `show_limit()` (do pg_trgm) lê o limiar e carrega a biblioteca na conexão. O `SHOW` direto
    # falha com "unrecognized configuration parameter" se o pg_trgm ainda não foi usado nela.
    with connection.cursor() as cursor:
        cursor.execute("SELECT show_limit()")
        return cursor.fetchone()[0]


@pytest.mark.django_db(transaction=True)  # sem a transação do pytest-django: autocommit de verdade
def test_a_reserva_roda_com_o_limiar_do_indice_igual_ao_do_codigo(client, monkeypatch):
    # O `%` do pg_trgm usa `pg_trgm.similarity_threshold` (padrão 0,3), não o nosso 0,5: com 0,3 o
    # índice devolve dezenas de milhares de candidatos que o `similarity >= 0,5` descarta depois
    # (medido em 3 milhões de linhas: 820 ms por consulta).
    _pessoa("MARIA SILVA")
    vistos = {}
    executar_de_verdade = search._executar

    def espiao(sql, params):
        vistos["limiar_na_reserva" if sql == search._POR_SIMILARIDADE else "outro"] = (
            _limiar_do_banco()
        )
        return executar_de_verdade(sql, params)

    monkeypatch.setattr(search, "_executar", espiao)

    assert _aproximados(client, "marai silva") == {"MARIA SILVA": True}, "controle: caiu na reserva"
    assert vistos["limiar_na_reserva"] == search.LIMIAR_DE_SIMILARIDADE


@pytest.mark.django_db(transaction=True)
def test_o_limiar_nao_vaza_para_a_conexao_depois_da_busca(client):
    padrao = _limiar_do_banco()
    _pessoa("MARIA SILVA")

    assert _aproximados(client, "marai silva") == {"MARIA SILVA": True}, "controle: usou a reserva"

    assert _limiar_do_banco() == padrao


def test_com_5_exatos_a_reserva_nao_entra_e_nenhum_e_aproximado(client):
    for i in range(5):
        _pessoa(f"MARIA SILVA {i}")
    _pessoa("MARCIA SILVA")

    resultado = _aproximados(client, "maria silva")

    assert len(resultado) == 5
    assert not any(resultado.values())


# --- o que nunca entra --------------------------------------------------------------------------


def test_nome_social_nao_e_buscavel_nem_aparece(client):
    _pessoa("FULANO DE TAL", social_name=NOME_SOCIAL_SECRETO)

    assert _buscar(client, "zz social") == [], "o social não pode achar a pessoa"
    resposta = client.get(URL, {"q": "fulano"})
    assert resposta.status_code == 200, "controle: o nome de urna acha a pessoa"
    assert _nomes(client, "fulano") == ["FULANO DE TAL"]
    assert NOME_SOCIAL_SECRETO not in resposta.content.decode()


# --- entrada do usuário -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "q",
    [
        "",
        "   ",
        "!!!",
        ":*",
        "a & b",
        "a | b",
        "!x",
        "'; DROP TABLE elections_person; --",
        '"',
        "(",
        "\\",
    ],
)
def test_entrada_estranha_nunca_da_erro(client, q):
    _pessoa("MARIA SILVA")

    resposta = client.get(URL, {"q": q})

    assert resposta.status_code == 200
    assert isinstance(resposta.json()["resultados"], list)


def test_sem_parametro_q_devolve_lista_vazia(client):
    _pessoa("MARIA SILVA")

    resposta = client.get(URL)

    assert resposta.status_code == 200
    assert resposta.json() == {"resultados": []}


def test_operadores_do_tsquery_nao_funcionam(client):
    _pessoa("MARIA SILVA")
    _pessoa("PEDRO LIMA")

    assert _nomes(client, "maria | pedro") == [], "o | não pode virar OU"
    assert _nomes(client, "!maria") == ["MARIA SILVA"], "o ! não pode virar NÃO"


def test_minimo_de_2_caracteres(client):
    _pessoa("AMANDA LIMA")
    _pessoa("JULIA LIMA")

    assert _buscar(client, "a") == []
    assert _buscar(client, "a!") == [], "o símbolo não conta como caractere"
    assert _nomes(client, "ju") == ["JULIA LIMA"]


def test_teto_de_tamanho_e_de_palavras_da_consulta():
    from apps.elections.search import normalizar_consulta

    assert len(normalizar_consulta("maria " * 200)) == 10
    assert sum(len(t) for t in normalizar_consulta("x" * 5000)) <= 100
    assert normalizar_consulta("  Maria,  da-Silva! ") == ["maria", "da", "silva"]
    assert normalizar_consulta("JOÃO") == ["joao"]


def test_consulta_gigante_ainda_responde_200(client):
    _pessoa("MARIA SILVA")

    resposta = client.get(URL, {"q": "maria " * 800})

    assert resposta.status_code == 200


# --- saída ---------------------------------------------------------------------------------------


def test_formato_do_resultado(client, run):
    pessoa = _pessoa("MARIA SILVA")
    _candidatura(run, pessoa, uf="SP", sigla="XYZ")

    resposta = client.get(URL, {"q": "maria"})

    assert resposta.status_code == 200
    assert resposta["Content-Type"].startswith("application/json")
    corpo = resposta.json()
    assert set(corpo) == {"resultados"}
    [item] = corpo["resultados"]
    assert set(item) == CHAVES_RESULTADO
    assert item == {
        "id": f"2026-{pessoa.tse_candidate_id}",
        "nome": "MARIA SILVA",
        "ciclo": 2026,
        "uf": "SP",
        "partido": "XYZ",
        "aproximado": False,
    }


def test_uf_e_partido_vem_da_candidatura_mais_recente(client, run):
    pessoa = _pessoa("MARIA SILVA")
    _candidatura(run, pessoa, turno=1, data=date(2026, 10, 4), uf="SP", sigla="AAA")
    _candidatura(run, pessoa, turno=2, data=date(2026, 10, 25), uf="RJ", sigla="BBB")

    [item] = _buscar(client, "maria")

    assert (item["uf"], item["partido"]) == ("RJ", "BBB")


def test_pessoa_sem_candidatura_aparece_com_uf_e_partido_nulos(client):
    _pessoa("MARIA SILVA")

    [item] = _buscar(client, "maria")

    assert (item["uf"], item["partido"]) == (None, None)


# --- método e custo ------------------------------------------------------------------------------


def test_so_leitura(client):
    assert client.get(URL, {"q": "maria"}).status_code == 200, "controle"

    assert client.post(URL, {"q": "maria"}).status_code == 405
    assert client.delete(URL).status_code == 405


def test_no_maximo_2_consultas_ao_banco_com_20_resultados(client, run):
    for i in range(20):
        _candidatura(run, _pessoa(f"MARIA NUMERO {i}"))

    with CaptureQueriesContext(connection) as capturadas:
        assert len(_buscar(client, "maria")) == 20

    assert len(capturadas) <= 2, [q["sql"] for q in capturadas]


# --- migração e índice ---------------------------------------------------------------------------


def test_a_busca_por_tokens_pode_usar_o_indice_gin(client):
    for i in range(30):
        _pessoa(f"PESSOA NUMERO {i}")
    with CaptureQueriesContext(connection) as capturadas:
        _buscar(client, "pessoa numero")
    sql = capturadas[0]["sql"]

    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL enable_seqscan = off")
        cursor.execute("EXPLAIN " + sql)
        plano = "\n".join(linha[0] for linha in cursor.fetchall())

    assert "Index" in plano or "Bitmap" in plano, plano
    assert "Seq Scan on elections_person" not in plano, plano


@pytest.mark.django_db(transaction=True)
def test_migracao_e_reversivel():
    from django.core.management import call_command

    def _existe_coluna():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'elections_person' AND column_name = 'public_name_tsv'"
            )
            return cursor.fetchone()[0] == 1

    def _existe_indice_gin():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM pg_indexes WHERE tablename = 'elections_person' "
                "AND indexdef ILIKE '%gin%' AND indexdef ILIKE '%public_name_tsv%'"
            )
            return cursor.fetchone()[0] >= 1

    assert _existe_coluna() and _existe_indice_gin(), "controle: a migração nova não foi aplicada"
    call_command("migrate", "elections", "0001", verbosity=0)
    try:
        assert not _existe_coluna()
        assert not _existe_indice_gin()
    finally:
        call_command("migrate", "elections", verbosity=0)
    assert _existe_coluna() and _existe_indice_gin()
