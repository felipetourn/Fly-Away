"""Identificación de pasajeros afectados y envío de notificaciones por cambios o cancelación de vuelo (US15, US16)."""
from collections import OrderedDict
import logging
import smtplib

from anymail.exceptions import AnymailError
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

from reservas.models import Reserva

from .models import Notificacion

logger = logging.getLogger(__name__)


def snapshot_horario(vuelo):
    """Captura los datos de fecha y horario de una instancia antes de editarla."""
    return {
        'fecha_operacion': vuelo.fecha_operacion,
        'fecha_llegada': vuelo.fecha_llegada,
        'hora_partida': vuelo.hora_partida,
        'hora_llegada': vuelo.hora_llegada,
    }


def cambio_el_horario(anterior, vuelo):
    """True si cambió la fecha de operación, la fecha de llegada, la hora de partida o la hora de llegada."""
    return snapshot_horario(vuelo) != anterior


def destinatarios_afectados(vuelo):
    """Pasajeros únicos con compra confirmada (`estado = pagada`) para esta instancia de vuelo.

    Agrupa por pasajero y correo de destino para que múltiples pasajes o reservas del mismo comprador
    en la misma instancia generen una única notificación por operación.
    """
    reservas = (
        Reserva.objects.filter(vuelo_id=vuelo.id, estado=Reserva.Estado.PAGADA)
        .select_related('pasajero')
        .prefetch_related('pasajes')
        .order_by('creado_en', 'id')
    )
    agrupados = OrderedDict()
    for reserva in reservas:
        usuario = reserva.pasajero
        email = (reserva.contacto_email or (usuario.email if usuario else '')).strip()
        if not email or usuario is None:
            continue
        clave = (usuario.id, email.lower())
        if clave not in agrupados:
            nombre = (reserva.contacto_nombre or f'{usuario.nombre} {usuario.apellido}').strip()
            agrupados[clave] = {
                'usuario': usuario,
                'email': email,
                'nombre': nombre,
                'codigos_pasaje': [],
            }
        for pasaje in reserva.pasajes.all():
            agrupados[clave]['codigos_pasaje'].append(pasaje.codigo_pasaje)
    return list(agrupados.values())


def mensaje_cambio_horario(vuelo, anterior):
    """Texto resumen persistido en `notificaciones.mensaje` con identificación del vuelo y horario anterior/nuevo."""
    origen = vuelo.aeropuerto_origen
    destino = vuelo.aeropuerto_destino
    return (
        f'El vuelo {vuelo.numero_vuelo} ({origen.ciudad} {origen.codigo_iata} -> '
        f'{destino.ciudad} {destino.codigo_iata}, instancia {vuelo.id}) modificó su horario. '
        f'Horario anterior: salida {anterior["fecha_operacion"]:%d/%m/%Y} {anterior["hora_partida"]:%H:%M}, '
        f'llegada {anterior["fecha_llegada"]:%d/%m/%Y} {anterior["hora_llegada"]:%H:%M}. '
        f'Nuevo horario: salida {vuelo.fecha_operacion:%d/%m/%Y} {vuelo.hora_partida:%H:%M}, '
        f'llegada {vuelo.fecha_llegada:%d/%m/%Y} {vuelo.hora_llegada:%H:%M}.'
    )


def mensaje_cancelacion(vuelo):
    """Texto resumen persistido en `notificaciones.mensaje` con identificación del vuelo cancelado."""
    origen = vuelo.aeropuerto_origen
    destino = vuelo.aeropuerto_destino
    return (
        f'El vuelo {vuelo.numero_vuelo} ({origen.ciudad} {origen.codigo_iata} -> '
        f'{destino.ciudad} {destino.codigo_iata}, instancia {vuelo.id}) programado para el '
        f'{vuelo.fecha_operacion:%d/%m/%Y} a las {vuelo.hora_partida:%H:%M} '
        f'(llegada {vuelo.fecha_llegada:%d/%m/%Y} a las {vuelo.hora_llegada:%H:%M}) fue cancelado.'
    )


def enviar_notificacion_cambio_horario(notificacion_id, email_destino, nombre, anterior, codigos_pasaje):
    """Envía por correo la notificación tras el commit; cualquier error queda registrado sin revertir el cambio."""
    try:
        notificacion = (
            Notificacion.objects.select_related('vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino', 'usuario')
            .get(id=notificacion_id)
        )
    except Notificacion.DoesNotExist:
        logger.error('No se pudo enviar la notificación %s: no existe.', notificacion_id)
        return False

    if notificacion.enviado:
        return True

    vuelo = notificacion.vuelo
    contexto = {
        'vuelo': vuelo,
        'anterior': anterior,
        'nombre': nombre,
        'codigos_pasaje': codigos_pasaje,
        'mensaje': notificacion.mensaje,
    }
    try:
        texto = render_to_string('vuelos/emails/cambio_horario.txt', contexto)
        html = render_to_string('vuelos/emails/cambio_horario.html', contexto)
        correo = EmailMultiAlternatives(
            subject=f'Modificación de horario - Vuelo {vuelo.numero_vuelo} ({vuelo.fecha_operacion:%d/%m/%Y})',
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_destino],
        )
        correo.attach_alternative(html, 'text/html')
        enviados = correo.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, AnymailError, Exception):
        logger.exception('Falló el envío de la notificación %s a %s.', notificacion.id, email_destino)
        return False

    if enviados != 1:
        logger.error('El proveedor de correo no confirmó el envío de la notificación %s a %s.', notificacion.id, email_destino)
        return False

    Notificacion.objects.filter(id=notificacion.id).update(enviado=True)
    return True


def programar_notificaciones_cambio_horario(vuelo, anterior):
    """Registra una `Notificacion` por pasajero afectado y agenda su envío por email tras el commit."""
    destinatarios = destinatarios_afectados(vuelo)
    if not destinatarios:
        return []

    mensaje = mensaje_cambio_horario(vuelo, anterior)
    creadas = []
    for dest in destinatarios:
        notificacion = Notificacion.objects.create(
            usuario=dest['usuario'],
            vuelo=vuelo,
            tipo=Notificacion.Tipo.CAMBIO_HORARIO,
            mensaje=mensaje,
            enviado=False,
        )
        creadas.append(notificacion)
        transaction.on_commit(
            lambda nid=notificacion.id, email=dest['email'], nombre=dest['nombre'], ant=dict(anterior), codigos=list(dest['codigos_pasaje']): (
                enviar_notificacion_cambio_horario(nid, email, nombre, ant, codigos)
            ),
            robust=True,
        )
    return creadas
