from django.core.management.base import BaseCommand, CommandError

from apps.sources.http_client import PoliteClient
from apps.sources.ingestion import IngestionError, ingest
from apps.sources.models import Dataset


class Command(BaseCommand):
    help = (
        "Coleta um conjunto de dados habilitado (ADR 0008): baixa, lê só a allowlist e grava a "
        "camada bruta. Uso: ingest_dataset <fonte>/<conjunto>. Faz requisições reais à fonte."
    )

    def add_arguments(self, parser):
        parser.add_argument("dataset", help="fonte/conjunto, por exemplo tse/consulta-cand-2026")

    def handle(self, *args, **options):
        source_slug, separator, dataset_slug = options["dataset"].partition("/")
        if not separator or not source_slug or not dataset_slug:
            raise CommandError("Use o formato fonte/conjunto.")
        dataset = (
            Dataset.objects.select_related("source")
            .filter(source__slug=source_slug, slug=dataset_slug)
            .first()
        )
        if dataset is None:
            raise CommandError("Conjunto não encontrado.")
        try:
            run = ingest(dataset, PoliteClient())
        except ValueError as error:
            raise CommandError(str(error)) from None
        except IngestionError as error:
            raise CommandError(str(error)) from None
        self.stdout.write(
            f"{dataset}: {run.state}, linhas lidas {run.rows_read}, "
            f"gravadas {run.rows_loaded}, erro {run.error_code or '-'}"
        )
