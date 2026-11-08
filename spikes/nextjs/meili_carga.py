"""Carrega as 300 mil pessoas sintéticas no Meilisearch (V4). Roda DENTRO do contêiner django-base:
  docker compose exec -T django-base python - < meili_carga.py
Variáveis: MEILI_URL, MEILI_MASTER_KEY, POSTGRES_* (já no ambiente do contêiner)."""

import json
import os
import time
import urllib.request

import psycopg

URL = os.environ["MEILI_URL"]
KEY = os.environ["MEILI_MASTER_KEY"]


def req(method, path, body=None):
    r = urllib.request.Request(
        URL + path,
        method=method,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.load(resp)


def espera(task):
    uid = task["taskUid"]
    while True:
        t = req("GET", f"/tasks/{uid}")
        if t["status"] in ("succeeded", "failed", "canceled"):
            if t["status"] != "succeeded":
                raise SystemExit(f"tarefa {uid}: {t}")
            return t
        time.sleep(1)


espera(req("POST", "/indexes", {"uid": "pessoas", "primaryKey": "id"}))
espera(
    req(
        "PATCH",
        "/indexes/pessoas/settings",
        {"searchableAttributes": ["nome_publico"], "displayedAttributes": ["*"], "filterableAttributes": ["uf", "partido"]},
    )
)

con = psycopg.connect(
    host=os.environ["POSTGRES_HOST"], dbname=os.environ["POSTGRES_DB"],
    user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"],
)
t0 = time.time()
with con.cursor(name="c") as cur:
    cur.itersize = 20000
    cur.execute("SELECT id, nome_publico, cargo, uf, partido, fonte, coletado_em, url_fonte FROM pessoa ORDER BY id")
    lote, ultimo = [], None
    for r in cur:
        lote.append(
            {"id": r[0], "nome_publico": r[1], "cargo": r[2], "uf": r[3], "partido": r[4],
             "fonte": r[5], "coletado_em": r[6].isoformat(), "url_fonte": r[7]}
        )
        if len(lote) == 20000:
            ultimo = req("POST", "/indexes/pessoas/documents", lote)
            lote = []
    if lote:
        ultimo = req("POST", "/indexes/pessoas/documents", lote)
espera(ultimo)
print("indexado em", round(time.time() - t0), "s;", req("GET", "/indexes/pessoas/stats"))
