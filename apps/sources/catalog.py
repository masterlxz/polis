"""Definições do cadastro inicial de fontes e conjuntos (aplicadas por `seed_sources`).

Revisadas em PR: a allowlist é a decisão de dado pessoal do ADR 0005 e não muda por baixo dos
panos. Fontes nascem `measured` e conjuntos `enabled=False`; ligar a integração e habilitar o
conjunto é decisão do dono, no admin, antes da primeira requisição real (ADR 0008).

Allowlist de `consulta_cand_2026` (TSE): 34 das 50 colunas medidas (`project/fontes/tse.md`).
Ficam de fora: CPF, título de eleitor e e-mail (decisão 1), cor/raça, gênero, grau de instrução,
estado civil e ocupação (decisão 4), e o nome civil, a data e a UF de nascimento, que ainda não
têm uso (sem ligação entre fontes; ver a decisão 2). Incluí-los depois é trocar esta lista e
recarregar o arquivo. Nenhuma coluna interna por enquanto.
"""

SOURCES = [
    {
        "slug": "tse",
        "name": "TSE: Portal de Dados Abertos",
        "institution": "Tribunal Superior Eleitoral",
        "official_url": "https://dadosabertos.tse.jus.br",
        "access_type": "download",
        "terms_url": "https://dadosabertos.tse.jus.br/about",
        "license_note": (
            "CC BY declarada por conjunto no CKAN (metadado license_id); os 9 conjuntos do portal "
            "sem licença não são coletados (ADR 0008, decisão 1). Portaria TSE 93/2021: dados "
            "abertos sob licença aberta, com atribuição como única condição. Uso comercial e "
            "redistribuição: P-16."
        ),
    },
    {
        "slug": "camara",
        "name": "Câmara dos Deputados: Dados Abertos",
        "institution": "Câmara dos Deputados",
        "official_url": "https://dadosabertos.camara.leg.br",
        "access_type": "api",
        "terms_url": "https://www2.camara.leg.br/termo-de-uso-e-politica-de-privacidade",
        "license_note": (
            "Sem licença nem atribuição declaradas (portal, FAQ e Ato da Mesa 45/2012). O Art. 27 "
            "do Ato limita informações pessoais, incluindo documentos de identificação. Coleta "
            "só por decisão registrada do dono (ADR 0008, decisão 1)."
        ),
    },
    {
        "slug": "senado",
        "name": "Senado Federal: Dados Abertos",
        "institution": "Senado Federal",
        "official_url": "https://legis.senado.leg.br/dadosabertos",
        "access_type": "api",
        "terms_url": (
            "https://www12.senado.leg.br/institucional/documentos/"
            "politica-de-uso-do-portal-do-senado-federal"
        ),
        "license_note": (
            "A política de uso do portal pede citar a fonte; a especificação da API não declara "
            "licença nem termos. Uso comercial não declarado e não presumido (ADR 0008, decisões "
            "3 e 9). Coleta só por decisão registrada do dono."
        ),
    },
]

DATASETS = [
    {
        "source": "tse",
        "slug": "consulta-cand-2026",
        "name": "Consulta de candidatos 2026",
        "url": (
            "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip"
        ),
        "format": "zip_csv",
        "allowed_columns": [
            "DT_GERACAO",
            "HH_GERACAO",
            "ANO_ELEICAO",
            "CD_TIPO_ELEICAO",
            "NM_TIPO_ELEICAO",
            "NR_TURNO",
            "CD_ELEICAO",
            "DS_ELEICAO",
            "DT_ELEICAO",
            "TP_ABRANGENCIA",
            "SG_UF",
            "SG_UE",
            "NM_UE",
            "CD_CARGO",
            "DS_CARGO",
            "SQ_CANDIDATO",
            "NR_CANDIDATO",
            "NM_URNA_CANDIDATO",
            "NM_SOCIAL_CANDIDATO",
            "CD_SITUACAO_CANDIDATURA",
            "DS_SITUACAO_CANDIDATURA",
            "TP_AGREMIACAO",
            "NR_PARTIDO",
            "SG_PARTIDO",
            "NM_PARTIDO",
            "NR_FEDERACAO",
            "NM_FEDERACAO",
            "SG_FEDERACAO",
            "DS_COMPOSICAO_FEDERACAO",
            "SQ_COLIGACAO",
            "NM_COLIGACAO",
            "DS_COMPOSICAO_COLIGACAO",
            "CD_SIT_TOT_TURNO",
            "DS_SIT_TOT_TURNO",
        ],
        "internal_columns": [],
        "license_basis": "declared",
        "license_id": "cc-by",
        "license_url": "http://www.opendefinition.org/licenses/cc-by",
        "license_check_url": (
            "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2026"
        ),
        # Agendamento (ADR 0008, decisão 6): uma vez por dia; o SHA-256 evita recarga inútil.
        "schedule_interval_hours": 24,
        "earliest_hour_utc": 0,
    },
    {
        # Lista dos deputados em exercício (legislatura atual), pela API paginada. Sem licença
        # declarada: a base é a decisão do dono (ADR 0008, decisão 1; ADR 0021). O cadastro
        # nunca habilita nem copia a justificativa: o dono faz isso no admin, com o texto do ADR.
        # Fora da allowlist e descartados na leitura: `email`, `urlFoto` e `uriPartido`; nunca
        # `cpf`, nome civil nem data de nascimento (ADR 0005).
        "source": "camara",
        "slug": "deputados",
        "name": "Deputados em exercício (legislatura atual)",
        "url": "https://dadosabertos.camara.leg.br/api/v2/deputados?itens=100&ordem=ASC&ordenarPor=id",
        "format": "json",
        "allowed_columns": ["id", "uri", "nome", "siglaPartido", "siglaUf", "idLegislatura"],
        "internal_columns": [],
        "license_basis": "owner_decision",
        "license_id": "",
        "license_url": "",
        "license_check_url": "",
        # Agendamento: uma vez por dia, só depois das 08:00 GMT (regeneração de madrugada).
        "schedule_interval_hours": 24,
        "earliest_hour_utc": 8,
    },
    {
        # Lista dos senadores em exercício: uma resposta só, aninhada (ADR 0028). Sem licença
        # declarada: a base é a decisão do dono, feita no admin com o texto do ADR. Da
        # `IdentificacaoParlamentar` só 4 campos; ficam de fora e são descartados na leitura o nome
        # completo (civil), e-mail, telefones, foto, suplentes e mandato (ADR 0005). O sufixo
        # `.json` escolhe o formato (o cliente não envia `Accept`).
        "source": "senado",
        "slug": "senadores",
        "name": "Senadores em exercício",
        "url": "https://legis.senado.leg.br/dadosabertos/senador/lista/atual.json",
        "format": "json_senado",
        "allowed_columns": [
            "CodigoParlamentar",
            "NomeParlamentar",
            "SiglaPartidoParlamentar",
            "UfParlamentar",
        ],
        "internal_columns": [],
        "license_basis": "owner_decision",
        "license_id": "",
        "license_url": "",
        "license_check_url": "",
        # Uma vez por dia, depois das 08:00 GMT; a política do Senado pede fugir de horários
        # redondos de pico (a coleta é 1 requisição por dia).
        "schedule_interval_hours": 24,
        "earliest_hour_utc": 8,
    },
]
