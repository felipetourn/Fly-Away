import secrets

from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from vuelos.models import Vuelo
from vuelos.servicios import ya_salio

from .models import Pasaje, Reserva

MAXIMO_PASAJES = 9
MINIMO_PASAJES = 1


def validar_datos_reserva(vuelo, clase, cantidad_pasajes):
    """Valida reglas de negocio previas a la reserva."""
    if not isinstance(cantidad_pasajes, int) or cantidad_pasajes < MINIMO_PASAJES or cantidad_pasajes > MAXIMO_PASAJES:
        raise DRFValidationError({
            'cantidad_pasajes': [f'La cantidad de pasajes debe ser entre {MINIMO_PASAJES} y {MAXIMO_PASAJES}.']
        })

    if clase not in (Pasaje.Clase.ECONOMY, Pasaje.Clase.PRIMERA):
        raise DRFValidationError({'clase': ['La clase debe ser economy o primera.']})

    if vuelo.estado == Vuelo.Estado.CANCELADO:
        raise DRFValidationError({'vuelo_id': ['El vuelo fue cancelado.']})

    if ya_salio(vuelo):
        raise DRFValidationError({'vuelo_id': ['El vuelo ya salió.']})

    disponibles = getattr(vuelo, f'asientos_disponibles_{clase}')
    if disponibles < cantidad_pasajes:
        raise DRFValidationError({
            'non_field_errors': [
                f'No hay asientos suficientes disponibles en clase {clase}. Disponibles: {disponibles}.'
            ]
        })


def generar_codigo_pasaje(numero_vuelo, indice):
    """Genera un código único alfanumérico para el pasaje, ej: FA1001-A8B9C0-01."""
    prefijo = numero_vuelo.replace(' ', '').upper()
    sufijo = secrets.token_hex(3).upper()
    return f'{prefijo}-{sufijo}-{indice:02d}'


def crear_reserva(
    usuario,
    vuelo_id,
    clase,
    cantidad_pasajes,
    pasajeros,
    contacto_email=None,
    contacto_nombre=None,
    vendido_por=None,
):
    """Crea una reserva en estado 'pendiente' y sus pasajes dentro de una transacción con lock sobre el vuelo."""
    try:
        vuelo = Vuelo.objects.get(id=vuelo_id)
    except (Vuelo.DoesNotExist, ValueError, TypeError):
        raise DRFValidationError({'vuelo_id': ['El vuelo seleccionado no existe.']})

    validar_datos_reserva(vuelo, clase, cantidad_pasajes)
    if len(pasajeros) != cantidad_pasajes:
        raise DRFValidationError({'pasajeros': ['Cargá los datos de cada pasajero.']})

    email = contacto_email or (usuario.email if usuario else '')
    nombre_contacto = contacto_nombre or (f'{usuario.nombre} {usuario.apellido}'.strip() if usuario else '')
    if not email:
        raise DRFValidationError({'contacto_email': ['El correo de contacto es obligatorio.']})

    precio_unitario = getattr(vuelo, f'precio_{clase}')

    with transaction.atomic():
        # Bloqueo del vuelo para validar disponibilidad concurrente
        vuelo_bloqueado = Vuelo.objects.select_for_update().get(id=vuelo.id)
        if vuelo_bloqueado.estado == Vuelo.Estado.CANCELADO:
            raise DRFValidationError({'vuelo_id': ['El vuelo fue cancelado.']})
        if ya_salio(vuelo_bloqueado):
            raise DRFValidationError({'vuelo_id': ['El vuelo ya salió.']})

        disponibles_lock = getattr(vuelo_bloqueado, f'asientos_disponibles_{clase}')
        if disponibles_lock < cantidad_pasajes:
            raise DRFValidationError({
                'non_field_errors': [
                    f'No hay asientos suficientes disponibles en clase {clase}. Disponibles: {disponibles_lock}.'
                ]
            })

        reserva = Reserva.objects.create(
            pasajero=usuario if not vendido_por else None,
            vendido_por=vendido_por,
            contacto_email=email,
            contacto_nombre=nombre_contacto,
            vuelo=vuelo_bloqueado,
            cantidad_pasajes=cantidad_pasajes,
            estado=Reserva.Estado.PENDIENTE,
        )

        for i, datos in enumerate(pasajeros):
            # Asegurar código de pasaje único
            while True:
                codigo = generar_codigo_pasaje(vuelo.numero_vuelo, i + 1)
                if not Pasaje.objects.filter(codigo_pasaje=codigo).exists():
                    break

            Pasaje.objects.create(
                reserva=reserva,
                codigo_pasaje=codigo,
                nombre_pasajero=datos['nombre_pasajero'],
                apellido_pasajero=datos['apellido_pasajero'],
                dni_pasajero=datos['dni_pasajero'],
                clase=clase,
                precio=precio_unitario,
            )

    return reserva


def crear_reservas_ida_vuelta(usuario, vuelo_ida, vuelo_vuelta, ida, vuelta):
    """Una reserva por tramo, las dos o ninguna. La vuelta hace la ruta inversa y sale después de que aterriza la ida."""
    vuelos = Vuelo.objects.in_bulk([vuelo_ida, vuelo_vuelta])
    v_ida, v_vuelta = vuelos.get(vuelo_ida), vuelos.get(vuelo_vuelta)
    if v_ida and v_vuelta:
        if (v_vuelta.aeropuerto_origen_id, v_vuelta.aeropuerto_destino_id) != (
            v_ida.aeropuerto_destino_id, v_ida.aeropuerto_origen_id
        ):
            raise DRFValidationError({'vuelo_vuelta': ['La vuelta tiene que hacer la ruta inversa de la ida.']})
        if (v_vuelta.fecha_operacion, v_vuelta.hora_partida) <= (v_ida.fecha_llegada, v_ida.hora_llegada):
            raise DRFValidationError({'vuelo_vuelta': ['La vuelta tiene que salir después de que llega la ida.']})

    with transaction.atomic():
        return (
            crear_reserva(usuario=usuario, vuelo_id=vuelo_ida, **ida),
            crear_reserva(usuario=usuario, vuelo_id=vuelo_vuelta, **vuelta),
        )
