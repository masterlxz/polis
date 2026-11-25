from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0011_estado_do_alerta'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='last_normalization_at',
            field=models.DateTimeField(blank=True, help_text='Escrito pelo agendador depois de cada coleta e pelo normalize_tse quando ele dá certo; vazio se nunca normalizou.', null=True, verbose_name='última normalização tentada em'),
        ),
    ]
