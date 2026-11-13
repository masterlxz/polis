import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0003_senator'),
        ('sources', '0009_formato_json_senado_votacoes'),
    ]

    operations = [
        migrations.CreateModel(
            name='SenateVoting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_voting_code', models.PositiveIntegerField(verbose_name='código da votação no Senado')),
                ('voted_on', models.DateField(verbose_name='data da sessão')),
                ('type_acronym', models.CharField(max_length=20, verbose_name='sigla do tipo')),
                ('number', models.CharField(max_length=20, verbose_name='número')),
                ('year', models.PositiveSmallIntegerField(verbose_name='ano')),
                ('identification', models.CharField(max_length=60, verbose_name='identificação')),
                ('summary', models.TextField(blank=True, verbose_name='ementa')),
                ('result', models.CharField(max_length=10, verbose_name='resultado')),
                ('secret', models.BooleanField(help_text="Verdadeiro: o conteúdo do voto não é divulgado; 'Votou' só diz que votou.", verbose_name='votação secreta')),
                ('total_yes', models.PositiveIntegerField(blank=True, null=True, verbose_name='total de votos sim')),
                ('total_no', models.PositiveIntegerField(blank=True, null=True, verbose_name='total de votos não')),
                ('total_abstention', models.PositiveIntegerField(blank=True, null=True, verbose_name='total de abstenções')),
                ('process_id', models.PositiveIntegerField(verbose_name='código do processo')),
                ('matter_id', models.PositiveIntegerField(verbose_name='código da matéria')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='senate_votings', to='sources.ingestionrun', verbose_name='última execução de coleta que a viu')),
            ],
            options={
                'verbose_name': 'votação do Senado',
                'verbose_name_plural': 'votações do Senado',
                'constraints': [models.UniqueConstraint(fields=('session_voting_code',), name='senate_voting_unique_code')],
            },
        ),
        migrations.CreateModel(
            name='SenateVote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('senate_id', models.PositiveIntegerField(verbose_name='código do parlamentar no Senado')),
                ('name', models.CharField(max_length=100, verbose_name='nome parlamentar')),
                ('party_acronym', models.CharField(blank=True, max_length=20, verbose_name='sigla do partido')),
                ('state', models.CharField(max_length=2, verbose_name='UF')),
                ('vote_code', models.CharField(max_length=40, verbose_name='sigla do voto')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='senate_votes', to='sources.ingestionrun', verbose_name='última execução de coleta que o viu')),
                ('voting', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='votes', to='legislature.senatevoting', verbose_name='votação')),
            ],
            options={
                'verbose_name': 'voto no Senado',
                'verbose_name_plural': 'votos no Senado',
                'constraints': [models.UniqueConstraint(fields=('voting', 'senate_id'), name='senate_vote_unique_per_voting')],
            },
        ),
    ]
