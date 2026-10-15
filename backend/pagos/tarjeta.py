"""Pasarela de tarjetas simulada: valida como una real y decide el resultado por el número (tarjetas de prueba)."""
import re
import uuid

APROBADO = 'Pago aprobado.'
RECHAZOS = {
    '4000000000000002': 'Tarjeta rechazada por el emisor.',
    '4000000000009995': 'Fondos insuficientes.',
    '4000000000000119': 'Error al procesar el pago. No se realizó ningún cobro; podés intentar de nuevo.',
}


def limpiar_numero(numero):
    return re.sub(r'[\s-]', '', numero)


def luhn_valido(numero):
    total = 0
    for i, digito in enumerate(reversed(numero)):
        n = int(digito)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def marca_de(numero):
    if numero.startswith('4'):
        return 'visa'
    if numero[:2] in ('34', '37'):
        return 'amex'
    if 51 <= int(numero[:2]) <= 55 or 2221 <= int(numero[:4]) <= 2720:
        return 'mastercard'
    return None


def errores_de_tarjeta(numero, titular, vencimiento, cvv, hoy):
    """{campo: mensaje}; vacío si los datos son válidos. `numero` ya sin espacios ni guiones."""
    errores = {}
    marca = None
    if not re.fullmatch(r'\d{13,19}', numero):
        errores['numero'] = 'Ingresá un número de tarjeta de 13 a 19 dígitos.'
    elif not luhn_valido(numero):
        errores['numero'] = 'El número de tarjeta no es válido.'
    else:
        marca = marca_de(numero)
        if not marca:
            errores['numero'] = 'Tarjeta no soportada. Aceptamos Visa, Mastercard y American Express.'
    if not titular.strip():
        errores['titular'] = 'Ingresá el nombre del titular.'
    fecha = re.fullmatch(r'(\d{2})/(\d{2})', vencimiento)
    if not fecha or not 1 <= int(fecha[1]) <= 12:
        errores['vencimiento'] = 'Ingresá el vencimiento como MM/AA.'
    elif (2000 + int(fecha[2]), int(fecha[1])) < (hoy.year, hoy.month):
        errores['vencimiento'] = 'La tarjeta está vencida.'
    largo = 4 if marca == 'amex' else 3
    if not re.fullmatch(rf'\d{{{largo}}}', cvv):
        errores['cvv'] = f'El código de seguridad tiene {largo} dígitos.'
    return errores


def procesar(numero):
    """(aprobado, detalle, transaccion_id) simulados según el número."""
    detalle = RECHAZOS.get(numero)
    return detalle is None, detalle or APROBADO, f'SIM-{uuid.uuid4()}'
