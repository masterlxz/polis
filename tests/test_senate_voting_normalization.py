"""Normalização de `senado/votacoes` em `SenateVoting` e `SenateVote` (ADR 0029, molde dos ADR 0022,
0027 e 0028). Dados sintéticos. O bruto guarda TUDO como texto, como o leitor JSON grava, uma linha
por voto com a votação repetida.

Regras: lê a carga mais recente, sem rede; linha inválida ou conflito não gravam nada; upsert pela
chave (código da votação; votação + código do parlamentar), nunca apaga; o voto NÃO aponta para
`Senator` (suplente que votou e saiu da lista não está lá) e guarda nome, partido e UF do momento
do voto; votação secreta é gravada com a marca e os totais, e `Votou` é só participação.
"""

from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, RawRecord, Source

pytestmark = pytest.mark.django_db

HASH = "a" * 64
SEGREDO = "valor-de-linha-que-nao-pode-vazar"
COLUNAS = [
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


def linha(votacao, parlamentar, sigla="Sim", **extra):
    base = {
        "codigoSessaoVotacao": str(votacao),
        "dataSessao": "2026-11-12",
        "sigla": "PL",
        "numero": "123",
        "ano": "2026",
        "identificacao": "PL 123/2026",
        "ementa": "Dispõe sobre algo.",
        "resultadoVotacao": "A",
        "votacaoSecreta": "N",
        "totalVotosSim": "",
        "totalVotosNao": "",
        "totalVotosAbstencao": "",
        "idProcesso": str(5000 + votacao),
        "codigoMateria": str(7000 + votacao),
        "codigoParlamentar": str(parlamentar),
        "nomeParlamentar": f"Senador {parlamentar}",
        "siglaPartidoParlamentar": "XYZ",
        "siglaUFParlamentar": "SP",
        "siglaVotoParlamentar": sigla,
    }
    return {**base, **extra}


def modelos():
    """Os modelos, importados só ao usar: cada teste falha por si, não a coleta."""
    from apps.legislature.models import SenateVote, SenateVoting

    return SenateVoting, SenateVote


def votacao_gravada(codigo):
    return modelos()[0].objects.get(session_voting_code=codigo)


def voto_gravado(votacao, parlamentar):
    return modelos()[1].objects.get(voting__session_voting_code=votacao, senate_id=parlamentar)


@pytest.fixture
def dataset():
    fonte = Source.objects.create(
        slug="senado",
        name="Senado Federal: Dados Abertos",
        institution="Senado Federal",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )
    return Dataset.objects.create(
        source=fonte,
        slug="votacoes",
        name="Votações do Senado",
        url="https://example.org/votacao",
        format=Dataset.Format.JSON_SENADO_VOTACOES,
        allowed_columns=COLUNAS,
    )


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
    RawRecord.objects.bulk_create([RawRecord(run=run, item_name="dados", values=v) for v in linhas])
    return run


def normalizar():
    saida = StringIO()
    call_command("normalize_senado_votacoes", stdout=saida, stderr=saida)
    return saida.getvalue()


def normalizar_run(run):
    from apps.legislature import senate_voting_normalization as normalizacao

    return normalizacao.normalize(run)


def recusa(run):
    from apps.legislature import senate_voting_normalization as normalizacao

    with pytest.raises(normalizacao.NormalizationRefused) as erro:
        normalizacao.normalize(run)
    return str(erro.value)


# --- caminho feliz -----------------------------------------------------------------------------


def test_duas_votacoes_de_tres_votos_criam_2_votacoes_e_6_votos(dataset):
    votos = ((10, "Sim"), (20, "Não"), (30, "AP"))
    linhas = [linha(v, p, sigla) for v in (1, 2) for p, sigla in votos]
    resultado = normalizar_run(carga(dataset, linhas))
    assert (resultado.rows_read, resultado.unique, resultado.created, resultado.existing) == (
        6,
        6,
        6,
        0,
    )
    assert resultado.votings_created == 2
    votacao = votacao_gravada(1)
    assert votacao.voted_on == date(2026, 11, 12)
    assert (votacao.type_acronym, votacao.number, votacao.year) == ("PL", "123", 2026)
    assert votacao.identification == "PL 123/2026"
    assert votacao.summary == "Dispõe sobre algo."
    assert votacao.result == "A"
    assert votacao.secret is False
    assert (votacao.process_id, votacao.matter_id) == (5001, 7001)
    voto = voto_gravado(1, 20)
    assert (voto.name, voto.party_acronym, voto.state, voto.vote_code) == (
        "Senador 20",
        "XYZ",
        "SP",
        "Não",
    )


def test_totais_nulos_das_votacoes_abertas_ficam_nulos(dataset):
    normalizar_run(carga(dataset, [linha(1, 10)]))
    votacao = votacao_gravada(1)
    assert (votacao.total_yes, votacao.total_no, votacao.total_abstention) == (None, None, None)


def test_votacao_secreta_guarda_a_marca_os_totais_e_o_votou_como_veio(dataset):
    totais = {
        "votacaoSecreta": "S",
        "totalVotosSim": "43",
        "totalVotosNao": "2",
        "totalVotosAbstencao": "1",
    }
    linhas = [
        linha(1, 10, "Votou", **totais),
        linha(1, 20, "Votou", **totais),
        linha(1, 30, "AP", **totais),
    ]
    normalizar_run(carga(dataset, linhas))
    votacao = votacao_gravada(1)
    assert votacao.secret is True
    assert (votacao.total_yes, votacao.total_no, votacao.total_abstention) == (43, 2, 1)
    assert voto_gravado(1, 10).vote_code == "Votou"
    assert voto_gravado(1, 30).vote_code == "AP"


def test_sigla_desconhecida_e_gravada_como_veio_sem_mapeamento(dataset):
    linhas = [linha(1, 10, "P-NRV"), linha(1, 20, "Presidente (art. 51 RISF)")]
    normalizar_run(carga(dataset, linhas))
    assert voto_gravado(1, 10).vote_code == "P-NRV"
    assert voto_gravado(1, 20).vote_code == "Presidente (art. 51 RISF)"


def test_o_voto_nao_aponta_para_senator_e_vale_para_quem_nao_esta_na_lista(dataset):
    from apps.legislature.models import Senator

    assert Senator.objects.count() == 0
    normalizar_run(carga(dataset, [linha(1, 99999)]))
    assert voto_gravado(1, 99999).name == "Senador 99999"
    campos = {f.name for f in modelos()[1]._meta.get_fields()}
    assert "senator" not in campos


def test_partido_literal_sem_partido_e_aceito_como_veio(dataset):
    normalizar_run(carga(dataset, [linha(1, 10, siglaPartidoParlamentar="S/Partido")]))
    assert voto_gravado(1, 10).party_acronym == "S/Partido"


def test_o_partido_do_voto_e_o_da_data_da_votacao_e_nao_o_de_hoje(dataset):
    """Mesmo parlamentar, duas votações, dois partidos: cada voto guarda o seu."""
    linhas = [
        linha(1, 10, siglaPartidoParlamentar="AAA"),
        linha(2, 10, siglaPartidoParlamentar="BBB", dataSessao="2026-11-13"),
    ]
    normalizar_run(carga(dataset, linhas))
    assert voto_gravado(1, 10).party_acronym == "AAA"
    assert voto_gravado(2, 10).party_acronym == "BBB"


# --- idempotência, correção e "nunca apaga" ----------------------------------------------------


def test_segunda_normalizacao_da_mesma_carga_nao_cria_nada(dataset):
    run = carga(dataset, [linha(1, 10), linha(1, 20)])
    normalizar_run(run)
    segunda = normalizar_run(run)
    assert (segunda.created, segunda.existing, segunda.votings_created) == (0, 2, 0)
    assert votacao_gravada(1).votes.count() == 2


def test_linhas_identicas_viram_uma(dataset):
    resultado = normalizar_run(carga(dataset, [linha(1, 10), linha(1, 10)]))
    assert (resultado.rows_read, resultado.unique) == (2, 1)


def test_a_fonte_corrigiu_resultado_ementa_e_voto_a_carga_nova_atualiza(dataset):
    normalizar_run(carga(dataset, [linha(1, 10, "Sim")]))
    nova = carga(dataset, [linha(1, 10, "Não", resultadoVotacao="R", ementa="Ementa corrigida.")])
    resultado = normalizar_run(nova)
    assert (resultado.created, resultado.existing) == (0, 1)
    assert votacao_gravada(1).result == "R"
    assert votacao_gravada(1).summary == "Ementa corrigida."
    assert voto_gravado(1, 10).vote_code == "Não"


def test_votacao_que_saiu_da_janela_continua_no_banco(dataset):
    antiga = carga(dataset, [linha(1, 10), linha(2, 10)])
    normalizar_run(antiga)
    depois = timezone.now() + timedelta(days=1)
    nova = carga(dataset, [linha(2, 10), linha(3, 10)], started_at=depois)
    normalizar_run(nova)
    SenateVoting, SenateVote = modelos()
    assert set(SenateVoting.objects.values_list("session_voting_code", flat=True)) == {1, 2, 3}
    assert SenateVote.objects.count() == 3


def test_voto_que_sumiu_da_carga_nova_continua_no_banco(dataset):
    normalizar_run(carga(dataset, [linha(1, 10), linha(1, 20)]))
    normalizar_run(carga(dataset, [linha(1, 10)]))
    assert modelos()[1].objects.count() == 2


# --- falha fechada -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("coluna", "valor"),
    [
        ("codigoSessaoVotacao", ""),
        ("codigoSessaoVotacao", "abc"),
        ("codigoSessaoVotacao", "-3"),
        ("codigoSessaoVotacao", "99999999999"),
        ("codigoSessaoVotacao", "１２"),
        ("dataSessao", "13/11/2026"),
        ("dataSessao", "2026-02-30"),
        ("dataSessao", ""),
        ("ano", "dois mil"),
        ("votacaoSecreta", "talvez"),
        ("votacaoSecreta", ""),
        ("totalVotosSim", "-1"),
        ("totalVotosNao", "muitos"),
        ("idProcesso", ""),
        ("codigoMateria", "x"),
        ("identificacao", ""),
        ("resultadoVotacao", ""),
        ("codigoParlamentar", ""),
        ("codigoParlamentar", "0"),
        ("nomeParlamentar", ""),
        ("siglaUFParlamentar", "sp"),
        ("siglaUFParlamentar", "SPP"),
        ("siglaVotoParlamentar", ""),
        ("siglaVotoParlamentar", "x" * 41),
        ("nomeParlamentar", "x" * 101),
    ],
)
def test_linha_invalida_recusa_tudo_e_a_mensagem_cita_a_coluna_e_nunca_o_valor(
    dataset, coluna, valor
):
    run = carga(dataset, [linha(1, 10), linha(1, 20, **{coluna: valor}), linha(1, 30)])
    mensagem = recusa(run)
    assert coluna in mensagem
    assert "Nada foi gravado" in mensagem
    assert valor not in mensagem or valor == ""
    SenateVoting, SenateVote = modelos()
    assert SenateVoting.objects.count() == 0
    assert SenateVote.objects.count() == 0


def test_o_mesmo_voto_com_siglas_diferentes_no_bruto_e_conflito(dataset):
    run = carga(dataset, [linha(1, 10, "Sim"), linha(1, 10, "Não")])
    assert "conflitantes" in recusa(run)
    assert modelos()[1].objects.count() == 0


def test_a_mesma_votacao_com_dados_diferentes_entre_linhas_e_conflito(dataset):
    run = carga(dataset, [linha(1, 10), linha(1, 20, ementa="Outra ementa.")])
    assert "conflitantes" in recusa(run)
    assert modelos()[0].objects.count() == 0


def test_mensagem_de_recusa_nao_cita_valores_de_linha(dataset):
    run = carga(dataset, [linha(1, 10, ementa=SEGREDO, siglaUFParlamentar="xx")])
    assert SEGREDO not in recusa(run)


def test_falha_no_meio_nao_deixa_gravacao_parcial(dataset, monkeypatch):
    """A gravação é uma transação só: se o banco recusar no meio, nem a votação fica."""
    run = carga(dataset, [linha(1, 10), linha(2, 10)])
    SenateVote = modelos()[1]
    original = SenateVote.objects.bulk_create

    def quebra(objetos, *args, **kwargs):
        original(objetos[:1], *args, **kwargs)
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(SenateVote.objects, "bulk_create", quebra)
    with pytest.raises(RuntimeError):
        normalizar_run(run)
    assert modelos()[0].objects.count() == 0
    assert SenateVote.objects.count() == 0


# --- encadeamento com o agendador e comando ----------------------------------------------------


def test_normalize_latest_ignora_carga_ja_normalizada(dataset):
    from apps.legislature import senate_voting_normalization as normalizacao

    carga(dataset, [linha(1, 10)])
    primeira = normalizacao.normalize_latest(dataset)
    assert primeira.created == 1
    assert normalizacao.normalize_latest(dataset) is None


def test_normalize_latest_sem_carga_com_linhas_devolve_none(dataset):
    from apps.legislature import senate_voting_normalization as normalizacao

    carga(dataset, [], rows_loaded=0)
    assert normalizacao.normalize_latest(dataset) is None


def test_comando_normaliza_e_resume_so_com_contagens(dataset):
    carga(dataset, [linha(1, 10, ementa=SEGREDO), linha(1, 20)])
    saida = normalizar()
    assert "linhas lidas 2" in saida
    assert "criadas 2" in saida
    assert SEGREDO not in saida


def test_comando_sem_o_conjunto_ou_sem_carga_diz_o_que_falta(db):
    with pytest.raises(CommandError, match="senado/votacoes"):
        normalizar()


def test_comando_sem_carga_manda_rodar_a_coleta(dataset):
    with pytest.raises(CommandError, match="ingest_dataset"):
        normalizar()


def test_comando_repassa_a_recusa_sem_valores(dataset):
    carga(dataset, [linha(1, 10, ementa=SEGREDO, siglaUFParlamentar="xx")])
    with pytest.raises(CommandError) as erro:
        normalizar()
    assert SEGREDO not in str(erro.value)
    assert "siglaUFParlamentar" in str(erro.value)
