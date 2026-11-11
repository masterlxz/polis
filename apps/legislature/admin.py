from django.contrib import admin

from .models import Deputy


@admin.register(Deputy)
class DeputyAdmin(admin.ModelAdmin):
    """Dado derivado da fonte: só leitura. A correção é feita na fonte (ADR 0005, decisão 10)."""

    list_display = ["name", "party_acronym", "state", "legislature_id", "camara_id"]
    list_filter = ["legislature_id", "state", "party_acronym"]
    search_fields = ["name"]
    raw_id_fields = ["ingestion_run"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
