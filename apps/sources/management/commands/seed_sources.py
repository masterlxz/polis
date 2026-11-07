from django.core.management.base import BaseCommand

from apps.sources import catalog
from apps.sources.models import Dataset, Source

# Campos que o seed mantém iguais ao catálogo. Tudo fora daqui (status, enabled, notes e a
# licença registrada do conjunto) é decisão do dono e nunca é sobrescrito depois de criado.
SOURCE_DESCRIPTIVE = (
    "name",
    "institution",
    "official_url",
    "access_type",
    "terms_url",
    "license_note",
)
DATASET_DESCRIPTIVE = ("name", "url", "format", "allowed_columns", "internal_columns")
DATASET_ON_CREATION = ("license_basis", "license_id", "license_url")


class Command(BaseCommand):
    help = (
        "Cadastra as fontes e o primeiro conjunto (apps/sources/catalog.py). Idempotente: só "
        "atualiza campos descritivos e nunca muda status nem enabled. Não faz requisições."
    )

    def handle(self, *args, **options):
        created_sources, updated_sources = 0, 0
        for definition in catalog.SOURCES:
            created, updated = self._upsert(
                Source, {"slug": definition["slug"]}, definition, SOURCE_DESCRIPTIVE, ()
            )
            created_sources += created
            updated_sources += updated

        created_datasets, updated_datasets = 0, 0
        for definition in catalog.DATASETS:
            source = Source.objects.get(slug=definition["source"])
            created, updated = self._upsert(
                Dataset,
                {"source": source, "slug": definition["slug"]},
                definition,
                DATASET_DESCRIPTIVE,
                DATASET_ON_CREATION,
            )
            created_datasets += created
            updated_datasets += updated

        self.stdout.write(
            f"Fontes: {created_sources} criadas, {updated_sources} atualizadas. "
            f"Conjuntos: {created_datasets} criados, {updated_datasets} atualizados."
        )

    @staticmethod
    def _upsert(model, lookup, definition, descriptive, on_creation):
        values = {name: definition[name] for name in descriptive}
        defaults = {**values, **{name: definition[name] for name in on_creation}}
        obj, created = model.objects.get_or_create(**lookup, defaults=defaults)
        if created:
            return True, False
        changed = [name for name, value in values.items() if getattr(obj, name) is None]
        for name in changed:
            setattr(obj, name, values[name])
        if changed:
            obj.save(update_fields=changed)
        return False, bool(changed)
