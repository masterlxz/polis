import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0004_votacoes_do_senado'),
        ('sources', '0011_estado_do_alerta'),
    ]

    operations = [
        migrations.CreateModel(
            name='CamaraVoting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('camara_voting_id', models.CharField(max_length=20, verbose_name='id da votação na Câmara')),
                ('voted_on', models.DateField(verbose_name='data da votação')),
                ('organ_acronym', models.CharField(max_length=20, verbose_name='sigla do órgão')),
                ('approval', models.CharField(blank=True, max_length=1, verbose_name='aprovação')),
                ('total_yes', models.PositiveIntegerField(verbose_name='votos sim')),
                ('total_no', models.PositiveIntegerField(verbose_name='votos não')),
                ('total_other', models.PositiveIntegerField(verbose_name='outros votos')),
                ('description', models.TextField(blank=True, verbose_name='descrição')),
                ('proposition_id', models.PositiveIntegerField(verbose_name='id da proposição')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='camara_votings', to='sources.ingestionrun', verbose_name='última execução de coleta que a viu')),
            ],
            options={
                'verbose_name': 'votação da Câmara',
                'verbose_name_plural': 'votações da Câmara',
                'constraints': [models.UniqueConstraint(fields=('camara_voting_id',), name='camara_voting_unique_id')],
            },
        ),
        migrations.CreateModel(
            name='CamaraVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('camara_id', models.PositiveIntegerField(verbose_name='id do deputado na Câmara')),
                ('legislature_id', models.PositiveIntegerField(verbose_name='legislatura')),
                ('party_acronym', models.CharField(blank=True, max_length=20, verbose_name='sigla do partido')),
                ('vote', models.CharField(blank=True, max_length=40, verbose_name='voto')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='camara_votes', to='sources.ingestionrun', verbose_name='última execução de coleta que o viu')),
                ('voting', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='votes', to='legislature.camaravoting', verbose_name='votação')),
            ],
            options={
                'verbose_name': 'voto na Câmara',
                'verbose_name_plural': 'votos na Câmara',
                'constraints': [models.UniqueConstraint(fields=('voting', 'camara_id'), name='camara_vote_unique_per_voting')],
            },
        ),
    ]
