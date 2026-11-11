from django.core.management.base import BaseCommand, CommandError

from apps.sources import scheduling
from apps.sources.http_client import PoliteClient


class Command(BaseCommand):
    help = (
        "Coleta os conjuntos habilitados que estão vencidos (ADR 0008, decisão 6). Pensado para "
        "ser chamado a cada minuto por um cron ou timer: o minuto sorteado só vale nesse ritmo. "
        "Faz requisições reais às fontes, só dos conjuntos vencidos."
    )

    def handle(self, *args, **options):
        result = scheduling.collect_due(PoliteClient())
        for line in result.lines:
            self.stdout.write(line)
        if not result.lines:
            self.stdout.write("nada vencido")
        if result.unexpected:
            raise CommandError(
                f"{result.unexpected} conjunto(s) falharam de forma inesperada; veja a saída."
            )
