from django.core.management.base import BaseCommand, CommandError

from apps.elections import normalization


class Command(BaseCommand):
    help = (
        "Normaliza o bruto do TSE (tse/consulta-cand-2026) em eleições, pessoas e candidaturas. "
        "Lê a execução mais recente que gravou linhas, sem rede. Linha inválida ou conflito "
        "param tudo e não gravam nada; nunca apaga."
    )

    def handle(self, *args, **options):
        name = f"{normalization.SOURCE_SLUG}/{normalization.DATASET_SLUG}"
        dataset = normalization.find_dataset()
        if dataset is None:
            raise CommandError(f"Conjunto {name} não encontrado.")
        run = normalization.latest_run(dataset)
        if run is None:
            raise CommandError(f"Nenhuma carga com linhas para {name}; rode ingest_dataset.")

        failed = False
        try:
            result = normalization.normalize(run)
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

        self.stdout.write(
            f"Execução {run.pk}: linhas lidas {result.rows_read}, "
            f"candidaturas únicas {result.unique}, criadas {result.created}, "
            f"já existentes {result.existing}."
        )
