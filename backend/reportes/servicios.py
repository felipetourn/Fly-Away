"""Ocupación de los vuelos (US12, US13). Base también de la US14 (estado del vuelo desde mostrador).

Vendidos = pasajes de reservas pagadas (compras confirmadas). Capacidad = el avión actual del vuelo.
Disponibles = el contador que usa la venta. La US11 garantiza vendidos + disponibles = capacidad.
"""
from django.db.models import Count, Q

from reservas.models import Reserva

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
