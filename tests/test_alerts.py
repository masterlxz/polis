"""Alerta ativo das fontes (Etapa 0, plano da Sessão 76).

`decide` é a regra pura (alerta, lembrete, recuperação ou nada) e `send_pending` junta o que
precisa de aviso numa mensagem só e entrega pelo `sender`. O que mais importa: avisar por MUDANÇA e
não por condição (sem repetir a cada minuto), lembrar 1 vez por dia, avisar a recuperação, e só
gravar que avisou DEPOIS de o envio dar certo (webhook fora do ar não pode perder o aviso). Sem
rede: o `sender` é falso. Dados sintéticos.
"""

from datetime import UTC, datetime, timedelta

import pytest

from apps.sources.freshness import Situation
from apps.sources.models import Dataset, IngestionRun, Source

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
RUIM = ["late", "failed", "normalization_failed"]
NAO_RUIM = ["on_time", "disabled", "no_schedule"]
MENSAGEM_DA_RECUSA = "Normalização recusada: linhas inválidas: 2; colunas: id (2). Nada gravado."


def _decidir(**extra):
    from apps.sources import alerts

    campos = {
        "situation": Situation.LATE,
        "last_alert_situation": "",
        "last_alert_at": None,
        "now": NOW,
        **extra,
    }
    return alerts.decide(**campos)


# --- Regra pura -----------------------------------------------------------------------------------


@pytest.mark.parametrize("valor", RUIM)
def test_situacao_ruim_sem_aviso_anterior_vira_alerta(valor):
    assert _decidir(situation=Situation(valor)) == "alert"


@pytest.mark.parametrize("valor", NAO_RUIM)
def test_situacao_que_nao_e_ruim_e_sem_aviso_aberto_nao_avisa(valor):
    assert _decidir(situation=Situation(valor)) is None


def test_mesma_situacao_ruim_dentro_de_24_horas_nao_repete():
    resultado = _decidir(
        last_alert_situation="late", last_alert_at=NOW - timedelta(hours=23, minutes=59)
    )

    assert resultado is None


def test_mesma_situacao_ruim_com_exatas_24_horas_vira_lembrete():
    resultado = _decidir(last_alert_situation="late", last_alert_at=NOW - timedelta(hours=24))

    assert resultado == "reminder"


def test_mesma_situacao_ruim_com_mais_de_24_horas_vira_lembrete():
    resultado = _decidir(last_alert_situation="late", last_alert_at=NOW - timedelta(days=3))

    assert resultado == "reminder"


def test_outra_situacao_ruim_avisa_na_hora_mesmo_com_aviso_recente():
    resultado = _decidir(
        situation=Situation.FAILED,
        last_alert_situation="late",
        last_alert_at=NOW - timedelta(minutes=1),
    )

    assert resultado == "alert"


@pytest.mark.parametrize("valor", NAO_RUIM)
def test_saiu_do_ruim_com_aviso_aberto_vira_recuperacao(valor):
    resultado = _decidir(
        situation=Situation(valor),
        last_alert_situation="late",
        last_alert_at=NOW - timedelta(hours=2),
    )

    assert resultado == "recovery"


def test_aviso_aberto_sem_data_e_tratado_como_alerta_novo():
    # Estado impossível pelo código, mas o banco aceita: melhor avisar de novo do que calar.
    assert _decidir(last_alert_situation="late", last_alert_at=None) == "alert"


# --- Envio ----------------------------------------------------------------------------------------


class FakeSender:
    def __init__(self, falha=False):
        self.textos = []
        self.falha = falha

    def __call__(self, texto):
        from apps.sources.webhook import WebhookError

        self.textos.append(texto)
        if self.falha:
            raise WebhookError("Falha de rede.")


@pytest.fixture
def fonte(db):
    return Source.objects.create(
        slug="fonte",
        name="Fonte de teste",
        institution="Instituição",
        official_url="https://example.org",
        access_type=Source.AccessType.API,
    )


def _conjunto(fonte, slug, **extra):
    campos = {
        "source": fonte,
        "slug": slug,
        "name": f"Conjunto {slug}",
        "url": f"https://example.org/{slug}.json?token=SEGREDO-NA-URL",
        "format": Dataset.Format.JSON,
        "enabled": True,
        "allowed_columns": ["a"],
        "license_basis": Dataset.LicenseBasis.OWNER_DECISION,
        "license_justification": "Decisão do dono de teste.",
        "schedule_interval_hours": 24,
        **extra,
    }
    return Dataset.objects.create(**campos)


def _sucesso(conjunto, ha_horas):
    fim = NOW - timedelta(hours=ha_horas)
    return IngestionRun.objects.create(
        dataset=conjunto,
        source_url=conjunto.url,
        state=IngestionRun.State.SUCCEEDED,
        sha256_original="a" * 64,
        started_at=fim - timedelta(minutes=1),
        finished_at=fim,
    )


def _atrasado(fonte, slug="atrasado"):
    conjunto = _conjunto(fonte, slug)
    _sucesso(conjunto, ha_horas=100)
    return conjunto


def _em_dia(fonte, slug="em-dia"):
    conjunto = _conjunto(fonte, slug)
    _sucesso(conjunto, ha_horas=1)
    return conjunto


def _enviar(sender, now=NOW):
    from apps.sources import alerts

    return alerts.send_pending(now, sender)


@pytest.mark.django_db
def test_sem_conjunto_ruim_nao_envia_nada(fonte):
    _em_dia(fonte)
    sender = FakeSender()

    resultado = _enviar(sender)

    assert sender.textos == []
    assert resultado.sent == 0
    assert resultado.failed is False


@pytest.mark.django_db
def test_conjunto_atrasado_gera_um_alerta_com_o_nome_e_a_situacao(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender()

    resultado = _enviar(sender)

    assert len(sender.textos) == 1
    assert "ALERTA" in sender.textos[0]
    assert "fonte/atrasado" in sender.textos[0]
    assert "Atrasado" in sender.textos[0]
    assert resultado.sent == 1
    conjunto.refresh_from_db()
    assert conjunto.last_alert_situation == "late"
    assert conjunto.last_alert_at == NOW


@pytest.mark.django_db
def test_na_volta_seguinte_nao_repete_o_aviso(fonte):
    _atrasado(fonte)
    sender = FakeSender()
    _enviar(sender)

    _enviar(sender, now=NOW + timedelta(minutes=1))

    assert len(sender.textos) == 1


@pytest.mark.django_db
def test_depois_de_24_horas_manda_o_lembrete_e_renova_a_data(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender()
    _enviar(sender)
    depois = NOW + timedelta(hours=24)

    _enviar(sender, now=depois)

    assert len(sender.textos) == 2
    assert "LEMBRETE" in sender.textos[1]
    assert "fonte/atrasado" in sender.textos[1]
    conjunto.refresh_from_db()
    assert conjunto.last_alert_at == depois


@pytest.mark.django_db
def test_recuperacao_avisa_e_fecha_o_aviso_aberto(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender()
    _enviar(sender)
    _sucesso(conjunto, ha_horas=0)
    volta = NOW + timedelta(minutes=5)

    _enviar(sender, now=volta)

    assert len(sender.textos) == 2
    assert "RECUPERADO" in sender.textos[1]
    assert "fonte/atrasado" in sender.textos[1]
    conjunto.refresh_from_db()
    assert conjunto.last_alert_situation == ""
    assert conjunto.last_alert_at == volta


@pytest.mark.django_db
def test_depois_de_recuperar_nao_avisa_mais(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender()
    _enviar(sender)
    _sucesso(conjunto, ha_horas=0)
    _enviar(sender, now=NOW + timedelta(minutes=5))

    _enviar(sender, now=NOW + timedelta(minutes=6))

    assert len(sender.textos) == 2


@pytest.mark.django_db
def test_conjunto_desabilitado_depois_de_um_alerta_conta_como_recuperacao(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender()
    _enviar(sender)
    Dataset.objects.filter(pk=conjunto.pk).update(enabled=False)

    _enviar(sender, now=NOW + timedelta(minutes=5))

    assert "RECUPERADO" in sender.textos[1]
    assert "Desabilitado" in sender.textos[1]


@pytest.mark.django_db
def test_conjunto_desabilitado_nunca_gera_alerta(fonte):
    conjunto = _atrasado(fonte)
    Dataset.objects.filter(pk=conjunto.pk).update(enabled=False)
    sender = FakeSender()

    _enviar(sender)

    assert sender.textos == []


@pytest.mark.django_db
def test_varios_conjuntos_ruins_saem_numa_mensagem_so(fonte):
    _atrasado(fonte, "a")
    _atrasado(fonte, "b")
    _atrasado(fonte, "c")
    sender = FakeSender()

    resultado = _enviar(sender)

    assert len(sender.textos) == 1
    assert all(f"fonte/{slug}" in sender.textos[0] for slug in "abc")
    assert resultado.sent == 3


@pytest.mark.django_db
def test_alerta_novo_e_lembrete_vao_juntos_na_mesma_mensagem(fonte):
    _atrasado(fonte, "velho")
    sender = FakeSender()
    _enviar(sender)
    depois = NOW + timedelta(hours=24)
    _atrasado(fonte, "novo")

    _enviar(sender, now=depois)

    assert len(sender.textos) == 2
    assert "LEMBRETE" in sender.textos[1]
    assert "ALERTA" in sender.textos[1]


@pytest.mark.django_db
def test_envio_que_falha_nao_grava_o_estado_e_tenta_de_novo_na_volta_seguinte(fonte):
    conjunto = _atrasado(fonte)
    sender = FakeSender(falha=True)

    resultado = _enviar(sender)

    assert resultado.failed is True
    assert resultado.sent == 0
    conjunto.refresh_from_db()
    assert conjunto.last_alert_situation == ""
    assert conjunto.last_alert_at is None

    sender.falha = False
    _enviar(sender, now=NOW + timedelta(minutes=1))
    assert len(sender.textos) == 2
    conjunto.refresh_from_db()
    assert conjunto.last_alert_situation == "late"


@pytest.mark.django_db
def test_normalizacao_que_falhou_leva_a_mensagem_da_recusa_no_texto(fonte):
    conjunto = _em_dia(fonte)
    Dataset.objects.filter(pk=conjunto.pk).update(last_normalization_error=MENSAGEM_DA_RECUSA)
    sender = FakeSender()

    _enviar(sender)

    assert "Normalização falhou" in sender.textos[0]
    assert MENSAGEM_DA_RECUSA in sender.textos[0]


@pytest.mark.django_db
def test_o_texto_nunca_leva_a_url_do_conjunto(fonte):
    _atrasado(fonte)
    sender = FakeSender()

    _enviar(sender)

    assert "SEGREDO-NA-URL" not in sender.textos[0]
    assert "http" not in sender.textos[0]


# --- Retiradas paradas (carga do TSE recusada) ---------------------------------------------------

FRASE_DAS_RETIRADAS = "Retiradas pedidas pela fonte ficam paradas até a normalização passar."
TSE = "tse/consulta-cand-2026"


@pytest.fixture
def fonte_tse(db):
    return Source.objects.create(
        slug="tse",
        name="Fonte TSE de teste",
        institution="Instituição",
        official_url="https://example.org/tse",
        access_type=Source.AccessType.API,
    )


def _recusar(conjunto):
    Dataset.objects.filter(pk=conjunto.pk).update(last_normalization_error=MENSAGEM_DA_RECUSA)


@pytest.mark.django_db
def test_a_lista_real_tem_o_tse_e_so_chaves_que_tem_normalizador(settings):
    assert TSE in settings.RETIREMENT_DATASETS
    assert set(settings.RETIREMENT_DATASETS) <= set(settings.NORMALIZERS)


@pytest.mark.django_db
def test_tse_com_normalizacao_recusada_avisa_que_as_retiradas_estao_paradas(fonte_tse):
    conjunto = _em_dia(fonte_tse, "consulta-cand-2026")
    _recusar(conjunto)
    sender = FakeSender()

    _enviar(sender)

    assert "ALERTA tse/consulta-cand-2026: Normalização falhou" in sender.textos[0]
    assert MENSAGEM_DA_RECUSA in sender.textos[0]
    assert sender.textos[0].count(FRASE_DAS_RETIRADAS) == 1


@pytest.mark.django_db
def test_o_lembrete_do_tse_leva_a_mesma_frase(fonte_tse):
    conjunto = _em_dia(fonte_tse, "consulta-cand-2026")
    _recusar(conjunto)
    sender = FakeSender()
    _enviar(sender)

    _enviar(sender, now=NOW + timedelta(hours=24))

    assert "LEMBRETE tse/consulta-cand-2026" in sender.textos[1]
    assert sender.textos[1].count(FRASE_DAS_RETIRADAS) == 1


@pytest.mark.django_db
def test_a_frase_vem_da_lista_e_nao_do_nome_do_tse(fonte, fonte_tse, settings):
    settings.RETIREMENT_DATASETS = frozenset({"fonte/com-retirada"})
    _recusar(_em_dia(fonte, "com-retirada"))
    _recusar(_em_dia(fonte_tse, "consulta-cand-2026"))
    sender = FakeSender()

    _enviar(sender)

    linha_da_fonte = next(t for t in sender.textos[0].split("\n") if "fonte/com-retirada" in t)
    linha_do_tse = next(t for t in sender.textos[0].split("\n") if TSE in t)
    assert FRASE_DAS_RETIRADAS in linha_da_fonte
    assert FRASE_DAS_RETIRADAS not in linha_do_tse


@pytest.mark.django_db
def test_lista_vazia_nao_acrescenta_a_frase_nem_ao_tse(fonte_tse, settings):
    settings.RETIREMENT_DATASETS = frozenset()
    _recusar(_em_dia(fonte_tse, "consulta-cand-2026"))
    sender = FakeSender()

    _enviar(sender)

    assert MENSAGEM_DA_RECUSA in sender.textos[0]
    assert FRASE_DAS_RETIRADAS not in sender.textos[0]


@pytest.mark.django_db
def test_mesmo_slug_em_outra_fonte_ou_outro_conjunto_do_tse_nao_leva_a_frase(fonte, fonte_tse):
    _recusar(_em_dia(fonte, "consulta-cand-2026"))
    _recusar(_em_dia(fonte_tse, "outro-conjunto"))
    sender = FakeSender()

    _enviar(sender)

    assert "fonte/consulta-cand-2026" in sender.textos[0]
    assert "tse/outro-conjunto" in sender.textos[0]
    assert FRASE_DAS_RETIRADAS not in sender.textos[0]


@pytest.mark.django_db
def test_tse_atrasado_nao_leva_a_frase(fonte_tse):
    _atrasado(fonte_tse, "consulta-cand-2026")
    sender = FakeSender()

    _enviar(sender)

    assert "ALERTA tse/consulta-cand-2026: Atrasado" in sender.textos[0]
    assert FRASE_DAS_RETIRADAS not in sender.textos[0]


@pytest.mark.django_db
def test_a_recuperacao_do_tse_nao_leva_a_frase(fonte_tse):
    conjunto = _em_dia(fonte_tse, "consulta-cand-2026")
    _recusar(conjunto)
    sender = FakeSender()
    _enviar(sender)
    Dataset.objects.filter(pk=conjunto.pk).update(last_normalization_error="")

    _enviar(sender, now=NOW + timedelta(minutes=5))

    assert FRASE_DAS_RETIRADAS in sender.textos[0]
    assert "RECUPERADO tse/consulta-cand-2026" in sender.textos[1]
    assert FRASE_DAS_RETIRADAS not in sender.textos[1]


@pytest.mark.django_db
def test_com_a_frase_o_texto_continua_sem_url(fonte_tse):
    _recusar(_em_dia(fonte_tse, "consulta-cand-2026"))
    sender = FakeSender()

    _enviar(sender)

    assert FRASE_DAS_RETIRADAS in sender.textos[0]
    assert "SEGREDO-NA-URL" not in sender.textos[0]
    assert "http" not in sender.textos[0]
