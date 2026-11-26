import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0006_indice_dos_votos_da_camara'),
        ('sources', '0013_ajuda_da_ultima_normalizacao_comandos'),
    ]

    operations = [
        migrations.CreateModel(
            name='CamaraProposition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('camara_id', models.PositiveIntegerField(verbose_name='id da proposição na Câmara')),
                ('title', models.CharField(max_length=100, verbose_name='título')),
                ('type_acronym', models.CharField(max_length=10, verbose_name='sigla do tipo')),
                ('number', models.PositiveIntegerField(verbose_name='número')),
                ('year', models.PositiveIntegerField(blank=True, null=True, verbose_name='ano')),
                ('ementa', models.TextField(blank=True, verbose_name='ementa')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='camara_propositions', to='sources.ingestionrun', verbose_name='última execução de coleta que a viu')),
            ],
            options={
                'verbose_name': 'proposição da Câmara',
                'verbose_name_plural': 'proposições da Câmara',
                'constraints': [models.UniqueConstraint(fields=('camara_id',), name='camara_proposition_unique_id')],
            },
        ),
        migrations.CreateModel(
            name='CamaraVotingProposition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('camara_voting_id', models.CharField(max_length=20, verbose_name='id da votação na Câmara')),
                ('origin', models.CharField(max_length=20, verbose_name='arquivo de origem')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='camara_voting_propositions', to='sources.ingestionrun', verbose_name='última execução de coleta que a viu')),
                ('proposition', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='voting_links', to='legislature.camaraproposition', verbose_name='proposição')),
            ],
            options={
                'verbose_name': 'proposição de votação da Câmara',
                'verbose_name_plural': 'proposições de votações da Câmara',
                'constraints': [models.UniqueConstraint(fields=('camara_voting_id', 'proposition'), name='camara_voting_proposition_unique')],
            },
        ),
    ]
