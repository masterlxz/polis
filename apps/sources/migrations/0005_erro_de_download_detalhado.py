from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0004_licenca_checagem_ckan'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingestionrun',
            name='error_detail',
            field=models.CharField(blank=True, max_length=200, verbose_name='detalhe do erro'),
        ),
    ]
