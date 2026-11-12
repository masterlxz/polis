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
