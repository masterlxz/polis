"""Semeia pessoas e candidaturas SINTÉTICAS para a medição de carga da busca (ADR 0010, 0016).

Uso (no CI, ver `.github/workflows/carga-busca.yml`):
`python scripts/carga_busca/semear.py N consultas.txt`.
Cria N pessoas com nome de urna sintético em caixa alta (vocabulário pequeno de propósito, como no
spike do ADR 0016: homônimos são muitos), uma candidatura por pessoa, atualiza as estatísticas do
planner e exporta 3.000 nomes sorteados para o gerador de carga. Nenhum dado real.
"""

import os
import sys
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from apps.elections.models import Election  # noqa: E402
from apps.sources.models import Dataset, IngestionRun, Source  # noqa: E402

NOMES = (
    "João,José,Antônio,Francisco,Carlos,Paulo,Pedro,Lucas,Luiz,Marcos,Luís,Gabriel,Rafael,"
    "Daniel,Marcelo,Bruno,Eduardo,Felipe,Raimundo,Rodrigo,Maria,Ana,Francisca,Antônia,Adriana,"
    "Juliana,Márcia,Fernanda,Patrícia,Aline,Sandra,Camila,Amanda,Bruna,Jéssica,Letícia,Júlia,"
    "Luciana,Vanessa,Mariana,Cláudia,Simone,Rita,Sônia,Raquel,Teresa,Beatriz,Helena,Lúcia,Rosa"
).split(",")
SOBRENOMES = (
    "Silva,Santos,Oliveira,Souza,Rodrigues,Ferreira,Alves,Pereira,Lima,Gomes,Costa,Ribeiro,"
    "Martins,Carvalho,Almeida,Lopes,Soares,Fernandes,Vieira,Barbosa,Rocha,Dias,Nascimento,"
    "Andrade,Moreira,Nunes,Marques,Machado,Mendes,Freitas,Cardoso,Ramos,Gonçalves,Santana,"
    "Teixeira,Azevedo,Tavares,Fonseca,Cunha,Araújo,Pinto,Moura,Correia,Campos,Monteiro,Melo,"
    "Batista,Farias,Borges,Duarte,Castro,Miranda,Barros,Pires,Medeiros,Moraes,Reis,Cavalcanti,"
    "Leite,Coelho"
).split(",")
UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()
PARTIDOS = [f"P{i:02d}" for i in range(20)]

SILABAS = (
    "ba be bi bo bu ca ce ci co cu da de di do du fa fe fi fo ga ge gi go la le li lo lu "
    "ma me mi mo mu na ne ni no nu pa pe pi po ra re ri ro ru sa se si so ta te ti to va ve vi vo"
).split()


def _sorteia(lista, tamanho):
    return f"(%({lista})s::text[])[1 + floor(random() * %({tamanho})s)::int]"


# Palavra rara: 2 ou 3 sílabas sorteadas (~100 mil palavras possíveis). A mistura de palavras
# comuns (da lista) com raras dá homonímia bem menor que a do primeiro teste (3 mil combinações
# para 3 milhões de pessoas), mais perto dos nomes reais (maior grupo medido: 6 em 21 mil).
_RARA = (
    f"{_sorteia('sil', 'nsil')} || {_sorteia('sil', 'nsil')} || "
    f"CASE WHEN random() < 0.5 THEN {_sorteia('sil', 'nsil')} ELSE '' END"
)
_PRIMEIRO = f"CASE WHEN random() < 0.7 THEN {_sorteia('nomes', 'nn')} ELSE {_RARA} END"
_SOBRENOME = f"CASE WHEN random() < 0.5 THEN {_sorteia('sobre', 'ns')} ELSE {_RARA} END"

PESSOAS = (
    "INSERT INTO elections_person (cycle_year, tse_candidate_id, public_name, social_name) "  # noqa: S608
    f"SELECT 2026, g, upper({_PRIMEIRO} || ' ' || {_SOBRENOME} || "
    f"CASE WHEN random() < 0.5 THEN ' ' || {_SOBRENOME} ELSE '' END), '' "
    "FROM generate_series(1, %(n)s) AS g"
)  # fragmentos são constantes do arquivo; só `n` e as listas viajam como parâmetro

HOMONIMIA = """
SELECT count(*), count(DISTINCT public_name), max(c) FROM (
    SELECT public_name, count(*) OVER (PARTITION BY public_name) AS c FROM elections_person
) t
"""

CANDIDATURAS = """
INSERT INTO elections_candidacy (
    election_id, person_id, ballot_number, office_code, office_name, scope, state,
    electoral_unit_code, electoral_unit_name, party_number, party_acronym, party_name,
    federation_acronym, federation_name, coalition_name, coalition_composition,
    status_code, status_name, result_code, result_name, ingestion_run_id, source_generated_at)
SELECT %(eleicao)s, p.id, 10000 + (p.id %% 90000), 6, 'DEPUTADO FEDERAL', 'ESTADUAL',
       (%(ufs)s::text[])[1 + (p.id %% %(nu)s)], (%(ufs)s::text[])[1 + (p.id %% %(nu)s)],
       'UNIDADE DE TESTE', 12, (%(partidos)s::text[])[1 + (p.id %% %(np)s)], 'Partido de Teste',
       '', '', '', '', NULL, '', NULL, '', %(run)s, now()
FROM elections_person p
"""


def main(total, caminho_consultas):
    fonte = Source.objects.create(
        slug="carga",
        name="Carga sintética",
        institution="Teste de carga",
        official_url="https://example.org",
        access_type=Source.AccessType.DOWNLOAD,
    )
    conjunto = Dataset.objects.create(
        source=fonte,
        slug="carga-sintetica",
        name="Carga sintética",
        url="https://example.org/carga.zip",
        format=Dataset.Format.ZIP_CSV,
        license_basis=Dataset.LicenseBasis.DECLARED,
        license_id="cc-by",
        license_url="https://example.org/licencas/cc-by",
    )
    execucao = IngestionRun.objects.create(dataset=conjunto, source_url=conjunto.url)
    eleicao = Election.objects.create(
        tse_code=1,
        round=1,
        year=2026,
        kind_code=2,
        kind_name="Eleição Ordinária",
        description="Eleições sintéticas 2026",
        date=date(2026, 10, 4),
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT setseed(0.42)")
        cursor.execute(
            PESSOAS,
            {
                "nomes": NOMES,
                "nn": len(NOMES),
                "sobre": SOBRENOMES,
                "ns": len(SOBRENOMES),
                "sil": SILABAS,
                "nsil": len(SILABAS),
                "n": total,
            },
        )
        cursor.execute(
            CANDIDATURAS,
            {
                "eleicao": eleicao.id,
                "run": execucao.id,
                "ufs": UFS,
                "nu": len(UFS),
                "partidos": PARTIDOS,
                "np": len(PARTIDOS),
            },
        )
        cursor.execute("ANALYZE elections_person")
        cursor.execute("ANALYZE elections_candidacy")
        cursor.execute("SELECT public_name FROM elections_person ORDER BY random() LIMIT 3000")
        nomes = [linha[0] for linha in cursor.fetchall()]
        cursor.execute(HOMONIMIA)
        pessoas, distintos, maior_grupo = cursor.fetchone()
    with open(caminho_consultas, "w", encoding="utf-8") as saida:
        saida.write("\n".join(nomes) + "\n")
    print(
        f"semeadas {pessoas} pessoas, {distintos} nomes distintos, maior grupo de homônimos "
        f"{maior_grupo}; {len(nomes)} nomes exportados para {caminho_consultas}"
    )


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2])
