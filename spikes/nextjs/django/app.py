"""Spike do Next.js (ADR 0015, decisão 3). Dados 100% sintéticos; NÃO é código de produto.

Um único módulo Django que serve, sobre a MESMA consulta ao banco:
  - HTML renderizado por template: /perfil/<id>/ e /busca/?q=   (pilha BASE)
  - JSON interno:                  /api/perfil/<id>/ e /api/busca/?q= (pilha ALVO, consumida pelo Next.js)
"""

import json
import os
import re
import threading
import time
import unicodedata
import urllib.request

import psycopg
from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.urls import path

settings.configure(
    DEBUG=False,
    SECRET_KEY=os.environ["DJANGO_SECRET_KEY"],
    ALLOWED_HOSTS=["*"],
    ROOT_URLCONF=__name__,
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [os.path.join(os.path.dirname(__file__), "templates")],
        }
    ],
)

_local = threading.local()


def conn():
    c = getattr(_local, "c", None)
    if c is None or c.closed:
        c = psycopg.connect(
            host=os.environ["POSTGRES_HOST"],
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            autocommit=True,
        )
        _local.c = c
    return c


COLS = "id, nome_publico, cargo, uf, partido, fonte, coletado_em, url_fonte"
KEYS = [c.strip() for c in COLS.split(",")]


def _row(r):
    d = dict(zip(KEYS, r))
    d["coletado_em"] = d["coletado_em"].isoformat()
    return d


def get_perfil(pid):
    with conn().cursor() as cur:
        cur.execute(f"SELECT {COLS} FROM pessoa WHERE id = %s", (pid,))
        r = cur.fetchone()
    if r is None:
        raise Http404
    return _row(r)


def _sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _trgm(q, limiar, word=False):
    """V0/V1: trigramas. V0 = % com limiar 0,3; V1 = % com 0,5; V1w = <% (word_similarity) com 0,5."""
    with conn().cursor() as cur:
        if word:
            cur.execute("SELECT set_config('pg_trgm.word_similarity_threshold', %s, false)", (str(limiar),))
            cur.execute(
                f"SELECT {COLS} FROM pessoa WHERE f_unaccent(%s) <%% f_unaccent(nome_publico) "
                "ORDER BY word_similarity(f_unaccent(%s), f_unaccent(nome_publico)) DESC, "
                "similarity(f_unaccent(nome_publico), f_unaccent(%s)) DESC LIMIT 20",
                (q, q, q),
            )
        else:
            cur.execute("SELECT set_config('pg_trgm.similarity_threshold', %s, false)", (str(limiar),))
            cur.execute(
                f"SELECT {COLS} FROM pessoa WHERE f_unaccent(nome_publico) %% f_unaccent(%s) "
                "ORDER BY similarity(f_unaccent(nome_publico), f_unaccent(%s)) DESC LIMIT 20",
                (q, q),
            )
        return [_row(r) for r in cur.fetchall()]


def _tokens(q):
    """V2: palavras (ou prefixos) exatas via tsvector 'simple'; trigramas só como reserva."""
    toks = re.findall(r"[a-z0-9]+", _sem_acento(q).lower())
    if toks:
        tsq = " & ".join(f"{t}:*" for t in toks)
        with conn().cursor() as cur:
            cur.execute(
                f"SELECT {COLS} FROM pessoa WHERE nome_tsv @@ to_tsquery('simple', %s) "
                "ORDER BY (lower(f_unaccent(nome_publico)) = %s) DESC, length(nome_publico), id LIMIT 20",
                (tsq, " ".join(toks)),
            )
            itens = [_row(r) for r in cur.fetchall()]
        if len(itens) >= 5:
            return itens
    return _trgm(q, 0.5)


def _meili(q):
    """V4: busca dedicada (Meilisearch, edição comunitária)."""
    req = urllib.request.Request(
        f"{os.environ['MEILI_URL']}/indexes/pessoas/search",
        data=json.dumps({"q": q, "limit": 20}).encode(),
        headers={"Authorization": f"Bearer {os.environ['MEILI_MASTER_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["hits"]


_cache = {}
_CACHE_TTL = 60.0
_CACHE_MAX = 5000


def do_busca(q, v="V0", cache=False):
    if not q:
        return []
    if cache:
        hit = _cache.get((v, q))
        if hit and time.monotonic() - hit[0] < _CACHE_TTL:
            return hit[1]
    if v == "V0":
        itens = _trgm(q, 0.3)
    elif v == "V1":
        itens = _trgm(q, 0.5)
    elif v == "V1w":
        itens = _trgm(q, 0.5, word=True)
    elif v == "V2":
        itens = _tokens(q)
    elif v == "V4":
        itens = _meili(q)
    else:
        raise Http404
    if cache:
        if len(_cache) >= _CACHE_MAX:
            _cache.clear()
        _cache[(v, q)] = (time.monotonic(), itens)
    return itens


def perfil_html(request, pid):
    return render(request, "perfil.html", {"p": get_perfil(pid)})


def busca_html(request):
    q = request.GET.get("q", "")
    itens = do_busca(q, request.GET.get("v", "V0"), request.GET.get("c") == "1")
    return render(request, "busca.html", {"q": q, "itens": itens})


def perfil_json(request, pid):
    return JsonResponse(get_perfil(pid))


def busca_json(request):
    itens = do_busca(request.GET.get("q", ""), request.GET.get("v", "V0"), request.GET.get("c") == "1")
    return JsonResponse({"itens": itens})


def saude(request):
    with conn().cursor() as cur:
        cur.execute("SELECT 1")
    return JsonResponse({"ok": True})


urlpatterns = [
    path("perfil/<int:pid>/", perfil_html),
    path("busca/", busca_html),
    path("api/perfil/<int:pid>/", perfil_json),
    path("api/busca/", busca_json),
    path("saude/", saude),
]

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
