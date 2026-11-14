"""Situação de um conjunto de dados (monitoramento da Etapa 0; plano da Sessão 74).

Função pura: recebe o estado do conjunto e o relógio (`now`) e devolve uma de cinco situações. O que
mais importa são os limites (exatamente 2 intervalos sem coleta, 1 minuto a mais) e a ordem das
regras: desabilitado e sem agenda vêm antes de qualquer outra coisa; falha da última coleta vem
antes de "atrasado"; "nunca coletou" só vira atraso quando a próxima coleta venceu há mais de 2
intervalos. Sem banco, sem rede.
"""

from datetime import UTC, datetime, timedelta

import pytest

from apps.sources.freshness import LATE_FACTOR, Situation, situation

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
INTERVALO = 24


def _situacao(**extra):
    campos = {
        "enabled": True,
        "interval_hours": INTERVALO,
        "next_collection_at": NOW + timedelta(hours=1),
        "last_success_at": NOW - timedelta(hours=1),
        "last_finished_state": "succeeded",
        "normalization_failed": False,
        "now": NOW,
        **extra,
    }
    return situation(**campos)


def test_o_fator_e_dois_intervalos():
    assert LATE_FACTOR == 2


def test_coleta_recente_com_sucesso_esta_em_dia():
    assert _situacao() is Situation.ON_TIME


def test_desabilitado_vence_qualquer_outra_regra():
    resultado = _situacao(
        enabled=False,
        last_finished_state="failed",
        last_success_at=NOW - timedelta(days=30),
    )

    assert resultado is Situation.DISABLED


def test_sem_intervalo_e_sem_agenda_mesmo_com_coleta_velha_ou_falha():
    resultado = _situacao(
        interval_hours=None,
        last_finished_state="failed",
        last_success_at=NOW - timedelta(days=30),
    )

    assert resultado is Situation.NO_SCHEDULE


def test_ultima_coleta_que_falhou_aparece_mesmo_com_sucesso_recente():
    assert _situacao(last_finished_state="failed") is Situation.FAILED


def test_normalizacao_que_falhou_aparece_mesmo_com_a_coleta_em_dia():
    assert _situacao(normalization_failed=True) is Situation.NORMALIZATION_FAILED


def test_normalizacao_que_falhou_vence_o_atraso():
    velha = NOW - timedelta(days=10)

    resultado = _situacao(normalization_failed=True, last_success_at=velha)

    assert resultado is Situation.NORMALIZATION_FAILED


def test_coleta_que_falhou_vence_a_normalizacao_que_falhou():
    resultado = _situacao(normalization_failed=True, last_finished_state="failed")

    assert resultado is Situation.FAILED


def test_desabilitado_e_sem_agenda_vencem_a_normalizacao_que_falhou():
    assert _situacao(normalization_failed=True, enabled=False) is Situation.DISABLED
    assert _situacao(normalization_failed=True, interval_hours=None) is Situation.NO_SCHEDULE


def test_normalizacao_que_falhou_vale_tambem_para_quem_nunca_teve_sucesso():
    nunca_coletou = {"last_success_at": None, "last_finished_state": None}

    resultado = _situacao(normalization_failed=True, **nunca_coletou)

    assert resultado is Situation.NORMALIZATION_FAILED


def test_falha_antes_de_um_sucesso_nao_conta():
    # A última execução concluída foi um sucesso: a falha de antes não pesa.
    assert _situacao(last_finished_state="succeeded") is Situation.ON_TIME


def test_falha_com_sucesso_velho_continua_sendo_falha_nao_atraso():
    resultado = _situacao(last_finished_state="failed", last_success_at=NOW - timedelta(days=10))

    assert resultado is Situation.FAILED


def test_exatamente_dois_intervalos_sem_coleta_ainda_esta_em_dia():
    limite = NOW - timedelta(hours=LATE_FACTOR * INTERVALO)

    assert _situacao(last_success_at=limite) is Situation.ON_TIME


def test_um_minuto_alem_de_dois_intervalos_esta_atrasado():
    passou = NOW - timedelta(hours=LATE_FACTOR * INTERVALO, minutes=1)

    assert _situacao(last_success_at=passou) is Situation.LATE


def test_o_limite_acompanha_o_intervalo_do_conjunto():
    # 30 horas sem coleta: atrasado para quem coleta de hora em hora, em dia para quem coleta a
    # cada 24.
    sem_coleta = NOW - timedelta(hours=30)

    assert _situacao(interval_hours=1, last_success_at=sem_coleta) is Situation.LATE
    assert _situacao(interval_hours=24, last_success_at=sem_coleta) is Situation.ON_TIME


def test_nunca_coletou_com_a_proxima_no_futuro_esta_em_dia():
    resultado = _situacao(
        last_success_at=None, last_finished_state=None, next_collection_at=NOW + timedelta(hours=1)
    )

    assert resultado is Situation.ON_TIME


def test_nunca_coletou_e_nunca_armado_esta_em_dia():
    # Recém-habilitado: o agendador ainda vai sortear a primeira data.
    resultado = _situacao(last_success_at=None, last_finished_state=None, next_collection_at=None)

    assert resultado is Situation.ON_TIME


def test_nunca_coletou_com_a_proxima_vencida_ha_mais_de_dois_intervalos_esta_atrasado():
    vencida = NOW - timedelta(hours=LATE_FACTOR * INTERVALO, minutes=1)

    resultado = _situacao(
        last_success_at=None, last_finished_state=None, next_collection_at=vencida
    )

    assert resultado is Situation.LATE


def test_nunca_coletou_com_a_proxima_vencida_ha_exatos_dois_intervalos_esta_em_dia():
    vencida = NOW - timedelta(hours=LATE_FACTOR * INTERVALO)

    resultado = _situacao(
        last_success_at=None, last_finished_state=None, next_collection_at=vencida
    )

    assert resultado is Situation.ON_TIME


def test_so_falhas_sem_nenhum_sucesso_aparece_como_falha():
    resultado = _situacao(last_success_at=None, last_finished_state="failed")

    assert resultado is Situation.FAILED


@pytest.mark.parametrize(
    ("valor", "rotulo"),
    [
        ("on_time", "Em dia"),
        ("late", "Atrasado"),
        ("failed", "Última coleta falhou"),
        ("normalization_failed", "Normalização falhou"),
        ("no_schedule", "Sem agenda"),
        ("disabled", "Desabilitado"),
    ],
)
def test_cada_situacao_tem_o_rotulo_em_portugues(valor, rotulo):
    assert Situation(valor).label == rotulo
