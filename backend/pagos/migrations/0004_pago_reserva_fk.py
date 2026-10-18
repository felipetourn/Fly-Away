import django.db.models.deletion
from django.db import migrations, models


def borrar_pagos_sin_reserva(apps, schema_editor):
    """Los pagos de prueba de las reservas demo no apuntan a ninguna `Reserva`: no pueden pasar a FK."""
    Pago = apps.get_model('pagos', 'Pago')
    Reserva = apps.get_model('reservas', 'Reserva')
    Pago.objects.exclude(reserva_id__in=Reserva.objects.values('id')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0003_reservademo_estado'),
        ('reservas', '0002_alter_pasaje_options'),
    ]

    operations = [
        migrations.RunPython(borrar_pagos_sin_reserva, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='pago', name='pago_un_aprobado_por_reserva'),
        migrations.RenameField(model_name='pago', old_name='reserva_id', new_name='reserva'),
        migrations.AlterField(
            model_name='pago',
            name='reserva',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name='pagos', to='reservas.reserva'
            ),
        ),
        migrations.AddConstraint(
            model_name='pago',
            constraint=models.UniqueConstraint(
                condition=models.Q(('estado', 'aprobado')), fields=('reserva',), name='pago_un_aprobado_por_reserva'
            ),
        ),
        migrations.DeleteModel(name='ReservaDemo'),
    ]
