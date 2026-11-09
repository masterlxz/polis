from django.contrib import admin

from .models import Candidacy, Election, Person


class ReadOnlyAdmin(admin.ModelAdmin):
    """Dado derivado da fonte: só leitura. A correção é feita na fonte (ADR 0005, decisão 10)."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Election)
class ElectionAdmin(ReadOnlyAdmin):
    list_display = ["description", "round", "year", "date"]
    list_filter = ["year", "round"]


@admin.register(Person)
class PersonAdmin(ReadOnlyAdmin):
    """O nome social é interno e fica fora da lista e da busca."""

    list_display = ["public_name", "cycle_year", "tse_candidate_id"]
    list_filter = ["cycle_year"]
    search_fields = ["public_name"]
    exclude = ["social_name"]


@admin.register(Candidacy)
class CandidacyAdmin(ReadOnlyAdmin):
    list_display = ["person", "election", "office_name", "state", "party_acronym"]
    list_filter = ["election", "office_name", "state"]
    raw_id_fields = ["person", "election", "ingestion_run"]
