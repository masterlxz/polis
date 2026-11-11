"""Agendador da coleta (`collect_due`; ADR 0008 decisão 6, plano da Sessão 57).

O `ingest` é falso: nenhum teste faz rede. O que se prova é a decisão (quem está vencido, quando
é a próxima, o que acontece nas falhas) e não a coleta em si, que já tem os seus testes.
Relógio e sorteio entram por parâmetro (`now`, `rng`).
"""

import socket
from datetime import UTC, datetime, timedelta
from io import StringIO
from random import Random

import pytest
from django.core.management import CommandError, call_command
from django.db import IntegrityError, transaction

from apps.sources.ingestion import IngestionError
from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 11, 11, 9, 17, 42, tzinfo=UTC)
HASH = "a" * 64


@pytest.fixture
def agendador():
    from apps.sources import scheduling

    return scheduling


class FakeIngest:
    """Imita `ingest()`: recusa fonte pausada como o portão real e cria a execução combinada."""

    def __init__(self):
        self.calls = []
        self.modos = {}
        self.ao_chamar = None

    def __call__(self, dataset, client):
        self.calls.append((dataset.slug, client))
        dataset.source.refresh_from_db(fields=["status"])
        if dataset.source.status == Source.Status.PAUSED:
            raise ValueError("A fonte está pausada.")
        modo = self.modos.get(dataset.slug, "ok")
        if modo == "gate":
            raise ValueError("O conjunto não está habilitado.")
        if modo == "unexpected":
            raise IngestionError("falha inesperada")
        if self.ao_chamar is not None:
            gancho, self.ao_chamar = self.ao_chamar, None  # uso único: sem recursão
            gancho()
        if modo == "ok":
            return IngestionRun.objects.create(
                dataset=dataset,
                source_url=dataset.url,
                state=IngestionRun.State.SUCCEEDED,
                finished_at=NOW,
                sha256_original=HASH,
            )
        code = IngestionRun.ErrorCode.BLOCKED if modo == "blocked" else "download"
        if modo == "blocked":
            dataset.source.status = Source.Status.PAUSED
            dataset.source.save(update_fields=["status"])
        return IngestionRun.objects.create(
            dataset=dataset,
            source_url=dataset.url,
            state=IngestionRun.State.FAILED,
            error_code=code,
            finished_at=NOW,
        )


@pytest.fixture
def ingest(agendador, monkeypatch):
    falso = FakeIngest()
    monkeypatch.setattr(agendador, "ingest", falso)
    return falso


def make_source(slug="camara", status=Source.Status.ACTIVE):
    return Source.objects.create(
        slug=slug,
        name=slug.upper(),
        institution="Instituição",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
        status=status,
    )


def make_dataset(
    fonte=None,
    slug="deputados",
    interval=24,
    earliest=0,
    next_at="vencido",
    enabled=True,
):
    fonte = fonte or make_source()
    proximo = NOW - timedelta(minutes=1) if next_at == "vencido" else next_at
    return Dataset.objects.create(
        source=fonte,
        slug=slug,
        name=slug,
        url=f"https://example.org/{slug}",
        format=Dataset.Format.JSON,
        allowed_columns=["id"],
        license_basis=Dataset.LicenseBasis.DECLARED,
        license_id="cc-by",
        enabled=enabled,
        schedule_interval_hours=interval,
        earliest_hour_utc=earliest,
        next_collection_at=proximo,
    )


def coletar(agendador, now=NOW, client=None):
    return agendador.collect_due(client or object(), now=now, rng=Random(7))


def minuto_permitido(momento):
    return 1 <= momento.minute <= 59 and momento.minute % 5 != 0


# --- Quem coleta e quando ---


def test_conjunto_vencido_e_dentro_da_janela_coleta_uma_vez_e_agenda_a_proxima(agendador, ingest):
    dataset = make_dataset()

    coletar(agendador)

    assert [slug for slug, _ in ingest.calls] == ["deputados"]
    dataset.refresh_from_db()
    proxima = dataset.next_collection_at
    assert proxima.date() == (NOW + timedelta(hours=24)).date()
    assert proxima.hour == NOW.hour
    assert minuto_permitido(proxima)


def test_proxima_no_futuro_nao_coleta_e_nao_muda(agendador, ingest):
    futuro = NOW + timedelta(hours=1)
    dataset = make_dataset(next_at=futuro)

    coletar(agendador)

    assert ingest.calls == []
    dataset.refresh_from_db()
    assert dataset.next_collection_at == futuro


@pytest.mark.parametrize(
    "preparar",
    [
        lambda: make_dataset(interval=None),
        lambda: make_dataset(enabled=False),
        lambda: make_dataset(fonte=make_source(status=Source.Status.PAUSED)),
        lambda: make_dataset(fonte=make_source(status=Source.Status.MEASURED)),
    ],
    ids=["sem_intervalo", "desabilitado", "fonte_pausada", "fonte_sem_integracao"],
)
def test_conjunto_fora_do_agendamento_nao_coleta_nem_arma(agendador, ingest, preparar):
    dataset = preparar()
    dataset.next_collection_at = None
    dataset.save(update_fields=["next_collection_at"])

    coletar(agendador)

    assert ingest.calls == []
    dataset.refresh_from_db()
    assert dataset.next_collection_at is None


def test_conjunto_nunca_armado_e_armado_sem_coletar(agendador, ingest):
    dataset = make_dataset(next_at=None)

    coletar(agendador)

    assert ingest.calls == []
    dataset.refresh_from_db()
    assert NOW < dataset.next_collection_at <= NOW + timedelta(hours=2)
    assert minuto_permitido(dataset.next_collection_at)


def test_antes_da_janela_nao_coleta_mesmo_vencido(agendador, ingest):
    cedo = datetime(2026, 11, 11, 7, 30, tzinfo=UTC)
    vencido = cedo - timedelta(minutes=5)
    dataset = make_dataset(earliest=8, next_at=vencido)

    coletar(agendador, now=cedo)

    assert ingest.calls == []
    dataset.refresh_from_db()
    assert dataset.next_collection_at == vencido


def test_dentro_da_janela_coleta_no_mesmo_dia(agendador, ingest):
    na_janela = datetime(2026, 11, 11, 8, 41, tzinfo=UTC)
    make_dataset(earliest=8, next_at=na_janela - timedelta(minutes=5))

    coletar(agendador, now=na_janela)

    assert len(ingest.calls) == 1


@pytest.mark.parametrize("hora_local", [3, 7, 23])
def test_ao_armar_a_proxima_nunca_cai_antes_da_janela(agendador, ingest, hora_local):
    agora = datetime(2026, 11, 11, hora_local, 10, tzinfo=UTC)
    dataset = make_dataset(earliest=8, next_at=None)

    coletar(agendador, now=agora)

    dataset.refresh_from_db()
    assert dataset.next_collection_at > agora
    assert dataset.next_collection_at.hour >= 8
    assert minuto_permitido(dataset.next_collection_at)


# --- O sorteio ---


def test_500_sorteios_nunca_caem_em_minuto_redondo_e_mantem_a_hora(agendador):
    rng = Random(11)
    for _ in range(500):
        proxima = agendador.draw_next(NOW, 24, 0, rng)
        assert minuto_permitido(proxima)
        assert proxima.hour == NOW.hour
        assert proxima.date() == (NOW + timedelta(hours=24)).date()


def test_sorteio_com_hora_antes_da_janela_sobe_para_a_hora_da_janela(agendador):
    proxima = agendador.draw_next(NOW, 1, 12, Random(3))  # agora + 1 h = 10h, janela 12h

    assert proxima.hour == 12
    assert proxima.date() == NOW.date()
    assert minuto_permitido(proxima)


# --- Depois da coleta ---


def test_execucao_que_falhou_tenta_de_novo_em_6_horas_e_nao_em_24(agendador, ingest):
    ingest.modos["deputados"] = "failed"
    dataset = make_dataset()

    coletar(agendador)

    dataset.refresh_from_db()
    assert NOW + timedelta(hours=5) < dataset.next_collection_at < NOW + timedelta(hours=7)
    assert minuto_permitido(dataset.next_collection_at)


def test_bloqueio_pausa_a_fonte_e_o_outro_conjunto_dela_nao_derruba_o_comando(agendador, ingest):
    fonte = make_source()
    primeiro = make_dataset(fonte=fonte, slug="a-primeiro")
    segundo = make_dataset(fonte=fonte, slug="b-segundo")
    ingest.modos["a-primeiro"] = "blocked"

    resultado = coletar(agendador)

    assert resultado.unexpected == 0
    assert [slug for slug, _ in ingest.calls] == ["a-primeiro", "b-segundo"]
    fonte.refresh_from_db()
    assert fonte.status == Source.Status.PAUSED
    assert IngestionRun.objects.get(dataset=primeiro).error_code == "blocked"
    segundo.refresh_from_db()
    assert NOW + timedelta(hours=5) < segundo.next_collection_at < NOW + timedelta(hours=7)


def test_portao_que_recusa_nao_derruba_e_tenta_de_novo_em_6_horas(agendador, ingest):
    ingest.modos["deputados"] = "gate"
    dataset = make_dataset()

    resultado = coletar(agendador)

    assert resultado.unexpected == 0
    dataset.refresh_from_db()
    assert NOW + timedelta(hours=5) < dataset.next_collection_at < NOW + timedelta(hours=7)


def test_erro_inesperado_num_conjunto_nao_impede_o_proximo(agendador, ingest):
    fonte = make_source()
    ruim = make_dataset(fonte=fonte, slug="a-ruim")
    bom = make_dataset(fonte=fonte, slug="b-bom")
    ingest.modos["a-ruim"] = "unexpected"

    resultado = coletar(agendador)

    assert resultado.unexpected == 1
    assert [slug for slug, _ in ingest.calls] == ["a-ruim", "b-bom"]
    ruim.refresh_from_db()
    assert NOW + timedelta(hours=5) < ruim.next_collection_at < NOW + timedelta(hours=7)
    bom.refresh_from_db()
    assert bom.next_collection_at.date() == (NOW + timedelta(hours=24)).date()


# --- Concorrência e cliente ---


def test_segunda_invocacao_durante_a_coleta_nao_coleta_de_novo(agendador, ingest):
    make_dataset()
    ingest.ao_chamar = lambda: coletar(agendador)  # outro cron do minuto seguinte entra aqui

    coletar(agendador)

    assert len(ingest.calls) == 1


def test_a_reserva_so_vale_para_quem_leu_o_valor_atual(agendador):
    dataset = make_dataset()
    lido = dataset.next_collection_at
    depois = NOW + timedelta(hours=6)

    primeiro = agendador._claim(dataset.pk, lido, depois)
    segundo = agendador._claim(dataset.pk, lido, depois)

    assert (primeiro, segundo) == (True, False)


def test_um_unico_cliente_http_serve_todos_os_conjuntos(agendador, ingest):
    make_dataset(fonte=make_source("camara"), slug="a")
    make_dataset(fonte=make_source("tse"), slug="b")
    cliente = object()

    coletar(agendador, client=cliente)

    assert len(ingest.calls) == 2
    assert all(usado is cliente for _, usado in ingest.calls)


# --- O comando ---


@pytest.fixture
def comando(agendador, ingest, monkeypatch):
    from apps.sources.management.commands import collect_due

    monkeypatch.setattr(collect_due, "PoliteClient", lambda: object())
    return collect_due


def rodar_comando():
    saida = StringIO()
    call_command("collect_due", stdout=saida)
    return saida.getvalue()


def test_sem_nada_vencido_o_comando_diz_e_nao_coleta(comando, ingest):
    assert "nada vencido" in rodar_comando()
    assert ingest.calls == []


def test_a_saida_traz_o_conjunto_e_o_estado_mas_nenhum_endereco(comando, ingest):
    make_dataset()

    saida = rodar_comando()

    assert "camara/deputados" in saida
    assert "succeeded" in saida
    assert "http" not in saida


def test_erro_inesperado_faz_o_comando_terminar_com_erro_depois_de_seguir(comando, ingest):
    fonte = make_source()
    make_dataset(fonte=fonte, slug="a-ruim")
    make_dataset(fonte=fonte, slug="b-bom")
    ingest.modos["a-ruim"] = "unexpected"

    with pytest.raises(CommandError, match="inesperad"):
        rodar_comando()

    assert [slug for slug, _ in ingest.calls] == ["a-ruim", "b-bom"]


def test_o_comando_nao_abre_conexao_de_rede_por_conta_propria(comando, ingest, monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("o comando tentou usar a rede")

    monkeypatch.setattr(socket.socket, "connect", proibido)
    monkeypatch.setattr(socket, "create_connection", proibido)
    make_dataset()

    rodar_comando()

    assert len(ingest.calls) == 1


# --- Cadastro e modelo ---


def test_seed_cadastra_tse_e_camara_com_24_horas_e_a_janela_da_camara():
    call_command("seed_sources", stdout=StringIO())

    tse = Dataset.objects.get(source__slug="tse", slug="consulta-cand-2026")
    camara = Dataset.objects.get(source__slug="camara", slug="deputados")
    assert (tse.schedule_interval_hours, tse.earliest_hour_utc) == (24, 0)
    assert (camara.schedule_interval_hours, camara.earliest_hour_utc) == (24, 8)
    assert tse.next_collection_at is None
    assert camara.next_collection_at is None


def test_seed_nao_sobrescreve_o_agendamento_que_o_dono_mudou():
    call_command("seed_sources", stdout=StringIO())
    camara = Dataset.objects.get(source__slug="camara", slug="deputados")
    camara.schedule_interval_hours = 12
    camara.earliest_hour_utc = 10
    camara.next_collection_at = NOW
    camara.save()

    call_command("seed_sources", stdout=StringIO())

    camara.refresh_from_db()
    assert (camara.schedule_interval_hours, camara.earliest_hour_utc) == (12, 10)
    assert camara.next_collection_at == NOW


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("schedule_interval_hours", 0), ("earliest_hour_utc", 24)],
    ids=["intervalo_zero", "hora_24"],
)
def test_o_banco_barra_intervalo_zero_e_hora_fora_de_0_a_23(campo, valor):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_dataset(**{"interval" if campo == "schedule_interval_hours" else "earliest": valor})
