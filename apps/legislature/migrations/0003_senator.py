import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0002_saida_do_exercicio'),
        ('sources', '0008_formato_json_senado'),
    ]

    operations = [
        migrations.CreateModel(
            name='Senator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('senate_id', models.PositiveIntegerField(verbose_name='código no Senado')),
                ('name', models.CharField(max_length=100, verbose_name='nome parlamentar')),
                ('party_acronym', models.CharField(blank=True, max_length=20, verbose_name='sigla do partido')),
                ('state', models.CharField(max_length=2, verbose_name='UF')),
                ('in_office', models.BooleanField(default=True, help_text='Falso: não consta mais na lista de senadores em exercício do Senado. A lista não diz o motivo (licença, fim de mandato, renúncia, morte, titular de volta).', verbose_name='em exercício')),
                ('left_list_at', models.DateTimeField(blank=True, help_text='Início da primeira execução de coleta que não o trouxe: a data da COLETA, não a do fim do mandato. Vazio enquanto está na lista.', null=True, verbose_name='saiu da lista em')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='senators', to='sources.ingestionrun', verbose_name='última execução de coleta que o viu')),
            ],
            options={
                'verbose_name': 'senador',
                'verbose_name_plural': 'senadores',
                'constraints': [models.UniqueConstraint(fields=('senate_id',), name='senator_unique_senate_id'), models.CheckConstraint(condition=models.Q(('name', ''), _negated=True), name='senator_name')],
            },
        ),
    ]
