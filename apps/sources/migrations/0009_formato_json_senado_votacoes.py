from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0008_formato_json_senado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='format',
            field=models.CharField(choices=[('csv', 'CSV'), ('zip_csv', 'ZIP com CSV'), ('json', 'JSON'), ('json_senado', 'JSON do Senado'), ('json_senado_votacoes', 'JSON das votações do Senado'), ('xml', 'XML'), ('other', 'Outro')], max_length=20, verbose_name='formato'),
        ),
    ]
