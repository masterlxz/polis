from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0009_formato_json_senado_votacoes'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='last_normalization_at',
            field=models.DateTimeField(blank=True, help_text='Escrito pelo agendador depois de cada coleta; vazio se nunca normalizou.', null=True, verbose_name='última normalização tentada em'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='last_normalization_error',
            field=models.CharField(blank=True, help_text='Vazio: a última normalização deu certo. Recusa mostra a mensagem do contrato (só colunas e contagens); falha inesperada mostra um texto fixo.', max_length=300, verbose_name='erro da última normalização'),
        ),
    ]
