from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0010_resultado_da_normalizacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='last_alert_situation',
            field=models.CharField(blank=True, help_text='Vazio: nenhum aviso aberto. Escrito pelo alerta ativo (Sessão 76).', max_length=30, verbose_name='situação do último aviso'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='last_alert_at',
            field=models.DateTimeField(blank=True, help_text='Quando o último aviso (alerta, lembrete ou recuperação) foi entregue.', null=True, verbose_name='último aviso enviado em'),
        ),
    ]
