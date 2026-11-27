"""Deputado da Câmara, normalizado a partir do bruto de `camara/deputados` (ADR 0009, 0021, 0022).

Fica fora de `Person` de propósito: a identidade de `Person` é "ciclo + SQ_CANDIDATO do TSE", e
ligar um deputado a uma pessoa do TSE precisa de revisão humana (outra fatia). A chave é a
legislatura e o id da Câmara. Dentro da legislatura, a troca de partido sobrescreve a linha
(histórico de partido é fatia futura), e quem some da lista continua aqui: `ingestion_run` guarda
a última execução que o viu, `in_office` fica falso e `left_list_at` guarda o início da primeira
execução sem ele (ADR 0027). Quem volta à lista volta a `in_office`.
"""

from django.db import models

from apps.sources.models import IngestionRun


class Deputy(models.Model):
    """Deputado da lista em exercício da Câmara numa legislatura (nome parlamentar, não o civil)."""

    legislature_id = models.PositiveIntegerField("legislatura")
    camara_id = models.PositiveIntegerField("id na Câmara")
    name = models.CharField("nome parlamentar", max_length=100)
    party_acronym = models.CharField("sigla do partido", max_length=20, blank=True)
    state = models.CharField("UF", max_length=2)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="deputies",
        verbose_name="última execução de coleta que o viu",
    )
    in_office = models.BooleanField(
        "em exercício",
        default=True,
        help_text=(
            "Falso: não consta mais na lista de deputados em exercício da Câmara. A lista não "
            "diz o motivo (licença, fim de mandato, renúncia, morte, suplente assumindo)."
        ),
    )
    left_list_at = models.DateTimeField(
        "saiu da lista em",
        null=True,
        blank=True,
        help_text=(
            "Início da primeira execução de coleta que não o trouxe: a data da COLETA, não a do "
            "fim do mandato. Vazio enquanto está na lista."
        ),
    )

    class Meta:
        verbose_name = "deputado"
        verbose_name_plural = "deputados"
        constraints = [
            models.UniqueConstraint(
                fields=["legislature_id", "camara_id"], name="deputy_unique_legislature_camara_id"
            ),
            models.CheckConstraint(condition=~models.Q(name=""), name="deputy_name"),
        ]

    def __str__(self):
        return self.name


class Senator(models.Model):
    """Senador da lista em exercício do Senado (nome parlamentar, não o civil; ADR 0028).

    Fora de `Person` e de `Deputy`, pelo mesmo motivo do ADR 0022. A chave é só o código do
    parlamentar: o mandato de senador atravessa duas legislaturas. As regras de `in_office` e
    `left_list_at` são as do `Deputy` (ADR 0027): a data é a da COLETA, não a do fim do mandato.
    """

    senate_id = models.PositiveIntegerField("código no Senado")
    name = models.CharField("nome parlamentar", max_length=100)
    party_acronym = models.CharField("sigla do partido", max_length=20, blank=True)
    state = models.CharField("UF", max_length=2)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="senators",
        verbose_name="última execução de coleta que o viu",
    )
    in_office = models.BooleanField(
        "em exercício",
        default=True,
        help_text=(
            "Falso: não consta mais na lista de senadores em exercício do Senado. A lista não "
            "diz o motivo (licença, fim de mandato, renúncia, morte, titular de volta)."
        ),
    )
    left_list_at = models.DateTimeField(
        "saiu da lista em",
        null=True,
        blank=True,
        help_text=(
            "Início da primeira execução de coleta que não o trouxe: a data da COLETA, não a do "
            "fim do mandato. Vazio enquanto está na lista."
        ),
    )

    class Meta:
        verbose_name = "senador"
        verbose_name_plural = "senadores"
        constraints = [
            models.UniqueConstraint(fields=["senate_id"], name="senator_unique_senate_id"),
            models.CheckConstraint(condition=~models.Q(name=""), name="senator_name"),
        ]

    def __str__(self):
        return self.name


class SenateVoting(models.Model):
    """Votação do Senado, com a marca de votação secreta (ADR 0029).

    A chave é o código da votação no Senado (`codigoSessaoVotacao`, único em 87 de 87 medidas). A
    tabela só acumula: votação que sai da janela de coleta continua aqui. Os totais vêm da fonte,
    nulos nas votações abertas (calculam-se dos votos); nas secretas são o único resultado.
    """

    session_voting_code = models.PositiveIntegerField("código da votação no Senado")
    voted_on = models.DateField("data da sessão")
    type_acronym = models.CharField("sigla do tipo", max_length=20)
    number = models.CharField("número", max_length=20)
    year = models.PositiveSmallIntegerField("ano")
    identification = models.CharField("identificação", max_length=60)
    summary = models.TextField("ementa", blank=True)
    result = models.CharField("resultado", max_length=10)
    secret = models.BooleanField(
        "votação secreta",
        help_text="Verdadeiro: o conteúdo do voto não é divulgado; 'Votou' só diz que votou.",
    )
    total_yes = models.PositiveIntegerField("total de votos sim", null=True, blank=True)
    total_no = models.PositiveIntegerField("total de votos não", null=True, blank=True)
    total_abstention = models.PositiveIntegerField("total de abstenções", null=True, blank=True)
    process_id = models.PositiveIntegerField("código do processo")
    matter_id = models.PositiveIntegerField("código da matéria")
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="senate_votings",
        verbose_name="última execução de coleta que a viu",
    )

    class Meta:
        verbose_name = "votação do Senado"
        verbose_name_plural = "votações do Senado"
        constraints = [
            models.UniqueConstraint(
                fields=["session_voting_code"], name="senate_voting_unique_code"
            ),
        ]

    def __str__(self):
        return f"{self.identification} ({self.voted_on})"


class SenateVote(models.Model):
    """Voto de um parlamentar numa votação do Senado (ADR 0029).

    Sem chave para `Senator`: quem votou e saiu da lista de exercício não está lá, e uma chave
    recusaria a carga. Guarda o nome, o partido e a UF do momento do voto (o partido da data, não o
    de hoje); a junção com `Senator` é por código, na leitura. A sigla do voto vem da fonte, sem
    mapeamento (o significado de AP, LS, P-NRV e outras não foi verificado).
    """

    voting = models.ForeignKey(
        SenateVoting, on_delete=models.PROTECT, related_name="votes", verbose_name="votação"
    )
    senate_id = models.PositiveIntegerField("código do parlamentar no Senado")
    name = models.CharField("nome parlamentar", max_length=100)
    party_acronym = models.CharField("sigla do partido", max_length=20, blank=True)
    state = models.CharField("UF", max_length=2)
    vote_code = models.CharField("sigla do voto", max_length=40)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="senate_votes",
        verbose_name="última execução de coleta que o viu",
    )

    class Meta:
        verbose_name = "voto no Senado"
        verbose_name_plural = "votos no Senado"
        constraints = [
            models.UniqueConstraint(
                fields=["voting", "senate_id"], name="senate_vote_unique_per_voting"
            ),
        ]

    def __str__(self):
        return f"{self.name}: {self.vote_code}"


class CamaraVoting(models.Model):
    """Votação da Câmara, dos arquivos anuais em massa (ADR 0031).

    A chave é o id da votação em TEXTO (`2641546-7`); a tabela só acumula. Os totais vêm da fonte e
    não são calculados: só 1,9% das votações têm voto nominal, as outras só têm os totais. Só a
    data fica no modelo: os horários da fonte não dizem o fuso e ficam na camada bruta. `approval`
    e `proposition_id` ficam como vêm (`aprovacao` é `1`, `0` ou vazio, de significado não
    verificado; a proposição é `0` quando a fonte não indica nenhuma).
    """

    camara_voting_id = models.CharField("id da votação na Câmara", max_length=20)
    voted_on = models.DateField("data da votação")
    organ_acronym = models.CharField("sigla do órgão", max_length=20)
    approval = models.CharField("aprovação", max_length=1, blank=True)
    total_yes = models.PositiveIntegerField("votos sim")
    total_no = models.PositiveIntegerField("votos não")
    total_other = models.PositiveIntegerField("outros votos")
    description = models.TextField("descrição", blank=True)
    proposition_id = models.PositiveIntegerField("id da proposição")
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="camara_votings",
        verbose_name="última execução de coleta que a viu",
    )

    class Meta:
        verbose_name = "votação da Câmara"
        verbose_name_plural = "votações da Câmara"
        constraints = [
            models.UniqueConstraint(fields=["camara_voting_id"], name="camara_voting_unique_id"),
        ]

    def __str__(self):
        return f"{self.camara_voting_id} ({self.voted_on})"


class CamaraVote(models.Model):
    """Voto de um deputado numa votação da Câmara (ADR 0031).

    Sem chave para `Deputy`: guarda o id, a legislatura e o partido do momento do voto, e a junção
    é por (legislatura, id) na leitura, como no Senado (ADR 0029). Nome, uri, UF e foto do deputado
    nunca entram (ADR 0005). `vote` vem da fonte sem mapeamento e pode ser vazio: a votação
    `2645346-18` tem 466 votos sem posição registrada, e vazio é "sem posição", nunca um voto.
    """

    voting = models.ForeignKey(
        CamaraVoting, on_delete=models.PROTECT, related_name="votes", verbose_name="votação"
    )
    camara_id = models.PositiveIntegerField("id do deputado na Câmara")
    legislature_id = models.PositiveIntegerField("legislatura")
    party_acronym = models.CharField("sigla do partido", max_length=20, blank=True)
    vote = models.CharField("voto", max_length=40, blank=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="camara_votes",
        verbose_name="última execução de coleta que o viu",
    )

    class Meta:
        verbose_name = "voto na Câmara"
        verbose_name_plural = "votos na Câmara"
        constraints = [
            models.UniqueConstraint(
                fields=["voting", "camara_id"], name="camara_vote_unique_per_voting"
            ),
        ]
        # A unique acima começa por `voting` e não serve ao histórico de um deputado, que filtra
        # por (legislatura, id da Câmara).
        indexes = [
            models.Index(fields=["legislature_id", "camara_id"], name="camara_vote_leg_camara_idx"),
        ]

    def __str__(self):
        return f"{self.camara_id}: {self.vote or 'sem posição'}"


class CamaraProposition(models.Model):
    """Proposição que uma votação da Câmara tem como objeto, dos arquivos anuais em massa
    `votacoesProposicoes` e `votacoesObjetos` (Rodada 4 de `fontes/camara.md`).

    A chave é o id da proposição. `year` é nulo quando a fonte não o informa (32.899 linhas de
    `votacoesObjetos`); `ementa` pode ser vazia (404 proposições medidas). O texto vem da fonte
    com quebra de linha e TAB trocados por espaço; a página futura deve escapá-lo.
    """

    camara_id = models.PositiveIntegerField("id da proposição na Câmara")
    title = models.CharField("título", max_length=100)
    type_acronym = models.CharField("sigla do tipo", max_length=10)
    number = models.PositiveIntegerField("número")
    year = models.PositiveIntegerField("ano", null=True, blank=True)
    ementa = models.TextField("ementa", blank=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="camara_propositions",
        verbose_name="última execução de coleta que a viu",
    )

    class Meta:
        verbose_name = "proposição da Câmara"
        verbose_name_plural = "proposições da Câmara"
        constraints = [
            models.UniqueConstraint(fields=["camara_id"], name="camara_proposition_unique_id"),
        ]

    def __str__(self):
        return self.title


class CamaraVotingProposition(models.Model):
    """Ligação entre uma votação da Câmara e uma proposição dela.

    Sem chave para `CamaraVoting`: guarda o id da votação em texto e a junção é na leitura (como
    `CamaraVote` com `Deputy`, ADR 0029 e 0031), então a normalização não espera a votação nem
    corre contra a coleta dela. `origin` diz de qual arquivo veio a ligação ("proposicoes" ou
    "objetos"); o significado de cada um não foi verificado, e os dois não repetem nenhum par
    (votação, proposição) na medição de 2026-11-26.
    """

    camara_voting_id = models.CharField("id da votação na Câmara", max_length=20)
    proposition = models.ForeignKey(
        CamaraProposition,
        on_delete=models.PROTECT,
        related_name="voting_links",
        verbose_name="proposição",
    )
    origin = models.CharField("arquivo de origem", max_length=20)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="camara_voting_propositions",
        verbose_name="última execução de coleta que a viu",
    )

    class Meta:
        verbose_name = "proposição de votação da Câmara"
        verbose_name_plural = "proposições de votações da Câmara"
        constraints = [
            models.UniqueConstraint(
                fields=["camara_voting_id", "proposition"],
                name="camara_voting_proposition_unique",
            ),
        ]

    def __str__(self):
        return f"{self.camara_voting_id}: {self.proposition_id}"


class CamaraPropositionStep(models.Model):
    """Tramitação de uma proposição da Câmara, do arquivo anual em massa
    `proposicoesTramitacoes` (ADR 0034, Rodada 5 de `fontes/camara.md`).

    Sem chave para `CamaraProposition`: a maioria das proposições do arquivo (cerca de 36 mil de
    46 mil) não existe lá, então o id fica em texto e a junção é na leitura. `idTramitacao` não é
    lido (400 valores em 118.724 linhas) e `despacho` não é ingerido (cita agentes públicos).

    A chave é (proposição, `sequence`, `occurred_at`, `organ_code`, `description`): sem a
    `sequence` perderiam-se 1.290 linhas em 2026, e só com ela e a proposição há 13 eventos
    diferentes no mesmo par. `sequence` é nula quando a fonte a deixa vazia (1 linha em 2026), e a
    unicidade trata NULL como igual (`nulls_distinct=False`), senão essa linha duplicaria a cada
    carga. `occurred_at` vem sem fuso na fonte e é gravado como horário de Brasília (não
    verificado).
    """

    camara_proposition_id = models.CharField("id da proposição na Câmara", max_length=10)
    sequence = models.PositiveIntegerField("sequência", null=True, blank=True)
    occurred_at = models.DateTimeField("data e hora")
    organ_code = models.CharField("sigla do órgão", max_length=30)
    description = models.CharField("descrição da tramitação", max_length=200)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="camara_proposition_steps",
        verbose_name="última execução de coleta que a viu",
    )

    class Meta:
        verbose_name = "tramitação de proposição da Câmara"
        verbose_name_plural = "tramitações de proposições da Câmara"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "camara_proposition_id",
                    "sequence",
                    "occurred_at",
                    "organ_code",
                    "description",
                ],
                name="camara_proposition_step_unique",
                nulls_distinct=False,
            ),
        ]

    def __str__(self):
        return f"{self.camara_proposition_id}: {self.description}"
