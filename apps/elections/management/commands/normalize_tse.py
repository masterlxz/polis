from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.elections import normalization
from apps.sources.models import Dataset
from apps.sources.normalization import NormalizationRefused as SharedRefused


class Command(BaseCommand):
    help = (
        "Normaliza o bruto do TSE (tse/consulta-cand-2026) em eleições, pessoas e candidaturas. "
        "Lê a execução mais recente que gravou linhas, sem rede. Linha inválida ou conflito "
        "param tudo e não gravam nada. Candidatura que sumiu da carga é retirada e vira lápide "
        "(ADR 0005, decisão 9); acima do limite do disjuntor a carga é recusada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--aceitar-retiradas",
            action="store_true",
            help=(
                "Aceita retiradas acima do limite do disjuntor (apagamento irreversível: "
                "confira antes que o arquivo da fonte não está incompleto)."
            ),
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
            result = normalization.normalize(run, accept_retirements=options["aceitar_retiradas"])
        except SharedRefused as error:
            raise CommandError(str(error)) from None
        except Exception:
            # A mensagem de um erro do banco cita valores da linha: não é repassada nem
            # encadeada (mesmo cuidado de apps/sources/ingestion.py).
            failed = True
        if failed:
            raise CommandError(
                "A normalização falhou de forma inesperada; nada foi gravado."
            ) from None

        # Só no sucesso: a carga mais recente foi normalizada, então a recusa que o agendador
        # gravou antes deixou de valer (senão o painel e o aviso de coleta falhada seguem dizendo
        # que as retiradas estão paradas). Recusa e falha inesperada não gravam nada aqui: quem
        # registra esses resultados é o agendador. `update()` troca só estas duas colunas, como
        # `scheduling._record_normalization`, para não desfazer uma edição feita ao mesmo tempo
        # no admin. Limite conhecido: se o agendador coletar e recusar uma carga mais nova enquanto
        # este comando ainda normaliza a anterior (janela de segundos, coleta 1 vez por dia), este
        # `update()` zera a recusa dela; a próxima passada do agendador a grava de novo.
        Dataset.objects.all().update(  # MUTAÇÃO DO COORDENADOR: sem filtro por conjunto
            last_normalization_at=timezone.now(), last_normalization_error=""
        )
        self.stdout.write(
            f"Execução {run.pk}: linhas lidas {result.rows_read}, "
            f"candidaturas únicas {result.unique}, criadas {result.created}, "
            f"já existentes {result.existing}, retiradas {result.retired}."
        )
