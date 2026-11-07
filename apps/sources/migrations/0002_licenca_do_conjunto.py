from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='license_basis',
            field=models.CharField(choices=[('none', 'Sem licença'), ('declared', 'Declarada pela fonte'), ('owner_decision', 'Decisão do dono')], default='none', help_text='Licença é do conjunto, não da fonte (ADR 0008, decisão 1).', max_length=20, verbose_name='base da licença'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='license_id',
            field=models.CharField(blank=True, help_text='Como a fonte declara (por exemplo, o license_id do CKAN do TSE).', max_length=100, verbose_name='identificador da licença'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='license_url',
            field=models.URLField(blank=True, max_length=500, verbose_name='endereço da licença'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='license_justification',
            field=models.TextField(blank=True, help_text='Obrigatória na decisão do dono: por que coletar sem licença declarada.', verbose_name='justificativa do dono'),
        ),
        migrations.AlterField(
            model_name='dataset',
            name='enabled',
            field=models.BooleanField(default=False, help_text='Só pode ser habilitado com colunas permitidas e base de licença.', verbose_name='habilitado'),
        ),
        migrations.AlterField(
            model_name='ingestionrun',
            name='error_code',
            field=models.CharField(blank=True, choices=[('download', 'Falha de download'), ('schema', 'Esquema diferente do esperado'), ('malformed_row', 'Linha malformada'), ('hash', 'Hash não confere'), ('blocked', 'Bloqueado pela fonte'), ('license', 'Licença mudou ou sumiu'), ('other', 'Outro')], max_length=20, verbose_name='código do erro'),
        ),
        migrations.AddConstraint(
            model_name='dataset',
            constraint=models.CheckConstraint(
                condition=models.Q(enabled=False)
                | (models.Q(license_basis='declared') & ~models.Q(license_id=''))
                | (models.Q(license_basis='owner_decision') & ~models.Q(license_justification='')),
                name='dataset_enabled_requires_license_basis',
            ),
        ),
    ]
