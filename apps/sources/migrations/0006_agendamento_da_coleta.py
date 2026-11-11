from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sources', '0005_erro_de_download_detalhado'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='schedule_interval_hours',
            field=models.PositiveSmallIntegerField(blank=True, help_text='Vazio: o agendador não coleta este conjunto (ADR 0008, decisão 6).', null=True, verbose_name='intervalo da coleta (horas)'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='earliest_hour_utc',
            field=models.PositiveSmallIntegerField(default=0, help_text='O agendador só coleta a partir desta hora (0 a 23, UTC).', verbose_name='hora mínima da coleta (UTC)'),
        ),
        migrations.AddField(
            model_name='dataset',
            name='next_collection_at',
            field=models.DateTimeField(blank=True, help_text='Vazio: o agendador sorteia na próxima passada. Para forçar uma coleta, ponha uma data e hora já passadas.', null=True, verbose_name='próxima coleta'),
        ),
        migrations.AddConstraint(
            model_name='dataset',
            constraint=models.CheckConstraint(condition=models.Q(('schedule_interval_hours__isnull', True), ('schedule_interval_hours__gte', 1), _connector='OR'), name='dataset_schedule_interval_positive'),
        ),
        migrations.AddConstraint(
            model_name='dataset',
            constraint=models.CheckConstraint(condition=models.Q(('earliest_hour_utc__lte', 23)), name='dataset_earliest_hour_utc_range'),
        ),
    ]
