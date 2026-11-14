"""Cadastro de fontes e registro de execuções de coleta.

Regras de dados pessoais (ADR 0005): nenhuma fonte entra sem allowlist de colunas
declarada no conjunto; a execução guarda só nomes de colunas, contagens e o
SHA-256 do arquivo original, nunca valores de linha nem texto livre de erro.
"""

from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

SHA256_HEX_REGEX = r"^[0-9a-f]{64}$"


class Source(models.Model):
    """Instituição ou portal que publica dados (PRD §8.1)."""

    class AccessType(models.TextChoices):
        API = "api", "API"
        DOWNLOAD = "download", "Download"
        PAGE = "page", "Página"
        FILE = "file", "Arquivo"
        OTHER = "other", "Outro"

    class Status(models.TextChoices):
        MEASURED = "measured", "Medida, sem integração"
        INTEGRATING = "integrating", "Em integração"
        ACTIVE = "active", "Ativa"
        PAUSED = "paused", "Pausada"

    slug = models.SlugField("identificador", max_length=50, unique=True)
    name = models.CharField("nome", max_length=200)
    institution = models.CharField("instituição responsável", max_length=200)
    official_url = models.URLField("endereço oficial", max_length=500)
    access_type = models.CharField("tipo de acesso", max_length=20, choices=AccessType)
    terms_url = models.URLField("termos de uso", max_length=500, blank=True)
    license_note = models.TextField("licença e restrições", blank=True)
    status = models.CharField(
        "estado da integração", max_length=20, choices=Status, default=Status.MEASURED
    )
    notes = models.TextField("observações", blank=True)

    class Meta:
        verbose_name = "fonte"
        verbose_name_plural = "fontes"
        ordering = ["slug"]

    def __str__(self):
        return self.name


class Dataset(models.Model):
    """Um arquivo ou endpoint de uma fonte, com a allowlist de colunas (ADR 0005)."""

    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        ZIP_CSV = "zip_csv", "ZIP com CSV"
        JSON = "json", "JSON"
        JSON_SENADO = "json_senado", "JSON do Senado"
        JSON_SENADO_VOTACOES = "json_senado_votacoes", "JSON das votações do Senado"
        XML = "xml", "XML"
        OTHER = "other", "Outro"

    class LicenseBasis(models.TextChoices):
        NONE = "none", "Sem licença"
        DECLARED = "declared", "Declarada pela fonte"
        OWNER_DECISION = "owner_decision", "Decisão do dono"

    source = models.ForeignKey(
        Source, on_delete=models.PROTECT, related_name="datasets", verbose_name="fonte"
    )
    slug = models.SlugField("identificador", max_length=100)
    name = models.CharField("nome", max_length=200)
    url = models.URLField("endereço", max_length=500)
    format = models.CharField("formato", max_length=20, choices=Format)
    allowed_columns = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name="colunas permitidas",
        help_text="Allowlist: só estas colunas são lidas; o resto é descartado na leitura.",
    )
    internal_columns = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name="colunas internas",
        help_text="Subconjunto das permitidas que nunca é exposto (interface e API).",
    )
    license_basis = models.CharField(
        "base da licença",
        max_length=20,
        choices=LicenseBasis,
        default=LicenseBasis.NONE,
        help_text="Licença é do conjunto, não da fonte (ADR 0008, decisão 1).",
    )
    license_id = models.CharField(
        "identificador da licença",
        max_length=100,
        blank=True,
        help_text="Como a fonte declara (por exemplo, o license_id do CKAN do TSE).",
    )
    license_url = models.URLField("endereço da licença", max_length=500, blank=True)
    license_check_url = models.URLField(
        "endereço da checagem de licença",
        max_length=500,
        blank=True,
        help_text=(
            "Pacote do CKAN que declara a licença do conjunto (package_show). Vazio: sem "
            "checagem. Antes de cada carga, a licença de lá precisa ser a registrada aqui "
            "(ADR 0008, decisão 2)."
        ),
    )
    license_justification = models.TextField(
        "justificativa do dono",
        blank=True,
        help_text="Obrigatória na decisão do dono: por que coletar sem licença declarada.",
    )
    enabled = models.BooleanField(
        "habilitado",
        default=False,
        help_text="Só pode ser habilitado com colunas permitidas e base de licença.",
    )
    schedule_interval_hours = models.PositiveSmallIntegerField(
        "intervalo da coleta (horas)",
        null=True,
        blank=True,
        help_text="Vazio: o agendador não coleta este conjunto (ADR 0008, decisão 6).",
    )
    earliest_hour_utc = models.PositiveSmallIntegerField(
        "hora mínima da coleta (UTC)",
        default=0,
        help_text="O agendador só coleta a partir desta hora (0 a 23, UTC).",
    )
    next_collection_at = models.DateTimeField(
        "próxima coleta",
        null=True,
        blank=True,
        help_text=(
            "Vazio: o agendador sorteia na próxima passada. Para forçar uma coleta, ponha "
            "uma data e hora já passadas."
        ),
    )
    last_normalization_at = models.DateTimeField(
        "última normalização tentada em",
        null=True,
        blank=True,
        help_text="Escrito pelo agendador depois de cada coleta; vazio se nunca normalizou.",
    )
    last_normalization_error = models.CharField(
        "erro da última normalização",
        max_length=300,
        blank=True,
        help_text=(
            "Vazio: a última normalização deu certo. Recusa mostra a mensagem do contrato (só "
            "colunas e contagens); falha inesperada mostra um texto fixo."
        ),
    )

    class Meta:
        verbose_name = "conjunto de dados"
        verbose_name_plural = "conjuntos de dados"
        ordering = ["source__slug", "slug"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "slug"], name="dataset_unique_slug_per_source"
            ),
            models.CheckConstraint(
                condition=Q(enabled=False) | Q(allowed_columns__len__gt=0),
                name="dataset_enabled_requires_allowed_columns",
            ),
            models.CheckConstraint(
                condition=Q(enabled=False)
                | (Q(license_basis="declared") & ~Q(license_id=""))
                | (Q(license_basis="owner_decision") & ~Q(license_justification="")),
                name="dataset_enabled_requires_license_basis",
            ),
            models.CheckConstraint(
                condition=(
                    Q(schedule_interval_hours__isnull=True) | Q(schedule_interval_hours__gte=1)
                ),
                name="dataset_schedule_interval_positive",
            ),
            models.CheckConstraint(
                condition=Q(earliest_hour_utc__lte=23),
                name="dataset_earliest_hour_utc_range",
            ),
        ]

    def __str__(self):
        return f"{self.source.slug}/{self.slug}"

    def clean(self):
        super().clean()
        fora = sorted(set(self.internal_columns) - set(self.allowed_columns))
        if fora:
            raise ValidationError(
                {"internal_columns": f"Colunas internas fora das permitidas: {', '.join(fora)}."}
            )
        if self.enabled:
            self._clean_license()

    def _clean_license(self):
        if self.license_basis == self.LicenseBasis.DECLARED and not self.license_id.strip():
            raise ValidationError(
                {"license_id": "Licença declarada pela fonte exige o identificador da licença."}
            )
        if (
            self.license_basis == self.LicenseBasis.OWNER_DECISION
            and not self.license_justification.strip()
        ):
            raise ValidationError(
                {"license_justification": "Decisão do dono exige a justificativa por escrito."}
            )
        if self.license_basis == self.LicenseBasis.NONE:
            raise ValidationError(
                {"license_basis": "Conjunto sem licença não pode ser habilitado."}
            )


class IngestionRun(models.Model):
    """Registro de uma coleta (PRD §9.1, passo 2). Imutável depois de concluída."""

    class State(models.TextChoices):
        RUNNING = "running", "Em andamento"
        SUCCEEDED = "succeeded", "Concluída com sucesso"
        FAILED = "failed", "Falhou"

    class ErrorCode(models.TextChoices):
        DOWNLOAD = "download", "Falha de download"
        SCHEMA = "schema", "Esquema diferente do esperado"
        MALFORMED_ROW = "malformed_row", "Linha malformada"
        HASH = "hash", "Hash não confere"
        BLOCKED = "blocked", "Bloqueado pela fonte"
        LICENSE = "license", "Licença mudou ou sumiu"
        OTHER = "other", "Outro"

    dataset = models.ForeignKey(
        Dataset, on_delete=models.PROTECT, related_name="runs", verbose_name="conjunto de dados"
    )
    state = models.CharField("estado", max_length=20, choices=State, default=State.RUNNING)
    started_at = models.DateTimeField("início", default=timezone.now)
    finished_at = models.DateTimeField("fim", null=True, blank=True)
    source_url = models.URLField("endereço coletado", max_length=500)
    sha256_original = models.CharField("SHA-256 do arquivo original", max_length=64, blank=True)
    etag = models.CharField("ETag", max_length=200, blank=True)
    source_generated_at = models.DateTimeField("gerado pela fonte em", null=True, blank=True)
    size_bytes = models.PositiveBigIntegerField("tamanho (bytes)", null=True, blank=True)
    rows_read = models.PositiveIntegerField("linhas lidas", default=0)
    rows_loaded = models.PositiveIntegerField("linhas gravadas", default=0)
    dropped_columns = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True,
        verbose_name="colunas descartadas (só nomes)",
    )
    error_code = models.CharField("código do erro", max_length=20, choices=ErrorCode, blank=True)
    error_detail = models.CharField("detalhe do erro", max_length=200, blank=True)

    class Meta:
        verbose_name = "execução de coleta"
        verbose_name_plural = "execuções de coleta"
        ordering = ["-started_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(state="succeeded")
                | (Q(sha256_original__regex=SHA256_HEX_REGEX) & Q(finished_at__isnull=False)),
                name="run_succeeded_requires_hash_and_end",
            ),
            models.CheckConstraint(
                condition=~Q(state="failed") | (~Q(error_code="") & Q(finished_at__isnull=False)),
                name="run_failed_requires_error_code_and_end",
            ),
            models.CheckConstraint(
                condition=~Q(state="running") | Q(finished_at__isnull=True),
                name="run_running_has_no_end",
            ),
            models.CheckConstraint(
                condition=Q(rows_loaded__lte=F("rows_read")),
                name="run_rows_loaded_not_above_read",
            ),
        ]

    def __str__(self):
        return f"{self.dataset} em {self.started_at:%Y-%m-%d %H:%M} ({self.state})"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            anterior = type(self).objects.filter(pk=self.pk).values_list("state", flat=True).first()
            if anterior is not None and anterior != self.State.RUNNING:
                raise ValueError("Execução concluída é imutável.")
        super().save(*args, **kwargs)


class Tombstone(models.Model):
    """Lápide da retirada pela fonte (ADR 0005, decisão 9; ADR 0026).

    Guarda só o id de origem, o conjunto e as datas: NENHUM dado pessoal. Existe para não
    reexpor o que a fonte retirou depois de um restore de backup (`apply_tombstones`). Se o
    registro reaparece numa carga íntegra, a lápide fica "reativada" e deixa de valer.
    """

    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.PROTECT,
        related_name="tombstones",
        verbose_name="conjunto de dados",
    )
    source_key = models.CharField("identificador na fonte", max_length=60)
    retired_at = models.DateTimeField("retirada em", default=timezone.now)
    retired_in_run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="tombstones",
        verbose_name="execução que detectou a retirada",
    )
    reinstated_at = models.DateTimeField("reativada em", null=True, blank=True)

    class Meta:
        verbose_name = "lápide"
        verbose_name_plural = "lápides"
        ordering = ["-retired_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "source_key"], name="tombstone_unique_dataset_key"
            )
        ]

    def __str__(self):
        return f"{self.dataset}: {self.source_key}"


class RawRecord(models.Model):
    """Linha da camada bruta filtrada (ADR 0005, decisão 5): só as colunas permitidas.

    Guarda o que o leitor devolveu, nada além da allowlist do conjunto. Pode ter colunas
    internas (nome civil, data de nascimento); nunca é exposta. Só as 3 últimas cargas por
    conjunto ficam (decisão 11); a história vive no modelo normalizado.
    """

    run = models.ForeignKey(
        IngestionRun,
        on_delete=models.PROTECT,
        related_name="raw_records",
        verbose_name="execução de coleta",
    )
    item_name = models.CharField("item do arquivo", max_length=255)
    values = models.JSONField("valores", default=dict)

    class Meta:
        verbose_name = "registro bruto"
        verbose_name_plural = "registros brutos"

    def __str__(self):
        return f"{self.run_id}/{self.item_name}"
