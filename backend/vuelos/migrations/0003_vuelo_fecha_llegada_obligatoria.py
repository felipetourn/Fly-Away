from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [('vuelos', '0002_vuelo_fecha_llegada')]

    operations = [
        migrations.AlterField(model_name='vuelo', name='fecha_llegada', field=models.DateField()),
        migrations.AddConstraint(
            model_name='vuelo',
            constraint=models.CheckConstraint(
                condition=Q(fecha_llegada__gt=F('fecha_operacion'))
                | Q(fecha_llegada=F('fecha_operacion'), hora_llegada__gt=F('hora_partida')),
                name='vuelo_llegada_posterior_a_partida',
            ),
        ),
    ]
