"""Contrato comum das normalizações que o agendador encadeia depois da coleta (ADR 0023).

Cada app normaliza o bruto de um conjunto na sua própria tabela (`apps/elections`,
`apps/legislature`) e expõe `normalize_latest(dataset)`: devolve `None` se não há o que fazer,
ou um resumo com `rows_read`, `created` e `existing`. Quando recusa por dado inválido ou
conflitante (falha fechada, nada gravado), levanta uma subclasse de `NormalizationRefused`,
cuja mensagem é segura por contrato: só nomes de coluna e contagens, nunca valores de linha.
Quando só falta outra coleta (a Câmara-votações recebe o arquivo de votos antes do de votações),
levanta `NormalizationWaiting`: nem sucesso nem recusa, e o agendador deixa como está o
resultado gravado no conjunto. Qualquer outra exceção é inesperada e o chamador não deve repetir
a mensagem dela.

Os comandos `normalize_*` (à mão) chamam `record_success` quando a normalização dá certo; o
agendador grava o resultado dele em `scheduling._record_normalization`.
"""

from django.utils import timezone

from .models import Dataset

CLASS_NAME_MAX_LENGTH = 80  # corte do nome da classe da exceção no log


def unexpected_error_class(error):
    """Nome da classe de uma exceção inesperada, seguro para log e mensagem de comando.

    Só o nome (`__name__`, cortado), nunca a mensagem, os argumentos, `__context__` nem
    `__cause__`: a mensagem de um erro do banco cita valores da linha. `?` se o nome não for um
    identificador, para um nome com quebra de linha não forjar outra linha de log.
    """
    name = type(error).__name__
    return (name if name.isidentifier() else "?")[:CLASS_NAME_MAX_LENGTH]


class NormalizationRefused(Exception):
    """A normalização parou antes de gravar. A mensagem é segura: sem valores de linha."""


class NormalizationWaiting(Exception):
    """A normalização espera outra coleta: não gravou nada, e não é recusa nem sucesso.

    Não é subclasse de `NormalizationRefused` de propósito: recusa vira erro gravado no conjunto,
    e a espera não deve gravar nada. O agendador a trata à parte; quem não a conhece a vê como
    erro inesperado (falha alto), o que é melhor do que tratá-la como "nada a fazer".
    """


def record_success(*datasets):
    """Marca que a última normalização de `datasets` deu certo: limpa o erro e grava a hora.

    Para os comandos `normalize_*` à mão, só depois de a normalização dar certo: recusa e falha
    inesperada não chamam isto (quem registra esses resultados é o agendador). Sem isso a recusa
    que o agendador gravou antes ficava no painel e nos avisos depois de um comando bem-sucedido.
    `update()` troca só estas duas colunas, como `scheduling._record_normalization`, para não
    desfazer uma edição feita ao mesmo tempo no admin.

    Limite conhecido (vale para todos os comandos): se o agendador coletar e recusar uma carga mais
    nova enquanto o comando ainda normaliza a anterior (janela de segundos), isto zera a recusa
    dela, e ela só reaparece na próxima coleta bem-sucedida do conjunto (1 vez por dia).
    """
    Dataset.objects.filter(pk__in=[dataset.pk for dataset in datasets]).update(
        last_normalization_at=timezone.now(), last_normalization_error=""
    )
