"""Reglas de pago (US07) y confirmación de la venta (US08). Las llamadas a MP nunca van dentro de transaction.atomic()."""
import datetime as dt
from collections import Counter

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import APIException

from vuelos.models import Vuelo
from vuelos.servicios import error_general, ya_salio

from . import mercadopago, reservas_mock, tarjeta
from .models import Pago, ReservaDemo

YA_PAGADA = 'Reserva ya pagada con otro pago: corresponde devolución.'
SIN_ASIENTOS = 'No quedaban asientos al confirmar el pago: corresponde devolución.'
VUELO_NO_DISPONIBLE = 'El vuelo ya no está disponible: corresponde devolución.'
EN_PROCESO = 'Tenés un pago de Mercado Pago en proceso para esta reserva.'
SIN_CONEXION = 'No pudimos conectar con Mercado Pago.'
ESPERANDO = 'Estamos esperando la confirmación de Mercado Pago.'
SIN_ORDEN_MARGEN = dt.timedelta(minutes=2)  # más que el timeout de crear_orden (10 s)


class Conflicto(APIException):
    status_code = 409
    default_detail = 'La reserva ya está pagada.'


class SinConexionMercadoPago(APIException):
    status_code = 502
    default_detail = SIN_CONEXION


def validar_reserva(reserva):
    """Chequeos para cobrar, con el vuelo bloqueado. Llamar dentro de transaction.atomic(). Devuelve el vuelo bloqueado."""
    vuelo = Vuelo.objects.select_for_update().get(id=reserva.vuelo_id)
    reserva.refresh_from_db(fields=['estado'])  # leída antes del lock
    if reserva.estado == ReservaDemo.Estado.PAGADA:
        raise Conflicto()
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
    if _motivo_sin_lugar(reserva, vuelo):
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


def _pasajes_por_clase(reserva):
    return Counter(clase for clase, _ in reservas_mock.pasajes_de(reserva))


def _motivo_sin_lugar(reserva, vuelo):
    for clase, cantidad in _pasajes_por_clase(reserva).items():
        if getattr(vuelo, f'asientos_disponibles_{clase}') < cantidad:
            return SIN_ASIENTOS
    return None


def _motivo_para_no_vender(reserva, vuelo):
    if reserva.estado == ReservaDemo.Estado.PAGADA:
        return YA_PAGADA
    if vuelo.estado == Vuelo.Estado.CANCELADO or ya_salio(vuelo):
        return VUELO_NO_DISPONIBLE
    return _motivo_sin_lugar(reserva, vuelo)


def confirmar_compra(pago, detalle, **datos):
    """Único camino a `aprobado` (US08): pago aprobado + reserva pagada + asientos descontados, o nada.

    Bloquea vuelo y después pago, y relee la reserva con el vuelo bloqueado. Si ya no se puede vender,
    el pago queda rechazado con el motivo ("corresponde devolución"). `datos`: marca y cuenta_mp del medio.
    """
    reserva = reservas_mock.reserva_de_pago(pago)
    with transaction.atomic():
        vuelo = Vuelo.objects.select_for_update().get(id=reserva.vuelo_id)
        pago = Pago.objects.select_for_update().get(id=pago.id)
        if pago.estado != Pago.Estado.PENDIENTE:
            return pago  # ya resuelto: una transacción no confirma dos veces
        reserva = reservas_mock.reserva_de_pago(pago)
        for campo, valor in datos.items():
            setattr(pago, campo, valor)
        motivo = _motivo_para_no_vender(reserva, vuelo)
        if motivo:
            guardar_resultado(pago, Pago.Estado.RECHAZADO, motivo)
            return pago
        try:
            with transaction.atomic():  # los tres efectos juntos, o ninguno
                for clase, cantidad in _pasajes_por_clase(reserva).items():
                    campo = f'asientos_disponibles_{clase}'
                    Vuelo.objects.filter(id=vuelo.id).update(**{campo: F(campo) - cantidad})
                reservas_mock.marcar_pagada(reserva)
                pago.estado, pago.detalle, pago.procesado_en = Pago.Estado.APROBADO, detalle, timezone.now()
                pago.save()
        except IntegrityError:
            guardar_resultado(pago, Pago.Estado.RECHAZADO, YA_PAGADA)
        return pago


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
        orden = mercadopago.consultar_orden(pago.transaccion_externa_id)
    except mercadopago.ErrorMercadoPago:
        return None
    status_mp = orden.get('status')
    estado, detalle = mercadopago.resultado_de(status_mp, orden.get('status_detail'))
    if estado != Pago.Estado.PENDIENTE:
        marca = mercadopago.marca_de_orden(orden)
        _resolver(pago, estado, detalle, marca=marca, cuenta_mp=mercadopago.cuenta_del_comprador(str(pago.id)))
    return status_mp


def _resolver(pago, estado, detalle, **datos):
    """Guarda el resultado (y `datos` del medio) solo si el pago sigue pendiente (otro pedido pudo resolverlo antes)."""
    with transaction.atomic():
        bloqueado = Pago.objects.select_for_update().get(id=pago.id)
        if bloqueado.estado == Pago.Estado.PENDIENTE:
            for campo, valor in datos.items():
                setattr(bloqueado, campo, valor)
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
            raise SinConexionMercadoPago() from error
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
            marca=tarjeta.marca_de(numero),
            transaccion_externa_id=transaccion,
        )
        pago.save()  # pendiente: la aprobación pasa por confirmar_compra
        if aprobado:
            pago = confirmar_compra(pago, detalle)
        else:
            guardar_resultado(pago, Pago.Estado.RECHAZADO, detalle)
    return pago
