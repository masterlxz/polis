from django.contrib import admin

from .models import (
    CamaraProposition,
    CamaraVote,
    CamaraVoting,
    CamaraVotingProposition,
    Deputy,
    SenateVote,
    SenateVoting,
    Senator,
)


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


@admin.register(SenateVoting)
class SenateVotingAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0029)."""

    list_display = ["identification", "voted_on", "result", "secret", "session_voting_code"]
    list_filter = ["secret", "result", "year"]
    search_fields = ["identification", "summary"]


@admin.register(SenateVote)
class SenateVoteAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0029)."""

    list_display = ["name", "party_acronym", "state", "vote_code", "voting"]
    list_filter = ["vote_code", "state", "party_acronym"]
    search_fields = ["name"]
    raw_id_fields = ["ingestion_run", "voting"]


@admin.register(CamaraVoting)
class CamaraVotingAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0031)."""

    list_display = ["camara_voting_id", "voted_on", "organ_acronym", "approval", "proposition_id"]
    list_filter = ["organ_acronym", "approval"]
    search_fields = ["camara_voting_id", "description"]


@admin.register(CamaraVote)
class CamaraVoteAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0031). Sem nome do deputado: o voto guarda só o id (ADR 0005)."""

    list_display = ["camara_id", "legislature_id", "party_acronym", "vote", "voting"]
    list_filter = ["vote", "party_acronym"]
    list_select_related = ["voting"]
    search_fields = ["voting__camara_voting_id"]
    raw_id_fields = ["ingestion_run", "voting"]


@admin.register(CamaraProposition)
class CamaraPropositionAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0033)."""

    list_display = ["camara_id", "title", "type_acronym", "number", "year"]
    list_filter = ["type_acronym", "year"]
    search_fields = ["title", "ementa"]
    raw_id_fields = ["ingestion_run"]

    def has_add_permission(self, request):
        return True


@admin.register(CamaraVotingProposition)
class CamaraVotingPropositionAdmin(DeputyAdmin):
    """Idem: só leitura (ADR 0033). A votação é só o texto do id, sem chave."""

    list_display = ["camara_voting_id", "proposition", "origin"]
    list_filter = ["origin"]
    list_select_related = ["proposition"]
    search_fields = ["camara_voting_id", "proposition__title"]
    raw_id_fields = ["ingestion_run", "proposition"]
