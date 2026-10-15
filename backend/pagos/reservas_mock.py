"""Reservas demo hasta la US06: único punto de contacto de pagos con las reservas.

Al integrar la US06 se reescribe sobre `Reserva`/`Pasaje` con la misma interfaz
(ver "Contrato entre reservas (US06) y pagos" en docs/arquitectura.md).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from vuelos.models import Vuelo

from .models import ReservaDemo

PEDIDOS = [('economy', 1), ('primera', 2), ('economy', 9)]  # 9 = máximo por operación


def _reservas(usuario):
    return ReservaDemo.objects.filter(pasajero=usuario).select_related('vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino')


def _vuelos_con_lugar(clase, cantidad):
    ahora = timezone.localtime()
    return Vuelo.objects.filter(
        Q(fecha_operacion__gt=ahora.date()) | Q(fecha_operacion=ahora.date(), hora_partida__gt=ahora.time()),
        estado=Vuelo.Estado.ACTIVO,
        **{f'asientos_disponibles_{clase}__gte': cantidad},
    ).order_by('fecha_operacion', 'hora_partida', 'id')


def reservas_de(usuario):
    """Las reservas demo del pasajero. La primera vez crea una por pedido, cada una en un vuelo distinto; después quedan fijas."""
    # ponytail: dos primeras llamadas simultáneas podrían crear 6; es un mock de vida corta.
    if not _reservas(usuario).exists():
        usados = []
        for clase, cantidad in PEDIDOS:
            vuelo = _vuelos_con_lugar(clase, cantidad).exclude(id__in=usados).first()
            if vuelo:
                usados.append(vuelo.id)
                ReservaDemo.objects.create(pasajero=usuario, vuelo=vuelo, clase=clase, cantidad=cantidad)
    return list(_reservas(usuario))


def reserva_de(usuario, reserva_id):
    """La reserva si es del pasajero; None si es ajena, no existe o el id no es un UUID."""
    try:
        return _reservas(usuario).get(id=reserva_id)
    except (ReservaDemo.DoesNotExist, ValidationError):
        return None


def pasajes_de(reserva):
    """Un (clase, precio) por asiento, con el precio actual de la clase en el vuelo."""
    return [(reserva.clase, getattr(reserva.vuelo, f'precio_{reserva.clase}'))] * reserva.cantidad


def monto_de(reserva):
    return sum((precio for _, precio in pasajes_de(reserva)), Decimal('0'))
