"""Ocupación de los vuelos (US12, US13). Base también de la US14 (estado del vuelo desde mostrador).

Vendidos = pasajes de reservas pagadas (compras confirmadas). Capacidad = el avión actual del vuelo.
Disponibles = el contador que usa la venta. La US11 garantiza vendidos + disponibles = capacidad.
"""
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from reservas.models import Pasaje, Reserva

CLASES = ('economy', 'primera')


def con_ocupacion(vuelos):
    """El queryset con `vendidos_<clase>` anotado, en una sola consulta."""
    return vuelos.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino').annotate(
        **{
            f'vendidos_{clase}': Count(
                'reservas__pasajes',
                filter=Q(reservas__estado=Reserva.Estado.PAGADA, reservas__pasajes__clase=clase),
            )
            for clase in CLASES
        }
    )


def _cupo(filas):
    return {campo: sum(f[campo] for f in filas) for campo in ('capacidad', 'vendidos', 'disponibles')}


def ocupacion_de(vuelo, clases=CLASES):
    """{'clases': [{clase, capacidad, vendidos, disponibles}], 'total': {...}}. `vuelo` viene de `con_ocupacion`."""
    filas = [
        {
            'clase': clase,
            'capacidad': getattr(vuelo.avion, f'capacidad_{clase}'),
            'vendidos': getattr(vuelo, f'vendidos_{clase}'),
            'disponibles': getattr(vuelo, f'asientos_disponibles_{clase}'),
        }
        for clase in clases
    ]
    return {'clases': filas, 'total': _cupo(filas)}


def totales(vuelos, clases=CLASES):
    """La misma forma que `ocupacion_de`, sumando todos los `vuelos` (un queryset, sin paginar)."""
    sumas = vuelos.order_by().aggregate(**{
        f'{campo}_{clase}': Coalesce(Sum(f'{origen}{clase}'), 0)
        for clase in clases
        for campo, origen in (('capacidad', 'avion__capacidad_'), ('disponibles', 'asientos_disponibles_'))
    })
    vendidos = dict(
        Pasaje.objects.filter(reserva__vuelo__in=vuelos.order_by().values('pk'), reserva__estado=Reserva.Estado.PAGADA)
        .order_by().values_list('clase').annotate(n=Count('pk'))
    )
    filas = [
        {
            'clase': clase,
            'capacidad': sumas[f'capacidad_{clase}'],
            'vendidos': vendidos.get(clase, 0),
            'disponibles': sumas[f'disponibles_{clase}'],
        }
        for clase in clases
    ]
    return {'clases': filas, 'total': _cupo(filas)}
