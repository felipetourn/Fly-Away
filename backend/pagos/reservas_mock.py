"""Único punto de contacto de pagos con las reservas (`Reserva`/`Pasaje` de la app `reservas`).

Ver "Contrato entre reservas (US06) y pagos" en docs/arquitectura.md.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

from reservas.models import Reserva


def _reservas(usuario):
    return Reserva.objects.filter(pasajero=usuario).select_related(
        'pasajero', 'vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino'
    ).prefetch_related('pasajes')


def reservas_de(usuario):
    """Las reservas del pasajero."""
    return list(_reservas(usuario))


def reserva_de(usuario, reserva_id):
    """La reserva si es del pasajero; None si es ajena, no existe o el id no es un UUID."""
    try:
        return _reservas(usuario).get(id=reserva_id)
    except (Reserva.DoesNotExist, ValidationError):
        return None


def pasajes_de(reserva):
    """Un (clase, precio) por pasaje, con el precio congelado al reservar."""
    return [(p.clase, p.precio) for p in reserva.pasajes.all()]


def monto_de(reserva):
    return sum((precio for _, precio in pasajes_de(reserva)), Decimal('0'))


def reserva_de_pago(pago):
    """La reserva de un pago, sin filtrar por usuario (lo usa la confirmación de MP); None si no existe."""
    return Reserva.objects.select_related(
        'pasajero', 'vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino'
    ).prefetch_related('pasajes').filter(id=pago.reserva_id).first()


def esta_pagada(reserva):
    return reserva.estado == Reserva.Estado.PAGADA


def marcar_pagada(reserva):
    """La reserva pasa a ser una compra confirmada."""
    reserva.estado = Reserva.Estado.PAGADA
    reserva.save(update_fields=['estado'])
