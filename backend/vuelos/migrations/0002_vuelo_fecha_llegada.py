from django.db import migrations, models
from django.db.models import F


def completar(apps, schema_editor):
    # Hasta acá ningún vuelo cruzaba medianoche: todos llegan el día en que salen.
    apps.get_model('vuelos', 'Vuelo').objects.update(fecha_llegada=F('fecha_operacion'))


class Migration(migrations.Migration):
    dependencies = [('vuelos', '0001_initial')]

    operations = [
        migrations.AddField(model_name='vuelo', name='fecha_llegada', field=models.DateField(null=True)),
        migrations.RunPython(completar, migrations.RunPython.noop),
    ]
