from django.core.management.base import BaseCommand, CommandError

from apps.legislature import camara_proposition_normalization as normalization
from apps.sources.models import Dataset
from apps.sources.normalization import record_success, unexpected_error_class


class Command(BaseCommand):
    help = (
        "Normaliza o bruto das proposições das votações da Câmara "
        "(camara/votacoes-proposicoes-2026 e camara/votacoes-objetos-2026) em proposições e "
        "ligações votação-proposição. Lê a execução mais recente que gravou linhas de cada "
        "conjunto, sem rede. Linha inválida ou conflito param tudo e não gravam nada; nunca apaga."
    )

    def handle(self, *args, **options):
        slugs = list(normalization.ORIGIN_BY_SLUG)
        names = " e ".join(f"{normalization.SOURCE_SLUG}/{slug}" for slug in slugs)
        datasets = {
            dataset.slug: dataset
            for dataset in Dataset.objects.filter(
                source__slug=normalization.SOURCE_SLUG, slug__in=slugs
            )
        }
        if len(datasets) != len(slugs):
            raise CommandError(f"Conjuntos {names} não encontrados.")
        runs = {slug: normalization.latest_run(datasets[slug]) for slug in slugs}
        if any(run is None for run in runs.values()):
            raise CommandError(f"Falta carga com linhas para {names}; rode ingest_dataset.")

        for slug in slugs:
            self._normalize_one(datasets[slug], runs[slug])

    def _normalize_one(self, dataset, run):
        failed = False
        try:
            result = normalization.normalize(run, normalization.ORIGIN_BY_SLUG[dataset.slug])
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
            f"proposições {result.unique}, criadas {result.created}, "
            f"já existentes {result.existing}; ligações criadas {result.links_created}."
        )
