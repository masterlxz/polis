from django.core.management.base import BaseCommand

from apps.elections import normalization, retirement


class Command(BaseCommand):
    help = (
        "Reaplica as lápides ativas do TSE (ADR 0005, decisão 9): apaga de novo candidaturas, "
        "pessoas e linhas brutas que a fonte retirou e que voltaram por um restore de backup. "
        "Rode DEPOIS de restaurar e ANTES de subir o web. Idempotente; lápide reativada "
        "(o registro voltou na fonte) não vale. Sem rede."
    )

    def handle(self, *args, **options):
        name = f"{normalization.SOURCE_SLUG}/{normalization.DATASET_SLUG}"
        dataset = normalization.find_dataset()
        if dataset is None:
            self.stdout.write(f"{name}: conjunto não encontrado; nada a reaplicar.")
            return
        keys = retirement.active_keys(dataset)
        candidacies, persons, raw = retirement.erase(dataset, keys)
        self.stdout.write(
            f"{name}: lápides ativas {len(keys)}, candidaturas apagadas {candidacies}, "
            f"pessoas apagadas {persons}, linhas brutas apagadas {raw}."
        )
