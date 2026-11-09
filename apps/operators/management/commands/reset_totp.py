from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.operators import enrollment


class Command(BaseCommand):
    help = (
        "Recupera a conta de um operador que perdeu o aparelho (ADR 0019): apaga todos os "
        "dispositivos e códigos de recuperação antigos e cria novos. Não mexe na senha. "
        "Roda no servidor, por quem tem acesso a ele."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--codes",
            type=int,
            default=enrollment.DEFAULT_RECOVERY_CODES,
            help="Quantidade de códigos de recuperação.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        codes = options["codes"]
        if codes < 1:
            raise CommandError("--codes precisa ser pelo menos 1.")

        User = get_user_model()
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"O usuário {username!r} não existe.") from None

        # Tudo ou nada: ou o operador fica com o segundo fator novo, ou com o antigo.
        with transaction.atomic():
            TOTPDevice.objects.filter(user=usuario).delete()
            StaticDevice.objects.filter(user=usuario).delete()
            dispositivo, tokens = enrollment.enroll(usuario, codes)

        self.stdout.write(f"Segundo fator de {username!r} refeito.\n")
        self.stdout.write(enrollment.render(dispositivo, tokens))
