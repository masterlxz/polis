from django.core.management.base import BaseCommand, CommandError

from apps.legislature import camara_tramitacao_normalization as normalization
from apps.sources.models import Dataset
from apps.sources.normalization import record_success, unexpected_error_class


class Command(BaseCommand):
    help = (
        "Normaliza o bruto das tramitações das proposições da Câmara "
        "(camara/proposicoes-tramitacoes-2026) em tramitações. Lê a execução mais recente que "
        "gravou linhas do conjunto, sem rede. Linha inválida para tudo e não grava nada; nunca "
        "apaga."
    )

    def handle(self, *args, **options):
        name = f"{normalization.SOURCE_SLUG}/{normalization.DATASET_SLUG}"
        dataset = Dataset.objects.filter(
            source__slug=normalization.SOURCE_SLUG, slug=normalization.DATASET_SLUG
        ).first()
        if dataset is None:
            raise CommandError(f"Conjunto {name} não encontrado.")
        run = normalization.latest_run(dataset)
        if run is None:
            raise CommandError(f"Falta carga com linhas para {name}; rode ingest_dataset.")

        failed = False
        try:
            result = normalization.normalize(run)
        except normalization.NormalizationRefused as error:
            raise CommandError(str(error)) from None
        except Exception as error:
            # A mensagem de um erro do banco cita valores da linha: não é repassada nem
            # encadeada (mesmo cuidado de apps/sources/ingestion.py); só o nome da classe.
            failed = True
            error_class = unexpected_error_class(error)
        if failed:
            raise CommandError(
                f"A normalização falhou de forma inesperada ({error_class}); nada foi gravado."
            ) from None

        # Só no sucesso: limpa a recusa que o agendador gravou antes neste conjunto.
        record_success(dataset)
        self.stdout.write(
            f"{dataset.slug}, execução {run.pk}: linhas lidas {result.rows_read}, "
            f"tramitações {result.unique}, criadas {result.created}, "
            f"já existentes {result.existing}."
        )
