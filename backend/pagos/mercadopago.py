"""Cliente mínimo de la API de Orders de Mercado Pago (Checkout Pro). Son tres llamadas: urllib alcanza, sin SDK."""
import http.client
import json
import urllib.request

from django.conf import settings

API = 'https://api.mercadopago.com/v1/orders'
MOTIVOS = {
    'card_insufficient_amount': 'Fondos insuficientes.',
    'rejected_by_issuer': 'Tarjeta rechazada por el emisor.',
    'high_risk': 'Rechazado por prevención de fraude.',
}


class ErrorMercadoPago(Exception):
    """Sin token, sin conexión, timeout o respuesta inesperada de MP."""


def _llamar(metodo, url, cuerpo=None, idempotencia=None):
    if not settings.MP_ACCESS_TOKEN:
        raise ErrorMercadoPago('Falta MP_ACCESS_TOKEN.')
    headers = {'Authorization': f'Bearer {settings.MP_ACCESS_TOKEN}', 'Content-Type': 'application/json'}
    if idempotencia:
        headers['X-Idempotency-Key'] = idempotencia
    datos = None if cuerpo is None else json.dumps(cuerpo).encode()
    pedido = urllib.request.Request(url, data=datos, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=10) as respuesta:
            return json.loads(respuesta.read())
    # OSError cubre URLError, timeouts y conexiones cortadas; HTTPException, una respuesta cortada a la mitad.
    except (OSError, http.client.HTTPException, ValueError) as error:
        raise ErrorMercadoPago(str(error)) from error


def crear_orden(pago, items):
    """items: [(título, cantidad, precio unitario)]. Devuelve (order_id, checkout_url)."""
    retorno = f'{settings.FRONTEND_URL}/pagos/{pago.id}'
    orden = _llamar('POST', API, {
        'type': 'online',
        'processing_mode': 'manual',
        'total_amount': str(pago.monto),
        'external_reference': str(pago.id),
        'expiration_time': 'PT30M',
        'items': [{'title': titulo, 'quantity': cantidad, 'unit_price': str(precio)} for titulo, cantidad, precio in items],
        'config': {'online': {'success_url': retorno, 'failure_url': retorno, 'pending_url': retorno, 'auto_return': 'all'}},
    }, idempotencia=str(pago.id))
    try:
        return orden['id'], orden['checkout_url']
    except KeyError as error:
        raise ErrorMercadoPago(f'Respuesta sin {error}') from error


def consultar_orden(order_id):
    """(status, status_detail) de la orden."""
    orden = _llamar('GET', f'{API}/{order_id}')
    return orden.get('status'), orden.get('status_detail')


def cancelar_orden(order_id):
    _llamar('POST', f'{API}/{order_id}/cancel', idempotencia=f'cancelar-{order_id}')


def resultado_de(status, status_detail):
    """(estado del Pago, detalle para el pasajero) según la orden. Nunca se usan los parámetros de la URL de retorno."""
    if status == 'processed' and status_detail == 'accredited':
        return 'aprobado', 'Pago aprobado.'
    if status == 'refunded' or status_detail in ('refunded', 'partially_refunded'):
        return 'rechazado', 'El pago fue devuelto.'
    if status == 'failed':
        return 'rechazado', MOTIVOS.get(status_detail, 'Mercado Pago rechazó el pago.')
    if status in ('canceled', 'expired'):
        return 'rechazado', 'El pago no se completó a tiempo.'
    return 'pendiente', 'Estamos esperando la confirmación de Mercado Pago.'
