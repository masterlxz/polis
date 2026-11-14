from django.contrib import admin
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from .freshness import Situation, situation
from .models import Dataset, IngestionRun, Source, Tombstone


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "institution", "access_type", "status"]
    list_filter = ["status", "access_type"]
    search_fields = ["slug", "name", "institution"]


def _situation_of(dataset, now):
    return situation(
        enabled=dataset.enabled,
        interval_hours=dataset.schedule_interval_hours,
        next_collection_at=dataset.next_collection_at,
        last_success_at=dataset.last_success_at,
        last_finished_state=dataset.last_finished_state,
        normalization_failed=bool(dataset.last_normalization_error),
        now=now,
    )


class SituationFilter(admin.SimpleListFilter):
    """Separa os conjuntos pela situação da regra de `freshness.py`.

    A situação é calculada em Python sobre a lista já anotada: são dezenas de conjuntos, então
    não vale duplicar a regra em SQL (duas regras iguais em dois lugares acabam divergindo).
    """

    title = "situação"
    parameter_name = "situacao"

    def lookups(self, request, model_admin):
        return Situation.choices

    def queryset(self, request, queryset):
        wanted = self.value()
        if wanted not in Situation.values:
            return queryset
        now = timezone.now()
        pks = [d.pk for d in queryset if _situation_of(d, now) == wanted]
        return queryset.filter(pk__in=pks)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Também é o painel de fontes do monitoramento (Etapa 0): última coleta e situação."""

    list_display = [
        "__str__",
        "format",
        "license_basis",
        "enabled",
        "situation",
        "last_success",
        "last_result",
        "last_normalization",
        "next_collection_at",
    ]
    readonly_fields = ["last_normalization_at", "last_normalization_error"]
    list_filter = [SituationFilter, "enabled", "license_basis", "format", "source"]
    list_select_related = ["source"]
    search_fields = ["slug", "name"]

    def get_queryset(self, request):
        finished = IngestionRun.objects.filter(dataset=OuterRef("pk")).exclude(
            state=IngestionRun.State.RUNNING
        )
        succeeded = finished.filter(state=IngestionRun.State.SUCCEEDED)
        latest_success = succeeded.order_by("-finished_at").values("finished_at")[:1]
        latest = finished.order_by("-finished_at", "-pk")
        queryset = super().get_queryset(request)
        return queryset.annotate(
            last_success_at=Subquery(latest_success),
            last_finished_state=Subquery(latest.values("state")[:1]),
            last_error_code=Subquery(latest.values("error_code")[:1]),
        )

    @admin.display(description="situação")
    def situation(self, obj):
        return Situation(_situation_of(obj, timezone.now())).label

    @admin.display(description="última coleta com sucesso")
    def last_success(self, obj):
        return obj.last_success_at

    @admin.display(description="última normalização")
    def last_normalization(self, obj):
        if obj.last_normalization_error:
            return obj.last_normalization_error
        if obj.last_normalization_at is None:
            return "-"
        return "Concluída"

    @admin.display(description="resultado da última execução")
    def last_result(self, obj):
        if obj.last_finished_state is None:
            return "Nenhuma execução concluída"
        label = IngestionRun.State(obj.last_finished_state).label
        if obj.last_error_code:
            return f"{label}: {IngestionRun.ErrorCode(obj.last_error_code).label}"
        return label


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    """Só leitura: a execução é escrita pelo conector e não muda depois de concluída."""

    list_display = ["dataset", "state", "started_at", "finished_at", "rows_loaded", "error_code"]
    list_filter = ["state", "error_code", "dataset__source"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Tombstone)
class TombstoneAdmin(admin.ModelAdmin):
    """Só leitura: a lápide é escrita pela normalização (ADR 0005, decisão 9) e só tem ids."""

    list_display = ["dataset", "source_key", "retired_at", "reinstated_at"]
    list_filter = ["dataset"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
