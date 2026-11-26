"""Normalização de `camara/votacoes-proposicoes-2026` e `camara/votacoes-objetos-2026` em
`CamaraProposition` e `CamaraVotingProposition` (Sessão 107, Rodada 4 de `fontes/camara.md`).
Dados sintéticos no formato medido em 2026-11-26; o bruto guarda TUDO como texto.

Regras: cada arquivo é normalizado SOZINHO (a carga mais recente do próprio conjunto), sem rede; o
`origin` da ligação vem do conjunto; linha inválida ou conflito dentro do arquivo não gravam nada;
upsert pela chave (id da proposição; votação + proposição), nunca apaga; a ligação NÃO tem FK para
a votação (guarda o texto do id, a junção é na leitura), então não há espera nem corrida entre
coletas; entre os dois arquivos vale a última gravação (medido: 0 conflitos nas 21 proposições
comuns).

Os módulos novos são importados dentro dos testes: antes de existirem, cada teste falha por si e a
coleta do pytest não para.
"""

from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "valor-de-linha-que-nao-pode-vazar"
COLUNAS = [
    "idVotacao",
    "proposicao_id",
    "proposicao_titulo",
    "proposicao_ementa",
    "proposicao_siglaTipo",
    "proposicao_numero",
    "proposicao_ano",
]


def linha(votacao="104333-87", proposicao="104333", **extra):
    base = {
        "idVotacao": votacao,
        "proposicao_id": proposicao,
        "proposicao_titulo": "PL 11/2003",
        "proposicao_ementa": "Proíbe a veiculação de peças publicitárias.",
        "proposicao_siglaTipo": "PL",
        "proposicao_numero": "11",
        "proposicao_ano": "2003",
    }
    return {**base, **extra}


@pytest.fixture
def conjuntos():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    proposicoes = Dataset.objects.create(
        source=fonte,
        slug="votacoes-proposicoes-2026",
        name="Proposições das votações da Câmara (2026)",
        url="https://example.org/votacoesProposicoes-2026.csv",
        format=Dataset.Format.CSV,
        allowed_columns=COLUNAS,
    )
    objetos = Dataset.objects.create(
        source=fonte,
        slug="votacoes-objetos-2026",
        name="Objetos das votações da Câmara (2026)",
        url="https://example.org/votacoesObjetos-2026.csv",
        format=Dataset.Format.CSV,
        allowed_columns=COLUNAS,
    )
    return SimpleNamespace(proposicoes=proposicoes, objetos=objetos)


def carga(dataset, linhas, **extra):
    campos = {
        "state": IngestionRun.State.SUCCEEDED,
        "finished_at": timezone.now(),
        "sha256_original": HASH,
        "rows_read": len(linhas),
        "rows_loaded": len(linhas),
        **extra,
    }
    run = IngestionRun.objects.create(dataset=dataset, source_url=dataset.url, **campos)
    RawRecord.objects.bulk_create(
        [RawRecord(run=run, item_name="download.zip", values=v) for v in linhas]
    )
    return run


def modelos():
    """Os modelos, importados só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import CamaraProposition, CamaraVotingProposition

    return CamaraProposition, CamaraVotingProposition


def normalizar(run, origem="proposicoes"):
    from apps.legislature import camara_proposition_normalization as normalizacao

    return normalizacao.normalize(run, origem)


def recusa(run, origem="proposicoes"):
    from apps.legislature import camara_proposition_normalization as normalizacao

    with pytest.raises(normalizacao.NormalizationRefused) as erro:
        normalizacao.normalize(run, origem)
    return str(erro.value)


def proposicao_gravada(codigo):
    return modelos()[0].objects.get(camara_id=codigo)


def contagens():
    proposicoes, ligacoes = modelos()
    return proposicoes.objects.count(), ligacoes.objects.count()


# --- caminho feliz -----------------------------------------------------------------------------


def test_uma_linha_grava_a_proposicao_e_a_ligacao_com_a_origem(conjuntos):
    run = carga(conjuntos.proposicoes, [linha()])
    resultado = normalizar(run)
    assert (resultado.rows_read, resultado.created, resultado.existing) == (1, 1, 0)
    assert resultado.links_created == 1
    proposicao = proposicao_gravada(104333)
    assert (proposicao.title, proposicao.type_acronym, proposicao.number, proposicao.year) == (
        "PL 11/2003",
        "PL",
        11,
        2003,
    )
    assert proposicao.ementa == "Proíbe a veiculação de peças publicitárias."
    ligacao = modelos()[1].objects.get()
    assert (ligacao.camara_voting_id, ligacao.proposition_id, ligacao.origin) == (
        "104333-87",
        proposicao.pk,
        "proposicoes",
    )


def test_ano_vazio_grava_nulo_e_o_titulo_inteiro(conjuntos):
    run = carga(
        conjuntos.objetos,
        [
            linha(
                "2555417-29",
                "2600556",
                proposicao_titulo="RDF 1 => MPV 1312/2025",
                proposicao_siglaTipo="RDF",
                proposicao_numero="1",
                proposicao_ano="",
            )
        ],
    )
    normalizar(run, "objetos")
    proposicao = proposicao_gravada(2600556)
    assert proposicao.year is None
    assert proposicao.title == "RDF 1 => MPV 1312/2025"
    assert modelos()[1].objects.get().origin == "objetos"


def test_quebra_de_linha_e_tab_da_ementa_viram_espaco_e_ementa_vazia_e_aceita(conjuntos):
    run = carga(
        conjuntos.proposicoes,
        [
            linha("1-1", "1", proposicao_ementa="a\nb\r\nc\td"),
            linha("1-1", "2", proposicao_ementa=""),
        ],
    )
    normalizar(run)
    assert proposicao_gravada(1).ementa == "a b c d"
    assert proposicao_gravada(2).ementa == ""


def test_outro_controle_na_ementa_recusa_tudo_e_a_mensagem_cita_a_coluna_e_nunca_o_valor(
    conjuntos,
):
    run = carga(
        conjuntos.proposicoes,
        [linha("1-1", "1"), linha("1-1", "2", proposicao_ementa=f"{SEGREDO}\x07")],
    )
    mensagem = recusa(run)
    assert "proposicao_ementa (1)" in mensagem
    assert "Nada foi gravado" in mensagem
    assert SEGREDO not in mensagem
    assert contagens() == (0, 0)


def test_linha_invalida_recusa_tudo_e_a_mensagem_nunca_cita_valores(conjuntos):
    run = carga(
        conjuntos.proposicoes,
        [linha("1-1", "1"), linha("1-1", "2", proposicao_titulo=SEGREDO * 5)],
    )
    mensagem = recusa(run)
    assert "proposicao_titulo (1)" in mensagem
    assert SEGREDO not in mensagem
    assert contagens() == (0, 0)


# --- repetição e conflito ----------------------------------------------------------------------


def test_linhas_identicas_viram_uma_proposicao_e_uma_ligacao(conjuntos):
    run = carga(conjuntos.proposicoes, [linha(), linha()])
    resultado = normalizar(run)
    assert contagens() == (1, 1)
    assert (resultado.rows_read, resultado.unique) == (2, 1)


def test_a_mesma_proposicao_em_duas_votacoes_e_uma_proposicao_e_duas_ligacoes(conjuntos):
    run = carga(conjuntos.proposicoes, [linha("1-1"), linha("2-2")])
    normalizar(run)
    assert contagens() == (1, 2)


def test_a_mesma_proposicao_com_titulo_diferente_no_mesmo_arquivo_e_conflito(conjuntos):
    run = carga(conjuntos.proposicoes, [linha("1-1"), linha("2-2", proposicao_titulo="PL 12/2003")])
    mensagem = recusa(run)
    assert "conflitantes" in mensagem
    assert "Nada foi gravado" in mensagem
    assert contagens() == (0, 0)


def test_a_mesma_proposicao_nos_dois_arquivos_e_uma_proposicao_e_uma_ligacao_por_origem(
    conjuntos,
):
    normalizar(carga(conjuntos.proposicoes, [linha("1-1")]), "proposicoes")
    normalizar(carga(conjuntos.objetos, [linha("2-2")]), "objetos")
    assert contagens() == (1, 2)
    assert set(modelos()[1].objects.values_list("origin", flat=True)) == {"proposicoes", "objetos"}


# --- idempotência e correção da fonte ----------------------------------------------------------


def test_segunda_normalizacao_da_mesma_carga_nao_cria_nada(conjuntos):
    run = carga(conjuntos.proposicoes, [linha("1-1"), linha("2-2", "104334")])
    normalizar(run)
    resultado = normalizar(run)
    assert (resultado.created, resultado.existing, resultado.links_created) == (0, 2, 0)
    assert contagens() == (2, 2)


def test_a_fonte_corrigiu_titulo_e_ementa_a_carga_nova_atualiza(conjuntos):
    normalizar(carga(conjuntos.proposicoes, [linha()]))
    nova = carga(
        conjuntos.proposicoes,
        [linha(proposicao_titulo="PL 11/2003 (corrigido)", proposicao_ementa="Nova ementa.")],
    )
    normalizar(nova)
    proposicao = proposicao_gravada(104333)
    assert (proposicao.title, proposicao.ementa) == ("PL 11/2003 (corrigido)", "Nova ementa.")
    assert proposicao.ingestion_run == nova
    assert contagens() == (1, 1)


def test_proposicao_e_ligacao_que_sairam_da_carga_nova_continuam_no_banco(conjuntos):
    normalizar(carga(conjuntos.proposicoes, [linha("1-1"), linha("2-2", "104334")]))
    normalizar(carga(conjuntos.proposicoes, [linha("1-1")]))
    assert contagens() == (2, 2)


# --- a ligação não depende da votação ----------------------------------------------------------


def test_votacao_que_nao_esta_no_banco_nao_impede_a_gravacao(conjuntos):
    from apps.legislature.models import CamaraVoting

    normalizar(carga(conjuntos.proposicoes, [linha("9999999-99")]))
    assert CamaraVoting.objects.count() == 0
    assert contagens() == (1, 1)


def test_a_ligacao_nao_tem_chave_para_a_votacao():
    from apps.legislature.models import CamaraVoting, CamaraVotingProposition

    destinos = {
        campo.related_model
        for campo in CamaraVotingProposition._meta.get_fields()
        if campo.is_relation and campo.related_model is not None
    }
    assert CamaraVoting not in destinos


# --- teto, lotes e transação -------------------------------------------------------------------


@pytest.mark.parametrize(("linhas", "recusa_esperada"), [(500_001, True), (500_000, False)])
def test_carga_acima_do_teto_de_linhas_recusa_antes_de_ler_e_no_teto_passa(
    conjuntos, linhas, recusa_esperada
):
    run = carga(conjuntos.proposicoes, [linha()], rows_read=linhas, rows_loaded=linhas)
    if recusa_esperada:
        mensagem = recusa(run)
        assert "limite de linhas" in mensagem
        assert "Nada foi gravado" in mensagem
        assert contagens() == (0, 0)
    else:
        assert normalizar(run).created == 1


def test_a_gravacao_em_lotes_nao_perde_nem_duplica_linhas(conjuntos, monkeypatch):
    from apps.legislature import camara_proposition_normalization as normalizacao

    monkeypatch.setattr(normalizacao, "BATCH_SIZE", 2)
    linhas = [linha(f"{n}-1", str(100 + n)) for n in range(5)]
    resultado = normalizar(carga(conjuntos.proposicoes, linhas))
    assert (resultado.created, resultado.links_created) == (5, 5)
    assert contagens() == (5, 5)


def test_falha_no_meio_nao_deixa_gravacao_parcial(conjuntos, monkeypatch):
    """A gravação é uma transação só: se o banco recusar nas ligações, nem a proposição fica."""
    run = carga(conjuntos.proposicoes, [linha("1-1", "1"), linha("2-2", "2")])
    ligacoes = modelos()[1]
    original = ligacoes.objects.bulk_create

    def quebra(objetos, *args, **kwargs):
        original(objetos[:1], *args, **kwargs)
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(ligacoes.objects, "bulk_create", quebra)
    with pytest.raises(RuntimeError):
        normalizar(run)
    assert contagens() == (0, 0)


# --- normalize_latest e o comando --------------------------------------------------------------


def test_normalize_latest_usa_a_carga_mais_recente_do_proprio_conjunto_e_a_origem_dele(conjuntos):
    from apps.legislature import camara_proposition_normalization as normalizacao

    carga(conjuntos.objetos, [linha("1-1", "1")])
    carga(conjuntos.proposicoes, [linha("2-2", "2")])
    resultado = normalizacao.normalize_latest(conjuntos.objetos)
    assert resultado.created == 1
    assert modelos()[1].objects.get().origin == "objetos"
    assert not modelos()[0].objects.filter(camara_id=2).exists()


def test_normalize_latest_sem_carga_com_linhas_devolve_none(conjuntos):
    from apps.legislature import camara_proposition_normalization as normalizacao

    assert normalizacao.normalize_latest(conjuntos.proposicoes) is None
    carga(conjuntos.proposicoes, [], rows_read=0, rows_loaded=0)
    assert normalizacao.normalize_latest(conjuntos.proposicoes) is None


def test_normalize_latest_de_carga_ja_normalizada_devolve_none(conjuntos):
    from apps.legislature import camara_proposition_normalization as normalizacao

    carga(conjuntos.proposicoes, [linha()])
    assert normalizacao.normalize_latest(conjuntos.proposicoes).created == 1
    assert normalizacao.normalize_latest(conjuntos.proposicoes) is None


@pytest.mark.parametrize(
    "estado",
    [
        {"state": IngestionRun.State.FAILED, "error_code": IngestionRun.ErrorCode.DOWNLOAD},
        {"state": IngestionRun.State.RUNNING, "finished_at": None},
    ],
    ids=["falhou", "em_andamento"],
)
def test_execucao_que_nao_terminou_bem_nao_e_a_carga_mais_recente(conjuntos, estado):
    from apps.legislature import camara_proposition_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.proposicoes, [linha("1-1", "1")], started_at=agora)
    carga(conjuntos.proposicoes, [linha("9-9", "9")], started_at=agora, **estado)
    assert normalizacao.normalize_latest(conjuntos.proposicoes).created == 1
    assert not modelos()[0].objects.filter(camara_id=9).exists()


def comando():
    saida = StringIO()
    call_command("normalize_camara_proposicoes", stdout=saida, stderr=saida)
    return saida.getvalue()


def test_comando_normaliza_os_dois_arquivos_e_resume_so_com_contagens(conjuntos):
    carga(conjuntos.proposicoes, [linha("1-1", "1", proposicao_ementa=SEGREDO)])
    carga(conjuntos.objetos, [linha("2-2", "2"), linha("2-2", "3")])
    saida = comando()
    assert "linhas lidas 1" in saida
    assert "linhas lidas 2" in saida
    assert SEGREDO not in saida
    assert contagens() == (3, 3)


def test_comando_sem_os_conjuntos_diz_o_que_falta(db):
    with pytest.raises(CommandError, match="camara/votacoes-proposicoes-2026"):
        comando()


def test_comando_sem_carga_manda_rodar_a_coleta(conjuntos):
    with pytest.raises(CommandError, match="ingest_dataset"):
        comando()


def test_comando_repassa_a_recusa_sem_valores(conjuntos):
    carga(conjuntos.proposicoes, [linha(proposicao_titulo=SEGREDO * 5)])
    carga(conjuntos.objetos, [linha()])
    with pytest.raises(CommandError) as erro:
        comando()
    assert SEGREDO not in str(erro.value)
    assert "proposicao_titulo" in str(erro.value)


# --- modelos -----------------------------------------------------------------------------------


def test_o_id_da_proposicao_e_unico_e_a_ligacao_e_unica_por_votacao_e_proposicao(conjuntos):
    Proposicao, Ligacao = modelos()
    normalizar(carga(conjuntos.proposicoes, [linha()]))
    existente = proposicao_gravada(104333)
    with pytest.raises(IntegrityError), transaction.atomic():
        Proposicao.objects.create(
            camara_id=104333,
            title="x",
            type_acronym="PL",
            number=1,
            ingestion_run=existente.ingestion_run,
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Ligacao.objects.create(
            camara_voting_id="104333-87",
            proposition=existente,
            origin="objetos",
            ingestion_run=existente.ingestion_run,
        )
