"""Comandos `normalize_*` da legislatura: estado da última normalização depois do comando à mão.

P-21 (Sessão 87). `Dataset.last_normalization_error` só era escrito pelo agendador, depois de
coleta bem-sucedida; um `normalize_*` à mão que desse certo deixava a recusa antiga no painel
(`normalize_tse` já limpava, Sessão 85). Regra: **só no sucesso** o comando limpa o erro e grava a
hora, nos conjuntos que ele normalizou; recusa e falha inesperada não mexem em nada.

A função `normalize` de cada módulo é trocada por um falso: o que se testa aqui é o que o COMANDO
faz com o estado do conjunto, não a normalização (que os testes de cada módulo já cobrem).
"""

from datetime import timedelta
from importlib import import_module
from io import StringIO
from types import SimpleNamespace

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.sources.models import Dataset, IngestionRun, Source

pytestmark = pytest.mark.django_db

SEGREDO = "SEGREDO-DE-TESTE-NAO-PODE-APARECER"
RECUSA_ANTIGA = "Normalização recusada: linhas inválidas: 2; colunas: id (2). Nada gravado."
RECUSA_DE_OUTRA_FONTE = "Normalização recusada: dados de outra fonte."

# comando -> (módulo que o comando usa, conjuntos que ele normaliza: (fonte, conjunto))
COMANDOS = {
    "normalize_camara": ("apps.legislature.normalization", [("camara", "deputados")]),
    "normalize_senado": ("apps.legislature.senate_normalization", [("senado", "senadores")]),
    "normalize_senado_votacoes": (
        "apps.legislature.senate_voting_normalization",
        [("senado", "votacoes")],
    ),
    "normalize_camara_votacoes": (
        "apps.legislature.camara_voting_normalization",
        [("camara", "votacoes-2026"), ("camara", "votos-2026")],
    ),
    "normalize_camara_proposicoes": (
        "apps.legislature.camara_proposition_normalization",
        [("camara", "votacoes-proposicoes-2026"), ("camara", "votacoes-objetos-2026")],
    ),
}


def criar_conjunto(fonte, slug, **extra):
    return Dataset.objects.create(
        source=fonte,
        slug=slug,
        name=f"Conjunto {slug}",
        url=f"https://example.org/{slug}",
        format=Dataset.Format.JSON,
        allowed_columns=["id"],
        **extra,
    )


def criar_carga(conjunto):
    fim = timezone.now()
    return IngestionRun.objects.create(
        dataset=conjunto,
        source_url=conjunto.url,
        state=IngestionRun.State.SUCCEEDED,
        sha256_original="a" * 64,
        rows_read=1,
        rows_loaded=1,
        finished_at=fim,
    )


@pytest.fixture
def cenario(db):
    """Os conjuntos do comando, cada um com carga e a recusa antiga; mais dois que ele não toca."""
    antes = timezone.now() - timedelta(days=1)

    def montar(comando):
        _, conjuntos = COMANDOS[comando]
        fontes = {}
        normalizados = []
        for slug_fonte, slug in conjuntos:
            if slug_fonte not in fontes:
                fontes[slug_fonte] = Source.objects.create(
                    slug=slug_fonte,
                    name=slug_fonte,
                    institution="Instituição",
                    official_url="https://example.org",
                    access_type=Source.AccessType.DOWNLOAD,
                )
            conjunto = criar_conjunto(fontes[slug_fonte], slug)
            criar_carga(conjunto)
            normalizados.append(conjunto)
        Dataset.objects.filter(pk__in=[c.pk for c in normalizados]).update(
            last_normalization_error=RECUSA_ANTIGA, last_normalization_at=antes
        )
        outra_fonte = Source.objects.create(
            slug="outra",
            name="Outra",
            institution="Instituição",
            official_url="https://example.org",
            access_type=Source.AccessType.DOWNLOAD,
        )
        outro = criar_conjunto(
            outra_fonte, "conjunto", last_normalization_error=RECUSA_DE_OUTRA_FONTE
        )
        # Da MESMA fonte do comando, mas que ele não normaliza: um filtro por fonte o limparia.
        irmao = criar_conjunto(
            fontes[conjuntos[0][0]], "irmao", last_normalization_error=RECUSA_DE_OUTRA_FONTE
        )
        return SimpleNamespace(normalizados=normalizados, outros=[outro, irmao], antes=antes)

    return montar


def estado(conjunto):
    conjunto.refresh_from_db()
    return conjunto.last_normalization_error, conjunto.last_normalization_at


def rodar(comando):
    call_command(comando, stdout=StringIO(), stderr=StringIO())


def resultado_falso(*_runs):
    return SimpleNamespace(
        rows_read=1, unique=1, created=1, existing=0, votings_created=0, links_created=0
    )


@pytest.mark.parametrize("comando", COMANDOS)
def test_normalizar_com_sucesso_limpa_a_recusa_antiga_e_marca_a_hora(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])
    monkeypatch.setattr(modulo, "normalize", resultado_falso)
    c = cenario(comando)
    comando_em = timezone.now()

    rodar(comando)

    for conjunto in c.normalizados:
        erro, hora = estado(conjunto)
        assert erro == ""
        assert hora is not None and hora > c.antes and hora >= comando_em


@pytest.mark.parametrize("comando", COMANDOS)
def test_o_comando_limpa_so_os_conjuntos_que_normalizou(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])
    monkeypatch.setattr(modulo, "normalize", resultado_falso)
    c = cenario(comando)

    rodar(comando)

    for conjunto in c.outros:
        assert estado(conjunto)[0] == RECUSA_DE_OUTRA_FONTE


@pytest.mark.parametrize("comando", COMANDOS)
def test_recusa_do_comando_nao_mexe_no_estado_gravado(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])

    def recusa(*_runs):
        raise modulo.NormalizationRefused("Recusada de teste.")

    monkeypatch.setattr(modulo, "normalize", recusa)
    c = cenario(comando)

    with pytest.raises(CommandError, match="Recusada de teste"):
        rodar(comando)

    for conjunto in c.normalizados:
        assert estado(conjunto) == (RECUSA_ANTIGA, c.antes)


@pytest.mark.parametrize("comando", COMANDOS)
def test_falha_inesperada_do_comando_nao_mexe_no_estado_gravado(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])

    def falha(*_runs):
        raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")

    monkeypatch.setattr(modulo, "normalize", falha)
    c = cenario(comando)

    with pytest.raises(CommandError, match="inesperada") as erro:
        rodar(comando)

    assert SEGREDO not in str(erro.value)
    for conjunto in c.normalizados:
        assert estado(conjunto) == (RECUSA_ANTIGA, c.antes)


@pytest.mark.parametrize("comando", COMANDOS)
def test_falha_inesperada_do_comando_mostra_so_a_classe_da_excecao(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])

    def falha(*_runs):
        raise RuntimeError(f"DETAIL: Failing row contains ({SEGREDO})")

    monkeypatch.setattr(modulo, "normalize", falha)
    cenario(comando)

    with pytest.raises(CommandError) as erro:
        rodar(comando)

    assert str(erro.value) == (
        "A normalização falhou de forma inesperada (RuntimeError); nada foi gravado."
    )


@pytest.mark.parametrize("comando", COMANDOS)
def test_classe_com_nome_que_nao_e_identificador_vira_interrogacao(comando, cenario, monkeypatch):
    modulo = import_module(COMANDOS[comando][0])
    forjada = type("Falsa\nforjada: tudo certo", (Exception,), {})

    def falha(*_runs):
        raise forjada(SEGREDO)

    monkeypatch.setattr(modulo, "normalize", falha)
    cenario(comando)

    with pytest.raises(CommandError) as erro:
        rodar(comando)

    assert str(erro.value) == "A normalização falhou de forma inesperada (?); nada foi gravado."
