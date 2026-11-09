"""Eleição, pessoa e candidatura, normalizadas a partir do bruto do TSE (ADR 0009, fatia 1).

Medido em `consulta-cand-2026` (Sessão 39): a candidatura é única por eleição+turno e
`SQ_CANDIDATO`; o mesmo `SQ_CANDIDATO` aparece nos dois turnos do ciclo, então a pessoa é única
por ciclo e `SQ_CANDIDATO`. Ligar pessoas de ciclos diferentes não é feito aqui (não verificado,
precisa de ADR próprio). O nome social é interno: nunca vai para `str()`, listas nem exibição.
"""

from django.db import models

from apps.sources.models import IngestionRun


class Election(models.Model):
    """Uma eleição de um turno (`CD_ELEICAO` + `NR_TURNO`)."""

    tse_code = models.PositiveIntegerField("código da eleição no TSE")
    round = models.PositiveSmallIntegerField("turno")
    year = models.PositiveSmallIntegerField("ano")
    kind_code = models.PositiveSmallIntegerField("código do tipo")
    kind_name = models.CharField("tipo", max_length=60)
    description = models.CharField("descrição", max_length=120)
    date = models.DateField("data da eleição")

    class Meta:
        verbose_name = "eleição"
        verbose_name_plural = "eleições"
        constraints = [
            models.UniqueConstraint(fields=["tse_code", "round"], name="election_unique_code_round")
        ]

    def __str__(self):
        return f"{self.description} ({self.round}º turno)"


class Person(models.Model):
    """Pessoa que concorreu num ciclo eleitoral, identificada pelo `SQ_CANDIDATO` do TSE."""

    cycle_year = models.PositiveSmallIntegerField("ano do ciclo eleitoral")
    tse_candidate_id = models.PositiveBigIntegerField("SQ_CANDIDATO do TSE")
    public_name = models.CharField("nome público (nome de urna)", max_length=100)
    social_name = models.CharField("nome social (interno)", max_length=100, blank=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        constraints = [
            models.UniqueConstraint(
                fields=["cycle_year", "tse_candidate_id"], name="person_unique_cycle_candidate"
            ),
            models.CheckConstraint(condition=~models.Q(public_name=""), name="person_public_name"),
        ]

    def __str__(self):
        return self.public_name


class Candidacy(models.Model):
    """Candidatura de uma pessoa numa eleição, com a origem da linha (PRD §4)."""

    election = models.ForeignKey(
        Election,
        on_delete=models.PROTECT,
        related_name="candidacies",
        verbose_name="eleição",
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="candidacies",
        verbose_name="pessoa",
    )
    ballot_number = models.PositiveIntegerField("número de urna")
    office_code = models.PositiveSmallIntegerField("código do cargo")
    office_name = models.CharField("cargo", max_length=60)
    scope = models.CharField("abrangência", max_length=20)
    state = models.CharField("UF", max_length=2)
    electoral_unit_code = models.CharField("código da unidade eleitoral", max_length=10)
    electoral_unit_name = models.CharField("unidade eleitoral", max_length=60)
    party_number = models.PositiveSmallIntegerField("número do partido")
    party_acronym = models.CharField("sigla do partido", max_length=20)
    party_name = models.CharField("partido", max_length=100)
    federation_acronym = models.CharField("sigla da federação", max_length=40, blank=True)
    federation_name = models.CharField("federação", max_length=100, blank=True)
    coalition_name = models.CharField("coligação", max_length=150, blank=True)
    coalition_composition = models.TextField("composição da coligação", blank=True)
    status_code = models.SmallIntegerField(
        "código da situação da candidatura", null=True, blank=True
    )
    status_name = models.CharField("situação da candidatura", max_length=60, blank=True)
    result_code = models.SmallIntegerField("código do resultado", null=True, blank=True)
    result_name = models.CharField("resultado", max_length=60, blank=True)
    ingestion_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="candidacies",
        verbose_name="execução de coleta de origem",
    )
    source_generated_at = models.DateTimeField("gerado pela fonte em")

    class Meta:
        verbose_name = "candidatura"
        verbose_name_plural = "candidaturas"
        constraints = [
            models.UniqueConstraint(
                fields=["election", "person"], name="candidacy_unique_election_person"
            )
        ]

    def __str__(self):
        return f"{self.person} ({self.office_name}, {self.state})"
