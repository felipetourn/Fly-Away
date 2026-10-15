"""Reglas de pago (US07). Las llamadas a Mercado Pago nunca van dentro de transaction.atomic()."""
import datetime as dt
from collections import Counter

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException

from vuelos.models import Vuelo
from vuelos.servicios import error_general, ya_salio

from . import mercadopago, reservas_mock, tarjeta
from .models import Pago

YA_PAGADA = 'Reserva ya pagada con otro pago: corresponde devolución.'
EN_PROCESO = 'Tenés un pago de Mercado Pago en proceso para esta reserva.'
SIN_CONEXION = 'No pudimos conectar con Mercado Pago.'
ESPERANDO = 'Estamos esperando la confirmación de Mercado Pago.'
SIN_ORDEN_MARGEN = dt.timedelta(minutes=2)  # más que el timeout de crear_orden (10 s)


class Conflicto(APIException):
    status_code = 409
    default_detail = 'La reserva ya está pagada.'


class ErrorDeMercadoPago(APIException):
    status_code = 502
    default_detail = SIN_CONEXION


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


def _sincronizar(pago):
    """Consulta la orden de un pago de MP pendiente y guarda el resultado si ya se resolvió.

    Devuelve el status de MP, o None si no se pudo consultar (el pago sigue pendiente).
    """
    if not pago.transaccion_externa_id:
        # La orden nunca se guardó (crear_orden en curso o el proceso se cortó). Pasado el margen, no hay nada que cobrar.
        if timezone.now() - pago.creado_en < SIN_ORDEN_MARGEN:
            return None
        _resolver(pago, Pago.Estado.RECHAZADO, 'No se pudo iniciar el pago en Mercado Pago.')
        return 'canceled'
    try:
        status_mp, detalle_mp = mercadopago.consultar_orden(pago.transaccion_externa_id)
    except mercadopago.ErrorMercadoPago:
        return None
    estado, detalle = mercadopago.resultado_de(status_mp, detalle_mp)
    if estado != Pago.Estado.PENDIENTE:
        _resolver(pago, estado, detalle)
    return status_mp


def _resolver(pago, estado, detalle):
    """Guarda el resultado solo si el pago sigue pendiente (otro pedido pudo resolverlo antes)."""
    with transaction.atomic():
        bloqueado = Pago.objects.select_for_update().get(id=pago.id)
        if bloqueado.estado == Pago.Estado.PENDIENTE:
            guardar_resultado(bloqueado, estado, detalle)


def actualizar_pago(pago):
    """El pago con su estado al día: si es de MP y está pendiente, consulta la orden."""
    if pago.metodo_pago == Pago.Metodo.MERCADOPAGO and pago.estado == Pago.Estado.PENDIENTE:
        _sincronizar(pago)
        pago.refresh_from_db()
    return pago


def liberar_pendientes_de_mp(reserva):
    """Antes de otro intento: actualiza los pagos de MP pendientes y cancela las órdenes que nadie pagó.

    Una orden en proceso (o que no se puede consultar) bloquea el intento: evita cobrar dos veces.
    """
    pendientes = Pago.objects.filter(
        reserva_id=reserva.id, metodo_pago=Pago.Metodo.MERCADOPAGO, estado=Pago.Estado.PENDIENTE
    )
    for pago in pendientes:
        status_mp = _sincronizar(pago)
        if status_mp == 'created':
            try:
                mercadopago.cancelar_orden(pago.transaccion_externa_id)
            except mercadopago.ErrorMercadoPago:
                raise Conflicto(EN_PROCESO)
            _resolver(pago, Pago.Estado.RECHAZADO, 'Reemplazado por un nuevo intento de pago.')
        elif status_mp is None or status_mp in ('processing', 'action_required'):
            raise Conflicto(EN_PROCESO)


def _items(reserva):
    """Un ítem por clase para la orden de MP; la suma da el monto."""
    vuelo = reserva.vuelo
    ruta = f'{vuelo.numero_vuelo} {vuelo.aeropuerto_origen.codigo_iata} → {vuelo.aeropuerto_destino.codigo_iata}'
    return [
        (f'Vuelo {ruta}, {clase}', cantidad, precio)
        for (clase, precio), cantidad in Counter(reservas_mock.pasajes_de(reserva)).items()
    ]


def pagar_con_mercadopago(reserva):
    """Crea el pago pendiente (commit), pide la orden a MP fuera de la transacción y devuelve (pago, checkout_url)."""
    liberar_pendientes_de_mp(reserva)
    with transaction.atomic():
        reserva.vuelo = validar_reserva(reserva)
        pago = Pago.objects.create(
            reserva_id=reserva.id,
            monto=reservas_mock.monto_de(reserva),
            metodo_pago=Pago.Metodo.MERCADOPAGO,
            detalle=ESPERANDO,
        )
    try:
        order_id, checkout_url = mercadopago.crear_orden(pago, _items(reserva))
    except Exception as error:
        # Cualquier falla deja el pago rechazado: un pendiente sin orden bloquearía la reserva.
        guardar_resultado(pago, Pago.Estado.RECHAZADO, SIN_CONEXION)
        if isinstance(error, mercadopago.ErrorMercadoPago):
            raise ErrorDeMercadoPago() from error
        raise
    pago.transaccion_externa_id = order_id
    pago.save(update_fields=['transaccion_externa_id'])
    return pago, checkout_url


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
