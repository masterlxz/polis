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
