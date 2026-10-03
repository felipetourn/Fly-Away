"""Reglas del ABM de vuelos (docs/superpowers/specs/2026-10-03-abm-vuelos-design.md)."""
import datetime as dt
from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Avion, Vuelo

UN_DIA = dt.timedelta(days=1)


def fechas_de_periodo(desde, hasta, dias):
    """Fechas de `desde` a `hasta` (inclusive) que caen en `dias` (0 = lunes ... 6 = domingo)."""
    rango = (desde + dt.timedelta(days=n) for n in range((hasta - desde).days + 1))
    return [fecha for fecha in rango if fecha.weekday() in dias]


def fecha_llegada_de(fecha, hora_partida, hora_llegada):
    """Si llega más temprano de lo que sale, llega al día siguiente."""
    return fecha + UN_DIA if hora_llegada < hora_partida else fecha


def ya_salio(vuelo):
    ahora = timezone.localtime()  # hora de Buenos Aires (TIME_ZONE)
    return (vuelo.fecha_operacion, vuelo.hora_partida) <= (ahora.date(), ahora.time())


def error_general(mensaje):
    return serializers.ValidationError({'non_field_errors': [mensaje]})


def exigir_modificable(vuelo):
    if vuelo.estado == Vuelo.Estado.CANCELADO:
        raise error_general('El vuelo ya está cancelado.')
    if ya_salio(vuelo):
        raise error_general('El vuelo ya salió.')


def errores_de_ruta_y_horas(origen, destino, hora_partida, hora_llegada):
    errores = {}
    if origen == destino:
        errores['destino'] = 'El destino tiene que ser distinto del origen.'
    elif origen.ciudad == destino.ciudad:
        errores['destino'] = 'Origen y destino están en la misma ciudad.'
    if hora_partida == hora_llegada:
        errores['hora_llegada'] = 'La llegada no puede ser a la misma hora que la partida.'
    return errores


def siguiente_numero():
    # ponytail: recorre los números distintos (cientos); pasar a una secuencia de la base si crecen mucho.
    usados = Vuelo.objects.order_by().values_list('numero_vuelo', flat=True).distinct()
    numeros = [int(n[3:]) for n in usados if n.startswith('FA ') and n[3:].isdigit()]
    return f'FA {max(numeros, default=999) + 1}'


def _intervalo(vuelo):
    return (
        dt.datetime.combine(vuelo.fecha_operacion, vuelo.hora_partida),
        dt.datetime.combine(vuelo.fecha_llegada, vuelo.hora_llegada),
    )


def choque_de_avion(vuelos, excluir=None):
    """Mensaje del primer vuelo activo que usa el mismo avión en un horario superpuesto, o None.

    `vuelos` pueden no estar guardados. `excluir` es el id del vuelo que se está editando.
    No contempla rotación ni dónde está el avión (fuera de alcance).
    """
    por_avion = defaultdict(list)
    for vuelo in vuelos:
        por_avion[vuelo.avion_id].append(vuelo)
    for avion_id, propios in por_avion.items():
        fechas = [v.fecha_operacion for v in propios]
        # Un día de margen a cada lado: un vuelo puede cruzar medianoche.
        existentes = Vuelo.objects.filter(
            avion_id=avion_id,
            estado=Vuelo.Estado.ACTIVO,
            fecha_operacion__range=(min(fechas) - UN_DIA, max(fechas) + UN_DIA),
        )
        if excluir:
            existentes = existentes.exclude(pk=excluir)
        por_fecha = defaultdict(list)
        for existente in existentes:
            por_fecha[existente.fecha_operacion].append(existente)
        for vuelo in propios:
            sale, llega = _intervalo(vuelo)
            for fecha in (vuelo.fecha_operacion - UN_DIA, vuelo.fecha_operacion, vuelo.fecha_operacion + UN_DIA):
                for otro in por_fecha[fecha]:
                    otro_sale, otro_llega = _intervalo(otro)
                    if sale < otro_llega and otro_sale < llega:
                        return (
                            f'{vuelo.avion.matricula} ya está asignado al {otro.numero_vuelo} '
                            f'el {otro.fecha_operacion} de {otro.hora_partida:%H:%M} a {otro.hora_llegada:%H:%M}.'
                        )
    return None


@transaction.atomic
def crear_vuelos(datos, usuario):
    """Una fila por fecha de cada período, todas o ninguna. Devuelve (numero_vuelo, cantidad).

    `datos` es el `validated_data` de AltaVueloSerializer (cada período trae sus `fechas`).
    """
    # Lock sobre toda la flota, en orden fijo: las altas van de a una, así el número correlativo
    # y el chequeo de avión libre no compiten con otra alta ni con una edición.
    # ponytail: lock global; pasar a una secuencia para el número y lock por avión si hay muchas altas a la vez.
    list(Avion.objects.select_for_update().order_by('pk'))
    numero = siguiente_numero()
    vuelos = [
        Vuelo(
            numero_vuelo=numero,
            avion=periodo['avion'],
            aeropuerto_origen=datos['origen'],
            aeropuerto_destino=datos['destino'],
            fecha_operacion=fecha,
            fecha_llegada=fecha_llegada_de(fecha, datos['hora_partida'], datos['hora_llegada']),
            hora_partida=datos['hora_partida'],
            hora_llegada=datos['hora_llegada'],
            precio_economy=periodo['precio_economy'],
            precio_primera=periodo['precio_primera'],
            asientos_disponibles_economy=periodo['avion'].capacidad_economy,
            asientos_disponibles_primera=periodo['avion'].capacidad_primera,
            creado_por=usuario,
        )
        for periodo in datos['periodos']
        for fecha in periodo['fechas']
    ]
    choque = choque_de_avion(vuelos)
    if choque:
        raise error_general(choque)
    Vuelo.objects.bulk_create(vuelos, batch_size=1000)
    return numero, len(vuelos)
