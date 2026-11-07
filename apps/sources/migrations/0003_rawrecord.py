import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0002_licenca_do_conjunto'),
    ]

    operations = [
        migrations.CreateModel(
            name='RawRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_name', models.CharField(max_length=255, verbose_name='item do arquivo')),
                ('values', models.JSONField(default=dict, verbose_name='valores')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='raw_records', to='sources.ingestionrun', verbose_name='execução de coleta')),
            ],
            options={
                'verbose_name': 'registro bruto',
                'verbose_name_plural': 'registros brutos',
            },
        ),
    ]
