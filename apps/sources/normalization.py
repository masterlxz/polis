"""Contrato comum das normalizações que o agendador encadeia depois da coleta (ADR 0023).

Cada app normaliza o bruto de um conjunto na sua própria tabela (`apps/elections`,
`apps/legislature`) e expõe `normalize_latest(dataset)`: devolve `None` se não há o que fazer,
ou um resumo com `rows_read`, `created` e `existing`. Quando recusa por dado inválido ou
conflitante (falha fechada, nada gravado), levanta uma subclasse de `NormalizationRefused`,
cuja mensagem é segura por contrato: só nomes de coluna e contagens, nunca valores de linha.
Qualquer outra exceção é inesperada e o chamador não deve repetir a mensagem dela.
"""


class NormalizationRefused(Exception):
    """A normalização parou antes de gravar. A mensagem é segura: sem valores de linha."""
