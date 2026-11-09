"""Índices da busca de pessoas por nome de urna (ADR 0016).

`f_busca_normaliza` tira acento, põe em minúsculas e troca tudo que não é [a-z0-9] por espaço. A
consulta (`apps/elections/search.py`) aplica a mesma regra em Python, para índice e consulta
tokenizarem igual (o parser do `to_tsvector` sozinho junta `DR.JOAO` num token só).

A função é declarada IMMUTABLE por promessa nossa: o `unaccent` do Postgres é STABLE porque
depende do dicionário, e índice só aceita IMMUTABLE. Aqui o dicionário é fixo (`public.unaccent`).
As extensões ficam instaladas na reversão (podem servir a outros usos); só os objetos nossos saem.
"""

from django.db import migrations

FUNCAO = """
CREATE FUNCTION f_busca_normaliza(texto text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$
    SELECT regexp_replace(lower(public.unaccent('public.unaccent'::regdictionary, texto)),
                          '[^a-z0-9]+', ' ', 'g')
$$
"""

COLUNA = """
ALTER TABLE elections_person
ADD COLUMN public_name_tsv tsvector
GENERATED ALWAYS AS (to_tsvector('simple', f_busca_normaliza(public_name))) STORED
"""


class Migration(migrations.Migration):
    dependencies = [("elections", "0001_initial")]

    operations = [
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS unaccent",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pg_trgm",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(FUNCAO, reverse_sql="DROP FUNCTION f_busca_normaliza(text)"),
        migrations.RunSQL(COLUNA, reverse_sql="ALTER TABLE elections_person DROP COLUMN public_name_tsv"),
        migrations.RunSQL(
            "CREATE INDEX person_name_tsv_gin ON elections_person USING gin (public_name_tsv)",
            reverse_sql="DROP INDEX person_name_tsv_gin",
        ),
        migrations.RunSQL(
            "CREATE INDEX person_name_trgm ON elections_person "
            "USING gin (f_busca_normaliza(public_name) gin_trgm_ops)",
            reverse_sql="DROP INDEX person_name_trgm",
        ),
    ]
