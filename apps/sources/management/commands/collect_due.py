from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.sources import alerts, scheduling, webhook
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
        self._send_alerts()
        problems = []
        if result.unexpected:
            problems.append(f"{result.unexpected} coleta(s) falharam de forma inesperada")
        if result.normalization_failed:
            problems.append(f"{result.normalization_failed} normalização(ões) não concluída(s)")
        if problems:
            raise CommandError("; ".join(problems) + "; veja a saída.")

    def _send_alerts(self):
        """Alerta ativo (Sessão 76): nunca derruba a coleta e nunca mostra a URL nem a exceção."""
        url = settings.ALERT_WEBHOOK_URL
        if not url:
            return

        def sender(text):
            webhook.post_text(url, text)

        try:
            outcome = alerts.send_pending(timezone.now(), sender)
        except Exception:  # a exceção pode citar a URL, que carrega o segredo
            self.stdout.write("alerta: falha inesperada ao avisar")
            return
        if outcome.failed:
            self.stdout.write("alerta: o webhook não aceitou o aviso; tenta na próxima volta")
        elif outcome.sent:
            self.stdout.write(f"alerta: {outcome.sent} aviso(s) enviado(s)")
