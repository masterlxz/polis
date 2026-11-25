from django.core.management.base import BaseCommand, CommandError

from apps.legislature import camara_voting_normalization as normalization
from apps.sources.normalization import record_success


class Command(BaseCommand):
    help = (
        "Normaliza o bruto das votações e dos votos da Câmara (camara/votacoes-2026 e "
        "camara/votos-2026) em votações e votos. Lê a execução mais recente que gravou linhas "
        "de cada conjunto, sem rede. Linha inválida, conflito ou voto sem votação param tudo e "
        "não gravam nada; nunca apaga."
    )

    def handle(self, *args, **options):
        names = (
            f"{normalization.SOURCE_SLUG}/{normalization.VOTINGS_SLUG} e "
            f"{normalization.SOURCE_SLUG}/{normalization.VOTES_SLUG}"
        )
        votings_dataset, votes_dataset = normalization.find_datasets()
        if votings_dataset is None or votes_dataset is None:
            raise CommandError(f"Conjuntos {names} não encontrados.")
        votings_run = normalization.latest_run(votings_dataset)
        votes_run = normalization.latest_run(votes_dataset)
        if votings_run is None or votes_run is None:
            raise CommandError(f"Falta carga com linhas para {names}; rode ingest_dataset.")

        failed = False
        try:
            result = normalization.normalize(votings_run, votes_run)
        except normalization.NormalizationRefused as error:
            raise CommandError(str(error)) from None
        except Exception:
            # A mensagem de um erro do banco cita valores da linha: não é repassada nem
            # encadeada (mesmo cuidado de apps/sources/ingestion.py).
            failed = True
        if failed:
            raise CommandError(
                "A normalização falhou de forma inesperada; nada foi gravado."
            ) from None

        # Só no sucesso: a normalização leu os dois conjuntos, então os dois deixam de ter a
        # recusa que o agendador gravou antes (ele grava no conjunto cuja coleta disparou o passo).
        record_success(votings_dataset)  # MUTAÇÃO DO COORDENADOR: só um dos dois conjuntos
        self.stdout.write(
            f"Execuções {votings_run.pk} e {votes_run.pk}: linhas lidas {result.rows_read}, "
            f"votos únicos {result.unique}, criadas {result.created}, "
            f"já existentes {result.existing}; votações criadas {result.votings_created}."
        )
