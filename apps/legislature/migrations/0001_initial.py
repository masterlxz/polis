import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('sources', '0005_erro_de_download_detalhado'),
    ]

    operations = [
        migrations.CreateModel(
            name='Deputy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('legislature_id', models.PositiveIntegerField(verbose_name='legislatura')),
                ('camara_id', models.PositiveIntegerField(verbose_name='id na Câmara')),
                ('name', models.CharField(max_length=100, verbose_name='nome parlamentar')),
                ('party_acronym', models.CharField(blank=True, max_length=20, verbose_name='sigla do partido')),
                ('state', models.CharField(max_length=2, verbose_name='UF')),
                ('ingestion_run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='deputies', to='sources.ingestionrun', verbose_name='última execução de coleta que o viu')),
            ],
            options={
                'verbose_name': 'deputado',
                'verbose_name_plural': 'deputados',
                'constraints': [models.UniqueConstraint(fields=('legislature_id', 'camara_id'), name='deputy_unique_legislature_camara_id'), models.CheckConstraint(condition=models.Q(('name', ''), _negated=True), name='deputy_name')],
            },
        ),
    ]
