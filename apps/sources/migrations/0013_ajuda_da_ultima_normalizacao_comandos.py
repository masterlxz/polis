from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0012_ajuda_da_ultima_normalizacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='last_normalization_at',
            field=models.DateTimeField(blank=True, help_text='Escrito pelo agendador depois de cada coleta e pelos comandos normalize_* quando dão certo; vazio se nunca normalizou.', null=True, verbose_name='última normalização tentada em'),
        ),
    ]
