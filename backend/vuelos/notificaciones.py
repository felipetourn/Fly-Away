"""Identificación de pasajeros afectados y armado de notificaciones por cambios de vuelo (US15)."""
from collections import OrderedDict

from reservas.models import Reserva


def snapshot_horario(vuelo):
    """Captura los datos de fecha y horario de una instancia antes de editarla."""
    return {
        'fecha_operacion': vuelo.fecha_operacion,
        'fecha_llegada': vuelo.fecha_llegada,
        'hora_partida': vuelo.hora_partida,
        'hora_llegada': vuelo.hora_llegada,
    }


def cambio_el_horario(anterior, vuelo):
    """True si cambió la fecha de operación, la fecha de llegada, la hora de partida o la hora de llegada."""
    return snapshot_horario(vuelo) != anterior


def destinatarios_afectados(vuelo):
    """Pasajeros únicos con compra confirmada (`estado = pagada`) para esta instancia de vuelo.

    Agrupa por pasajero y correo de destino para que múltiples pasajes o reservas del mismo comprador
    en la misma instancia generen una única notificación por operación.
    """
    reservas = (
        Reserva.objects.filter(vuelo_id=vuelo.id, estado=Reserva.Estado.PAGADA)
        .select_related('pasajero')
        .prefetch_related('pasajes')
        .order_by('creado_en', 'id')
    )
    agrupados = OrderedDict()
    for reserva in reservas:
        usuario = reserva.pasajero
        email = (reserva.contacto_email or (usuario.email if usuario else '')).strip()
        if not email or usuario is None:
            continue
        clave = (usuario.id, email.lower())
        if clave not in agrupados:
            nombre = (reserva.contacto_nombre or f'{usuario.nombre} {usuario.apellido}').strip()
            agrupados[clave] = {
                'usuario': usuario,
                'email': email,
                'nombre': nombre,
                'codigos_pasaje': [],
            }
        for pasaje in reserva.pasajes.all():
            agrupados[clave]['codigos_pasaje'].append(pasaje.codigo_pasaje)
    return list(agrupados.values())


def mensaje_cambio_horario(vuelo, anterior):
    """Texto resumen persistido en `notificaciones.mensaje` con identificación del vuelo y horario anterior/nuevo."""
    origen = vuelo.aeropuerto_origen
    destino = vuelo.aeropuerto_destino
    return (
        f'El vuelo {vuelo.numero_vuelo} ({origen.ciudad} {origen.codigo_iata} -> '
        f'{destino.ciudad} {destino.codigo_iata}, instancia {vuelo.id}) modificó su horario. '
        f'Horario anterior: salida {anterior["fecha_operacion"]:%d/%m/%Y} {anterior["hora_partida"]:%H:%M}, '
        f'llegada {anterior["fecha_llegada"]:%d/%m/%Y} {anterior["hora_llegada"]:%H:%M}. '
        f'Nuevo horario: salida {vuelo.fecha_operacion:%d/%m/%Y} {vuelo.hora_partida:%H:%M}, '
        f'llegada {vuelo.fecha_llegada:%d/%m/%Y} {vuelo.hora_llegada:%H:%M}.'
    )
