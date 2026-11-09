import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.operators import enrollment


class Command(BaseCommand):
    help = (
        "Cria um operador do admin com TOTP obrigatório (ADR 0019). A senha é pedida por "
        "prompt, nunca por argumento. Imprime a URL do TOTP e os códigos de recuperação uma vez."
    )

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--superuser", action="store_true", help="Cria superusuário (padrão: só is_staff)."
        )
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
        if User.objects.filter(username=username).exists():
            raise CommandError(f"O usuário {username!r} já existe.")

        senha = getpass.getpass("Senha: ")
        if senha != getpass.getpass("Confirme a senha: "):
            raise CommandError("As senhas não conferem.")
        try:
            validate_password(senha, User(username=username))
        except ValidationError as erro:
            raise CommandError("Senha recusada: " + " ".join(erro.messages)) from erro

        criar = User.objects.create_superuser if options["superuser"] else User.objects.create_user
        # Tudo ou nada: um usuário sem segundo fator não pode ficar no banco.
        with transaction.atomic():
            usuario = criar(username, password=senha, is_staff=True)
            dispositivo, tokens = enrollment.enroll(usuario, codes)

        self.stdout.write(f"Operador {username!r} criado.\n")
        self.stdout.write(enrollment.render(dispositivo, tokens))
