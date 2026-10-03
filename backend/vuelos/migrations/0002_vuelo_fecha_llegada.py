import datetime as dt

from django.db import migrations, models
from django.db.models import F


def completar(apps, schema_editor):
    Vuelo = apps.get_model('vuelos', 'Vuelo')
    Vuelo.objects.filter(hora_llegada__gt=F('hora_partida')).update(fecha_llegada=F('fecha_operacion'))
    # El seed nunca cruzó medianoche; esto cubre filas cargadas a mano, para que el CHECK de 0003 no frene el deploy.
    for vuelo in Vuelo.objects.filter(hora_llegada__lte=F('hora_partida')).only('fecha_operacion'):
        vuelo.fecha_llegada = vuelo.fecha_operacion + dt.timedelta(days=1)
        vuelo.save(update_fields=['fecha_llegada'])


class Migration(migrations.Migration):
    dependencies = [('vuelos', '0001_initial')]

    operations = [
        migrations.AddField(model_name='vuelo', name='fecha_llegada', field=models.DateField(null=True)),
        migrations.RunPython(completar, migrations.RunPython.noop),
    ]
