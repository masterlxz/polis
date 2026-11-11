"""Deputado da Câmara, normalizado a partir do bruto de `camara/deputados` (ADR 0009, 0021, 0022).

Fica fora de `Person` de propósito: a identidade de `Person` é "ciclo + SQ_CANDIDATO do TSE", e
ligar um deputado a uma pessoa do TSE precisa de revisão humana (outra fatia). A chave é a
legislatura e o id da Câmara. Dentro da legislatura, a troca de partido sobrescreve a linha
(histórico de partido é fatia futura), e quem some da lista continua aqui: `ingestion_run` guarda
a última execução que o viu.
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
