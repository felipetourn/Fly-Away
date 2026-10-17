"""Punto de contacto entre pagos y reservas.

Soporta las reservas reales (`Reserva`/`Pasaje` de la app `reservas`) y conserva compatibilidad
con `ReservaDemo` para los tests del módulo pagos.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from reservas.models import Reserva
from vuelos.models import Vuelo

from .models import ReservaDemo

PEDIDOS = [('economy', 1), ('primera', 2), ('economy', 9)]  # 9 = máximo por operación


def _reservas_demo(usuario):
    return ReservaDemo.objects.filter(pasajero=usuario).select_related('vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino')


def _reservas_reales(usuario):
    return Reserva.objects.filter(pasajero=usuario).select_related(
        'vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino'
    ).prefetch_related('pasajes')


def _vuelos_con_lugar(clase, cantidad):
    ahora = timezone.localtime()
    return Vuelo.objects.filter(
        Q(fecha_operacion__gt=ahora.date()) | Q(fecha_operacion=ahora.date(), hora_partida__gt=ahora.time()),
        estado=Vuelo.Estado.ACTIVO,
        **{f'asientos_disponibles_{clase}__gte': cantidad},
    ).order_by('fecha_operacion', 'hora_partida', 'id')


def reservas_de(usuario):
    """Devuelve las reservas del pasajero. Si tiene reservas reales, devuelve esas.

    Si no tiene ninguna reserva (demo ni real), genera las reservas demo para pruebas de pago.
    """
    reales = list(_reservas_reales(usuario))
    if reales:
        return reales

    # Fallback a demo para pruebas y tests de pagos
    if not _reservas_demo(usuario).exists():
        usados = []
        for clase, cantidad in PEDIDOS:
            vuelo = _vuelos_con_lugar(clase, cantidad).exclude(id__in=usados).first()
            if vuelo:
                usados.append(vuelo.id)
                ReservaDemo.objects.create(pasajero=usuario, vuelo=vuelo, clase=clase, cantidad=cantidad)
    return list(_reservas_demo(usuario))


def reserva_de(usuario, reserva_id):
    """La reserva si es del pasajero (real o demo); None si es ajena, no existe o el id no es un UUID."""
    try:
        # Primero busca en reservas reales
        reserva = _reservas_reales(usuario).filter(id=reserva_id).first()
        if reserva:
            return reserva
        return _reservas_demo(usuario).get(id=reserva_id)
    except (ReservaDemo.DoesNotExist, Reserva.DoesNotExist, ValidationError, ValueError):
        return None


def pasajes_de(reserva):
    """Un (clase, precio) por asiento."""
    if isinstance(reserva, Reserva):
        pasajes = list(reserva.pasajes.all())
        if pasajes:
            return [(p.clase, p.precio) for p in pasajes]
        # Fallback si no tiene pasajes cargados todavía
        clase = getattr(reserva, 'clase', 'economy')
        precio = getattr(reserva.vuelo, f'precio_{clase}')
        return [(clase, precio)] * reserva.cantidad_pasajes

    return [(reserva.clase, getattr(reserva.vuelo, f'precio_{reserva.clase}'))] * reserva.cantidad


def monto_de(reserva):
    return sum((precio for _, precio in pasajes_de(reserva)), Decimal('0'))


def reserva_de_pago(pago):
    """La reserva de un pago, sin filtrar por usuario (lo usa la confirmación de MP); None si no existe."""
    reserva = Reserva.objects.select_related('vuelo').prefetch_related('pasajes').filter(id=pago.reserva_id).first()
    if reserva:
        return reserva
    return ReservaDemo.objects.select_related('vuelo').filter(id=pago.reserva_id).first()


def marcar_pagada(reserva):
    """La reserva pasa a ser una compra confirmada (estado = 'pagada')."""
    reserva.estado = Reserva.Estado.PAGADA
    reserva.save(update_fields=['estado'])
