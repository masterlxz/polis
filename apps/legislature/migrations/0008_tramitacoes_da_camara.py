import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0007_proposicoes_da_camara'),
        ('sources', '0013_ajuda_da_ultima_normalizacao_comandos'),
    ]

    operations = [
        migrations.CreateModel(
            name='CamaraPropositionStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('camara_proposition_id', models.CharField(max_length=10, verbose_name='id da proposição na Câmara')),
                ('sequence', models.PositiveIntegerField(blank=True, null=True, verbose_name='sequência')),
                ('occurred_at', models.DateTimeField(verbose_name='data e hora')),
                ('organ_code', models.CharField(max_length=30, verbose_name='sigla do órgão')),
                ('description', models.CharField(max_length=200, verbose_name='descrição da tramitação')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='camara_proposition_steps', to='sources.ingestionrun', verbose_name='última execução de coleta que a viu')),
            ],
            options={
                'verbose_name': 'tramitação de proposição da Câmara',
                'verbose_name_plural': 'tramitações de proposições da Câmara',
                'constraints': [models.UniqueConstraint(fields=('camara_proposition_id', 'sequence', 'occurred_at', 'organ_code', 'description'), name='camara_proposition_step_unique', nulls_distinct=False)],
            },
        ),
    ]
