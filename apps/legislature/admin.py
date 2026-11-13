from django.contrib import admin

from .models import Deputy, Senator


@admin.register(Deputy)
class DeputyAdmin(admin.ModelAdmin):
    """Dado derivado da fonte: só leitura. A correção é feita na fonte (ADR 0005, decisão 10)."""

    list_display = [
        "name",
        "party_acronym",
        "state",
        "legislature_id",
        "camara_id",
        "in_office",
        "left_list_at",
    ]
    list_filter = ["in_office", "legislature_id", "state", "party_acronym"]
    search_fields = ["name"]
    raw_id_fields = ["ingestion_run"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Senator)
class SenatorAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0028)."""

    list_display = ["name", "party_acronym", "state", "senate_id", "in_office", "left_list_at"]
    list_filter = ["in_office", "state", "party_acronym"]
