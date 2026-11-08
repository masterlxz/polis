"""Spike do Next.js (ADR 0015, decisão 3). Dados 100% sintéticos; NÃO é código de produto.

Um único módulo Django que serve, sobre a MESMA consulta ao banco:
  - HTML renderizado por template: /perfil/<id>/ e /busca/?q=   (pilha BASE)
  - JSON interno:                  /api/perfil/<id>/ e /api/busca/?q= (pilha ALVO, consumida pelo Next.js)
"""

import os
import threading

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


def do_busca(q):
    if not q:
        return []
    with conn().cursor() as cur:
        cur.execute(
            f"SELECT {COLS} FROM pessoa WHERE f_unaccent(nome_publico) %% f_unaccent(%s) "
            "ORDER BY similarity(f_unaccent(nome_publico), f_unaccent(%s)) DESC LIMIT 20",
            (q, q),
        )
        return [_row(r) for r in cur.fetchall()]


def perfil_html(request, pid):
    return render(request, "perfil.html", {"p": get_perfil(pid)})


def busca_html(request):
    q = request.GET.get("q", "")
    return render(request, "busca.html", {"q": q, "itens": do_busca(q)})


def perfil_json(request, pid):
    return JsonResponse(get_perfil(pid))


def busca_json(request):
    return JsonResponse({"itens": do_busca(request.GET.get("q", ""))})


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
