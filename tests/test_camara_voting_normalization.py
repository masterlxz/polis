"""Normalização de `camara/votacoes-2026` e `camara/votos-2026` em `CamaraVoting` e `CamaraVote`
(ADR 0031, molde do ADR 0029). Dados sintéticos no formato medido em 2026-11-24 (`fontes/camara.md`,
Rodada 3). O bruto guarda TUDO como texto, como o leitor de CSV grava, em duas cargas: uma de
votações e uma de votos.

Regras: lê a carga mais recente de cada conjunto, sem rede; linha inválida ou conflito não gravam
nada; upsert pela chave (id da votação em texto; votação + id do deputado), nunca apaga; o voto NÃO
aponta para `Deputy` e guarda o id, a legislatura e o partido do momento do voto; `descricao` troca
quebra de linha por espaço; `voto` vazio é gravado vazio; os totais e o id da proposição valem `0`
(a fonte usa `0` em 4.101 de 9.153 votações para "sem proposição"). Os dois arquivos são coletados
em horas sorteadas: voto sem votação só é recusa quando a carga de votações é tão nova quanto a de
votos; se a de votos é mais nova, a normalização espera a próxima coleta.

Os módulos novos são importados dentro dos testes: antes de existirem, cada teste falha por si e a
coleta do pytest não para.
"""

from datetime import timedelta
from io import StringIO
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "valor-de-linha-que-nao-pode-vazar"
COLUNAS_VOTACOES = [
    "id",
    "data",
    "dataHoraRegistro",
    "siglaOrgao",
    "aprovacao",
    "votosSim",
    "votosNao",
    "votosOutros",
    "descricao",
    "ultimaApresentacaoProposicao_idProposicao",
]
COLUNAS_VOTOS = [
    "idVotacao",
    "dataHoraVoto",
    "voto",
    "deputado_id",
    "deputado_siglaPartido",
    "deputado_idLegislatura",
]


def votacao(codigo="2641546-7", **extra):
    base = {
        "id": codigo,
        "data": "2026-03-10",
        "dataHoraRegistro": "2026-03-10T15:21:04",
        "siglaOrgao": "PLEN",
        "aprovacao": "1",
        "votosSim": "300",
        "votosNao": "150",
        "votosOutros": "2",
        "descricao": "Aprovada a Emenda nº 1.",
        "ultimaApresentacaoProposicao_idProposicao": "2651254",
    }
    return {**base, **extra}


def voto(codigo="2641546-7", deputado=204379, texto="Sim", **extra):
    base = {
        "idVotacao": codigo,
        "dataHoraVoto": "2026-03-10T15:21:04",
        "voto": texto,
        "deputado_id": str(deputado),
        "deputado_siglaPartido": "PT",
        "deputado_idLegislatura": "57",
    }
    return {**base, **extra}


def modelos():
    """Os modelos, importados só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import CamaraVote, CamaraVoting

    return CamaraVoting, CamaraVote


def votacao_gravada(codigo):
    return modelos()[0].objects.get(camara_voting_id=codigo)


def voto_gravado(codigo, deputado):
    return modelos()[1].objects.get(voting__camara_voting_id=codigo, camara_id=deputado)


@pytest.fixture
def conjuntos():
    fonte = Source.objects.create(
        slug="camara",
        name="Câmara dos Deputados: Dados Abertos",
        institution="Câmara dos Deputados",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    votacoes = Dataset.objects.create(
        source=fonte,
        slug="votacoes-2026",
        name="Votações da Câmara (2026)",
        url="https://example.org/votacoes-2026.csv",
        format=Dataset.Format.CSV,
        allowed_columns=COLUNAS_VOTACOES,
    )
    votos = Dataset.objects.create(
        source=fonte,
        slug="votos-2026",
        name="Votos nominais da Câmara (2026)",
        url="https://example.org/votos-2026.csv",
        format=Dataset.Format.CSV,
        allowed_columns=COLUNAS_VOTOS,
    )
    return SimpleNamespace(votacoes=votacoes, votos=votos)


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


def cargas(conjuntos, linhas_votacoes, linhas_votos, **extra):
    """As duas cargas, com o mesmo `started_at` (a de votações é tão nova quanto a de votos)."""
    extra.setdefault("started_at", timezone.now())
    return (
        carga(conjuntos.votacoes, linhas_votacoes, **extra),
        carga(conjuntos.votos, linhas_votos, **extra),
    )


def normalizar_par(conjuntos, linhas_votacoes, linhas_votos):
    return normalizar_runs(*cargas(conjuntos, linhas_votacoes, linhas_votos))


def normalizar_runs(run_votacoes, run_votos):
    from apps.legislature import camara_voting_normalization as normalizacao

    return normalizacao.normalize(run_votacoes, run_votos)


def recusa(run_votacoes, run_votos):
    from apps.legislature import camara_voting_normalization as normalizacao

    with pytest.raises(normalizacao.NormalizationRefused) as erro:
        normalizacao.normalize(run_votacoes, run_votos)
    return str(erro.value)


def normalizar():
    saida = StringIO()
    call_command("normalize_camara_votacoes", stdout=saida, stderr=saida)
    return saida.getvalue()


# --- caminho feliz -----------------------------------------------------------------------------


def test_duas_votacoes_e_cinco_votos_criam_2_votacoes_e_5_votos(conjuntos):
    resultado = normalizar_par(
        conjuntos,
        [votacao("2641546-7"), votacao("2645346-18", descricao="Requerimento")],
        [
            voto("2641546-7", 204379, "Sim"),
            voto("2641546-7", 160976, "Não"),
            voto("2641546-7", 178957, "Abstenção"),
            voto("2645346-18", 204379, ""),
            voto("2645346-18", 160976, ""),
        ],
    )
    CamaraVoting, CamaraVote = modelos()
    assert (resultado.created, resultado.existing, resultado.votings_created) == (5, 0, 2)
    assert (CamaraVoting.objects.count(), CamaraVote.objects.count()) == (2, 5)
    primeira = votacao_gravada("2641546-7")
    assert primeira.votes.count() == 3
    assert primeira.voted_on.isoformat() == "2026-03-10"
    assert primeira.organ_acronym == "PLEN"
    assert primeira.description == "Aprovada a Emenda nº 1."
    assert primeira.proposition_id == 2651254


@pytest.mark.parametrize(
    ("bruto", "esperado"),
    [
        ("linha um\r\nlinha dois", "linha um linha dois"),
        ("linha um\nlinha dois", "linha um linha dois"),
        ("linha um\rlinha dois", "linha um linha dois"),
        ("a\r\nb\nc", "a b c"),
        ("linha um linha dois", "linha um linha dois"),
        ("linha um linha dois", "linha um linha dois"),
    ],
    ids=["crlf", "lf", "cr", "misturado", "separador_de_linha", "separador_de_paragrafo"],
)
def test_a_quebra_de_linha_da_descricao_vira_um_espaco(conjuntos, bruto, esperado):
    normalizar_par(conjuntos, [votacao(descricao=bruto)], [voto()])
    assert votacao_gravada("2641546-7").description == esperado


def test_outro_caractere_de_controle_na_descricao_recusa_a_carga(conjuntos):
    run_votacoes, run_votos = cargas(conjuntos, [votacao(descricao="a\x07b")], [voto()])
    mensagem = recusa(run_votacoes, run_votos)
    assert "descricao" in mensagem
    assert modelos()[0].objects.count() == 0


def test_voto_vazio_e_gravado_vazio_e_a_presenca_do_deputado_fica(conjuntos):
    normalizar_par(conjuntos, [votacao("2645346-18")], [voto("2645346-18", 204379, "")])
    gravado = voto_gravado("2645346-18", 204379)
    assert gravado.vote == ""
    assert gravado.camara_id == 204379


@pytest.mark.parametrize("codigo", ["1", "0", ""], ids=["um", "zero", "vazio"])
def test_aprovacao_fica_como_vem_sem_interpretar(conjuntos, codigo):
    normalizar_par(conjuntos, [votacao(aprovacao=codigo)], [voto()])
    assert votacao_gravada("2641546-7").approval == codigo


def test_total_zero_e_proposicao_zero_sao_aceitos_como_vem(conjuntos):
    # Medido: `votosSim` é 0 em 8.984 de 9.153 votações, e a proposição é 0 em 4.101.
    normalizar_par(
        conjuntos,
        [
            votacao(
                votosSim="0",
                votosNao="0",
                votosOutros="0",
                ultimaApresentacaoProposicao_idProposicao="0",
            )
        ],
        [voto()],
    )
    gravada = votacao_gravada("2641546-7")
    assert (gravada.total_yes, gravada.total_no, gravada.total_other) == (0, 0, 0)
    assert gravada.proposition_id == 0


def test_totais_da_fonte_sao_gravados_sem_conferir_com_a_contagem_dos_votos(conjuntos):
    normalizar_par(conjuntos, [votacao(votosSim="300", votosNao="150", votosOutros="2")], [voto()])
    gravada = votacao_gravada("2641546-7")
    assert (gravada.total_yes, gravada.total_no, gravada.total_other) == (300, 150, 2)
    assert gravada.votes.count() == 1


def test_o_voto_nao_aponta_para_deputy_e_vale_para_quem_nao_esta_na_lista(conjuntos):
    from apps.legislature.models import Deputy

    assert Deputy.objects.count() == 0
    normalizar_par(conjuntos, [votacao()], [voto(deputado=236518)])
    gravado = voto_gravado("2641546-7", 236518)
    assert (gravado.camara_id, gravado.legislature_id) == (236518, 57)


def test_o_partido_do_voto_e_o_da_data_da_votacao_e_nao_o_de_hoje(conjuntos):
    normalizar_par(
        conjuntos,
        [votacao("2641546-7"), votacao("2645346-18")],
        [
            voto("2641546-7", 204379, "Sim", deputado_siglaPartido="PT"),
            voto("2645346-18", 204379, "Não", deputado_siglaPartido="PL"),
        ],
    )
    assert voto_gravado("2641546-7", 204379).party_acronym == "PT"
    assert voto_gravado("2645346-18", 204379).party_acronym == "PL"


def test_nenhum_campo_do_modelo_guarda_a_identidade_do_deputado():
    CamaraVote = modelos()[1]
    campos = {campo.name for campo in CamaraVote._meta.get_fields()}
    assert not campos & {"name", "uri", "state", "photo", "party_uri"}


# --- idempotência e atualização ----------------------------------------------------------------


def test_segunda_normalizacao_da_mesma_carga_nao_cria_nada(conjuntos):
    runs = cargas(conjuntos, [votacao()], [voto(), voto(deputado=160976)])
    normalizar_runs(*runs)
    segunda = normalizar_runs(*runs)
    assert (segunda.created, segunda.existing, segunda.votings_created) == (0, 2, 0)
    assert votacao_gravada("2641546-7").votes.count() == 2


def test_linhas_identicas_viram_uma(conjuntos):
    resultado = normalizar_par(conjuntos, [votacao()], [voto(), voto()])
    assert (resultado.rows_read, resultado.unique) == (3, 1)


def test_a_fonte_corrigiu_descricao_aprovacao_e_voto_a_carga_nova_atualiza(conjuntos):
    normalizar_par(conjuntos, [votacao(aprovacao="1")], [voto(texto="Sim")])
    resultado = normalizar_par(
        conjuntos,
        [votacao(aprovacao="0", descricao="Descrição corrigida.")],
        [voto(texto="Não")],
    )
    assert (resultado.created, resultado.existing) == (0, 1)
    assert votacao_gravada("2641546-7").approval == "0"
    assert votacao_gravada("2641546-7").description == "Descrição corrigida."
    assert voto_gravado("2641546-7", 204379).vote == "Não"


def test_votacao_que_saiu_da_carga_nova_continua_no_banco(conjuntos):
    normalizar_par(conjuntos, [votacao("2641546-7"), votacao("2645346-18")], [voto("2641546-7")])
    normalizar_par(conjuntos, [votacao("2645346-18"), votacao("2650000-3")], [voto("2650000-3")])
    CamaraVoting, CamaraVote = modelos()
    codigos = set(CamaraVoting.objects.values_list("camara_voting_id", flat=True))
    assert codigos == {"2641546-7", "2645346-18", "2650000-3"}
    assert CamaraVote.objects.count() == 2


def test_voto_que_sumiu_da_carga_nova_continua_no_banco(conjuntos):
    normalizar_par(conjuntos, [votacao()], [voto(deputado=204379), voto(deputado=160976)])
    normalizar_par(conjuntos, [votacao()], [voto(deputado=204379)])
    assert modelos()[1].objects.count() == 2


# --- dado inválido e conflito (falha fechada) --------------------------------------------------


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("id", "2641546"),
        ("id", "x-1"),
        ("id", "٣-1"),
        ("id", "9999999999-9999999999"),
        ("data", "2026-13-40"),
        ("data", "10/03/2026"),
        ("siglaOrgao", ""),
        ("siglaOrgao", "x" * 21),
        ("aprovacao", "2"),
        ("votosSim", "-1"),
        ("votosSim", "٣"),
        ("votosNao", ""),
        ("votosOutros", "1.5"),
        ("ultimaApresentacaoProposicao_idProposicao", "abc"),
        ("ultimaApresentacaoProposicao_idProposicao", ""),
        ("descricao", "x" * 5001),
        ("descricao", "a\tb"),
    ],
)
def test_votacao_invalida_recusa_tudo_e_a_mensagem_cita_a_coluna_e_nunca_o_valor(
    conjuntos, coluna, valor
):
    run_votacoes, run_votos = cargas(
        conjuntos, [votacao(), votacao("2645346-18", **{coluna: valor})], [voto()]
    )
    mensagem = recusa(run_votacoes, run_votos)
    assert f"{coluna} (1)" in mensagem
    assert "Nada foi gravado" in mensagem
    assert valor not in mensagem or valor == ""
    CamaraVoting, CamaraVote = modelos()
    assert (CamaraVoting.objects.count(), CamaraVote.objects.count()) == (0, 0)


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("idVotacao", "2641546"),
        ("idVotacao", "9999999999-9999999999"),
        ("deputado_id", ""),
        ("deputado_id", "-5"),
        ("deputado_id", "0"),
        ("deputado_idLegislatura", "٥٧"),
        ("deputado_idLegislatura", ""),
        ("deputado_siglaPartido", "x" * 21),
        ("voto", "x" * 41),
    ],
)
def test_voto_invalido_recusa_tudo_e_a_mensagem_cita_a_coluna_e_nunca_o_valor(
    conjuntos, coluna, valor
):
    run_votacoes, run_votos = cargas(
        conjuntos, [votacao()], [voto(), voto(deputado=160976, **{coluna: valor})]
    )
    mensagem = recusa(run_votacoes, run_votos)
    assert f"{coluna} (1)" in mensagem
    assert "Nada foi gravado" in mensagem
    assert valor not in mensagem or valor == ""
    CamaraVoting, CamaraVote = modelos()
    assert (CamaraVoting.objects.count(), CamaraVote.objects.count()) == (0, 0)


def test_a_mesma_votacao_com_dados_diferentes_entre_linhas_e_conflito(conjuntos):
    run_votacoes, run_votos = cargas(
        conjuntos, [votacao(), votacao(descricao="Outra descrição.")], [voto()]
    )
    assert "conflitantes" in recusa(run_votacoes, run_votos)
    assert modelos()[0].objects.count() == 0


def test_o_mesmo_voto_com_posicoes_diferentes_no_bruto_e_conflito(conjuntos):
    run_votacoes, run_votos = cargas(conjuntos, [votacao()], [voto(texto="Sim"), voto(texto="Não")])
    assert "conflitantes" in recusa(run_votacoes, run_votos)
    assert modelos()[1].objects.count() == 0


def test_mensagem_de_recusa_nao_cita_valores_de_linha(conjuntos):
    run_votacoes, run_votos = cargas(
        conjuntos, [votacao(descricao=SEGREDO, siglaOrgao="x" * 21)], [voto()]
    )
    assert SEGREDO not in recusa(run_votacoes, run_votos)


# --- voto sem votação: a corrida entre as duas coletas ----------------------------------------


def test_voto_sem_votacao_recusa_quando_a_carga_de_votacoes_e_tao_nova_quanto_a_de_votos(
    conjuntos,
):
    run_votacoes, run_votos = cargas(
        conjuntos, [votacao("2641546-7")], [voto("2641546-7"), voto("2650000-3")]
    )
    mensagem = recusa(run_votacoes, run_votos)
    assert "sem votação" in mensagem
    assert "Nada foi gravado" in mensagem
    assert "2650000-3" not in mensagem
    assert modelos()[1].objects.count() == 0


def test_normalize_latest_espera_se_a_carga_de_votos_e_mais_nova_e_nao_grava_nada(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.votacoes, [votacao("2641546-7")], started_at=agora)
    carga(
        conjuntos.votos,
        [voto("2641546-7"), voto("2650000-3")],
        started_at=agora + timedelta(hours=2),
    )
    assert normalizacao.normalize_latest(conjuntos.votos) is None
    assert normalizacao.normalize_latest(conjuntos.votacoes) is None
    CamaraVoting, CamaraVote = modelos()
    assert (CamaraVoting.objects.count(), CamaraVote.objects.count()) == (0, 0)


def test_normalize_latest_recusa_se_a_carga_de_votacoes_e_mais_nova_e_ainda_falta_a_votacao(
    conjuntos,
):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.votos, [voto("2641546-7"), voto("2650000-3")], started_at=agora)
    carga(conjuntos.votacoes, [votacao("2641546-7")], started_at=agora + timedelta(hours=2))
    with pytest.raises(normalizacao.NormalizationRefused, match="sem votação"):
        normalizacao.normalize_latest(conjuntos.votacoes)
    assert modelos()[0].objects.count() == 0


def test_depois_que_a_votacao_chega_a_normalizacao_que_esperava_conclui(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.votacoes, [votacao("2641546-7")], started_at=agora)
    carga(
        conjuntos.votos,
        [voto("2641546-7"), voto("2650000-3")],
        started_at=agora + timedelta(hours=2),
    )
    assert normalizacao.normalize_latest(conjuntos.votos) is None
    carga(
        conjuntos.votacoes,
        [votacao("2641546-7"), votacao("2650000-3")],
        started_at=agora + timedelta(hours=3),
    )
    resultado = normalizacao.normalize_latest(conjuntos.votacoes)
    assert (resultado.created, resultado.votings_created) == (2, 2)


def cargas_com_orfao(conjuntos, atraso_dos_votos):
    """Votações em `agora`, votos (com um sem votação) `atraso_dos_votos` depois."""
    agora = timezone.now()
    carga(conjuntos.votacoes, [votacao("2641546-7")], started_at=agora)
    carga(
        conjuntos.votos,
        [voto("2641546-7"), voto("2650000-3")],
        started_at=agora + atraso_dos_votos,
    )


def test_a_espera_acaba_no_prazo_e_a_anomalia_aparece_como_recusa(conjuntos):
    # Votos 3 dias mais novos que as votações: não é a corrida de coletas, é votação que não vem.
    from apps.legislature import camara_voting_normalization as normalizacao

    cargas_com_orfao(conjuntos, timedelta(days=3))
    with pytest.raises(normalizacao.NormalizationRefused, match="sem votação"):
        normalizacao.normalize_latest(conjuntos.votos)


def test_dentro_do_prazo_de_48_horas_a_normalizacao_espera(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    cargas_com_orfao(conjuntos, timedelta(hours=48))
    assert normalizacao.normalize_latest(conjuntos.votos) is None


def test_um_segundo_alem_do_prazo_de_48_horas_recusa(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    cargas_com_orfao(conjuntos, timedelta(hours=48, seconds=1))
    with pytest.raises(normalizacao.NormalizationRefused, match="sem votação"):
        normalizacao.normalize_latest(conjuntos.votos)


def test_cargas_do_mesmo_instante_com_voto_sem_votacao_recusam(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    cargas_com_orfao(conjuntos, timedelta(0))
    with pytest.raises(normalizacao.NormalizationRefused, match="sem votação"):
        normalizacao.normalize_latest(conjuntos.votos)


# --- teto de linhas por carga ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("linhas_votacoes", "linhas_votos"),
    [(50_001, 1), (1, 500_001)],
    ids=["votacoes_demais", "votos_demais"],
)
def test_carga_acima_do_teto_de_linhas_recusa_antes_de_ler(
    conjuntos, linhas_votacoes, linhas_votos
):
    run_votacoes = carga(
        conjuntos.votacoes, [votacao()], rows_read=linhas_votacoes, rows_loaded=linhas_votacoes
    )
    run_votos = carga(conjuntos.votos, [voto()], rows_read=linhas_votos, rows_loaded=linhas_votos)
    mensagem = recusa(run_votacoes, run_votos)
    assert "limite de linhas" in mensagem
    assert "Nada foi gravado" in mensagem
    assert modelos()[0].objects.count() == 0


def test_carga_no_teto_de_linhas_passa(conjuntos):
    run_votacoes = carga(conjuntos.votacoes, [votacao()], rows_read=50_000, rows_loaded=50_000)
    run_votos = carga(conjuntos.votos, [voto()], rows_read=500_000, rows_loaded=500_000)
    assert normalizar_runs(run_votacoes, run_votos).created == 1


# --- lotes, e o espelho da detecção de carga já normalizada -----------------------------------


def test_a_gravacao_em_lotes_nao_perde_nem_duplica_linhas(conjuntos, monkeypatch):
    from apps.legislature import camara_voting_normalization as normalizacao

    monkeypatch.setattr(normalizacao, "BATCH_SIZE", 2)
    codigos = [f"26{n:05d}-1" for n in range(5)]
    resultado = normalizar_par(
        conjuntos,
        [votacao(codigo) for codigo in codigos],
        [voto(codigo, deputado) for codigo in codigos for deputado in (204379, 160976)],
    )
    CamaraVoting, CamaraVote = modelos()
    assert (resultado.votings_created, resultado.created, resultado.existing) == (5, 10, 0)
    assert (CamaraVoting.objects.count(), CamaraVote.objects.count()) == (5, 10)
    assert all(votacao_gravada(codigo).votes.count() == 2 for codigo in codigos)


def test_normalize_latest_normaliza_de_novo_quando_so_a_carga_de_votacoes_e_nova(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.votacoes, [votacao()], started_at=agora)
    carga(conjuntos.votos, [voto()], started_at=agora)
    normalizacao.normalize_latest(conjuntos.votacoes)
    carga(
        conjuntos.votacoes,
        [votacao(descricao="Descrição corrigida.")],
        started_at=agora + timedelta(hours=1),
    )
    assert normalizacao.normalize_latest(conjuntos.votacoes) is not None
    assert votacao_gravada("2641546-7").description == "Descrição corrigida."


@pytest.mark.parametrize(
    "estado",
    [
        {"state": IngestionRun.State.FAILED, "error_code": IngestionRun.ErrorCode.DOWNLOAD},
        {"state": IngestionRun.State.RUNNING, "finished_at": None},
    ],
    ids=["falhou", "em_andamento"],
)
def test_execucao_que_nao_terminou_bem_nao_e_a_carga_mais_recente(conjuntos, estado):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    cargas(conjuntos, [votacao()], [voto()], started_at=agora)
    carga(conjuntos.votacoes, [votacao("9999999-9")], started_at=agora, **estado)
    resultado = normalizacao.normalize_latest(conjuntos.votacoes)
    assert resultado.votings_created == 1
    assert modelos()[0].objects.filter(camara_voting_id="9999999-9").count() == 0


# --- admin -------------------------------------------------------------------------------------


@pytest.mark.parametrize("modelo", ["CamaraVoting", "CamaraVote"])
def test_os_campos_de_busca_do_admin_existem_no_modelo(modelo):
    from django.contrib import admin

    classe = getattr(__import__("apps.legislature.models", fromlist=[modelo]), modelo)
    for campo in admin.site._registry[classe].search_fields:
        caminho = campo.lstrip("=^@")
        classe.objects.filter(**{f"{caminho}__icontains": "x"}).exists()


# --- falha no meio -----------------------------------------------------------------------------


def test_falha_no_meio_nao_deixa_gravacao_parcial(conjuntos, monkeypatch):
    """A gravação é uma transação só: se o banco recusar no meio, nem a votação fica."""
    run_votacoes, run_votos = cargas(
        conjuntos,
        [votacao("2641546-7"), votacao("2645346-18")],
        [voto("2641546-7"), voto("2645346-18")],
    )
    CamaraVote = modelos()[1]
    original = CamaraVote.objects.bulk_create

    def quebra(objetos, *args, **kwargs):
        original(objetos[:1], *args, **kwargs)
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(CamaraVote.objects, "bulk_create", quebra)
    with pytest.raises(RuntimeError):
        normalizar_runs(run_votacoes, run_votos)
    assert modelos()[0].objects.count() == 0
    assert CamaraVote.objects.count() == 0


# --- encadeamento com o agendador ---------------------------------------------------------------


def test_os_dois_conjuntos_apontam_para_o_mesmo_normalizador():
    caminho = "apps.legislature.camara_voting_normalization.normalize_latest"
    assert settings.NORMALIZERS["camara/votacoes-2026"] == caminho
    assert settings.NORMALIZERS["camara/votos-2026"] == caminho


def test_normalize_latest_com_so_uma_das_cargas_devolve_none(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    carga(conjuntos.votacoes, [votacao()])
    assert normalizacao.normalize_latest(conjuntos.votacoes) is None
    assert normalizacao.normalize_latest(conjuntos.votos) is None


def test_normalize_latest_ignora_cargas_ja_normalizadas(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    cargas(conjuntos, [votacao()], [voto()])
    primeira = normalizacao.normalize_latest(conjuntos.votacoes)
    assert primeira.created == 1
    assert normalizacao.normalize_latest(conjuntos.votacoes) is None
    assert normalizacao.normalize_latest(conjuntos.votos) is None


def test_normalize_latest_normaliza_de_novo_quando_so_a_carga_de_votos_e_nova(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    agora = timezone.now()
    carga(conjuntos.votacoes, [votacao()], started_at=agora)
    carga(conjuntos.votos, [voto(deputado=204379)], started_at=agora)
    normalizacao.normalize_latest(conjuntos.votacoes)
    carga(
        conjuntos.votos,
        [voto(deputado=204379), voto(deputado=160976)],
        started_at=agora + timedelta(hours=1),
    )
    resultado = normalizacao.normalize_latest(conjuntos.votos)
    assert (resultado.created, resultado.existing) == (1, 1)
    assert modelos()[1].objects.count() == 2


def test_carga_sem_linhas_nao_conta(conjuntos):
    from apps.legislature import camara_voting_normalization as normalizacao

    carga(conjuntos.votacoes, [], rows_loaded=0)
    carga(conjuntos.votos, [], rows_loaded=0)
    assert normalizacao.normalize_latest(conjuntos.votacoes) is None


# --- comando -----------------------------------------------------------------------------------


def test_comando_normaliza_e_resume_so_com_contagens(conjuntos):
    cargas(
        conjuntos,
        [votacao(descricao=SEGREDO)],
        [voto(deputado=204379), voto(deputado=160976)],
    )
    saida = normalizar()
    assert "linhas lidas 3" in saida
    assert "criadas 2" in saida
    assert SEGREDO not in saida


def test_comando_sem_os_conjuntos_diz_o_que_falta(db):
    with pytest.raises(CommandError, match="camara/votacoes-2026"):
        normalizar()


def test_comando_sem_carga_manda_rodar_a_coleta(conjuntos):
    with pytest.raises(CommandError, match="ingest_dataset"):
        normalizar()


def test_comando_repassa_a_recusa_sem_valores(conjuntos):
    cargas(conjuntos, [votacao(descricao=SEGREDO, siglaOrgao="x" * 21)], [voto()])
    with pytest.raises(CommandError) as erro:
        normalizar()
    assert SEGREDO not in str(erro.value)
    assert "siglaOrgao" in str(erro.value)


# --- modelos -----------------------------------------------------------------------------------


def test_o_id_da_votacao_e_unico_e_o_voto_e_unico_por_votacao_e_deputado(conjuntos):
    CamaraVoting, CamaraVote = modelos()
    normalizar_par(conjuntos, [votacao()], [voto()])
    existente = votacao_gravada("2641546-7")
    campos = {
        "camara_voting_id": "2641546-7",
        "voted_on": existente.voted_on,
        "organ_acronym": "PLEN",
        "approval": "1",
        "total_yes": 1,
        "total_no": 1,
        "total_other": 1,
        "description": "",
        "proposition_id": 0,
        "ingestion_run": existente.ingestion_run,
    }
    with pytest.raises(IntegrityError), transaction.atomic():
        CamaraVoting.objects.create(**campos)
    with pytest.raises(IntegrityError), transaction.atomic():
        CamaraVote.objects.create(
            voting=existente,
            camara_id=204379,
            legislature_id=57,
            party_acronym="PT",
            vote="Sim",
            ingestion_run=existente.ingestion_run,
        )
