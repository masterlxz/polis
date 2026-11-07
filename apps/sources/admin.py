from django.contrib import admin

from .models import Dataset, IngestionRun, Source


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["slug", "name", "institution", "access_type", "status"]
    list_filter = ["status", "access_type"]
    search_fields = ["slug", "name", "institution"]


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ["__str__", "format", "license_basis", "enabled"]
    list_filter = ["enabled", "license_basis", "format", "source"]
    search_fields = ["slug", "name"]


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
