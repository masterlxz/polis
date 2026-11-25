from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('legislature', '0005_votacoes_da_camara'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='camaravote',
            index=models.Index(fields=['legislature_id', 'camara_id'], name='camara_vote_leg_camara_idx'),
        ),
    ]
