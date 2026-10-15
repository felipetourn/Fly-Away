"""Reglas de pago (US07). Las llamadas a Mercado Pago nunca van dentro de transaction.atomic()."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from vuelos.models import Vuelo
from vuelos.servicios import error_general, ya_salio

from . import reservas_mock, tarjeta
from .models import Pago

YA_PAGADA = 'Reserva ya pagada con otro pago: corresponde devolución.'
EN_PROCESO = 'Tenés un pago de Mercado Pago en proceso para esta reserva.'


class Conflicto(APIException):
    status_code = 409
    default_detail = 'La reserva ya está pagada.'


def validar_reserva(reserva):
    """Chequeos para cobrar, con el vuelo bloqueado. Llamar dentro de transaction.atomic(). Devuelve el vuelo bloqueado."""
    vuelo = Vuelo.objects.select_for_update().get(id=reserva.vuelo_id)
    pagos = Pago.objects.filter(reserva_id=reserva.id)
    if pagos.filter(estado=Pago.Estado.APROBADO).exists():
        raise Conflicto()
    if pagos.filter(estado=Pago.Estado.PENDIENTE, metodo_pago=Pago.Metodo.MERCADOPAGO).exists():
        raise Conflicto(EN_PROCESO)
    if vuelo.estado == Vuelo.Estado.CANCELADO:
        raise error_general('El vuelo fue cancelado.')
    if ya_salio(vuelo):
        raise error_general('El vuelo ya salió.')
    # ponytail: las reservas demo no retienen asientos; si la Reserva de la US06 los retiene, este chequeo cambia.
    if getattr(vuelo, f'asientos_disponibles_{reserva.clase}') < reserva.cantidad:
        raise error_general('No quedan asientos suficientes en el vuelo.')
    return vuelo


def guardar_resultado(pago, estado, detalle):
    """Guarda el resultado. Si el constraint frena un segundo aprobado, el pago queda rechazado (no 500)."""
    pago.estado, pago.detalle = estado, detalle
    pago.procesado_en = None if estado == Pago.Estado.PENDIENTE else timezone.now()
    try:
        with transaction.atomic():
            pago.save()
    except IntegrityError:
        pago.estado, pago.detalle = Pago.Estado.RECHAZADO, YA_PAGADA
        pago.save()


def liberar_pendientes_de_mp(reserva):
    """Antes de otro intento. Se completa con Mercado Pago."""


def actualizar_pago(pago):
    """El pago con su estado al día. Se completa con Mercado Pago."""
    return pago


def pagar_con_tarjeta(reserva, numero):
    liberar_pendientes_de_mp(reserva)
    aprobado, detalle, transaccion = tarjeta.procesar(numero)
    with transaction.atomic():
        reserva.vuelo = validar_reserva(reserva)
        pago = Pago(
            reserva_id=reserva.id,
            monto=reservas_mock.monto_de(reserva),
            metodo_pago=Pago.Metodo.TARJETA,
            ultimos_4=numero[-4:],
            transaccion_externa_id=transaccion,
        )
        guardar_resultado(pago, Pago.Estado.APROBADO if aprobado else Pago.Estado.RECHAZADO, detalle)
    return pago
