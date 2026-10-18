"""Generación y envío de la factura electrónica de una compra confirmada."""
import io
import logging
import smtplib

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from reservas.models import Reserva

from . import reservas_mock
from .models import Pago

logger = logging.getLogger(__name__)


def generar_numero_factura(pago):
    """Asigna un identificador determinista y único a la factura de este pago."""
    anio = timezone.localtime(pago.procesado_en).year
    return f'FA-{anio}-{pago.id.hex[:20].upper()}'


def _datos_factura(pago, reserva):
    vuelo = reserva.vuelo
    if isinstance(reserva, Reserva):
        pasajeros = [
            {
                'nombre': f'{pasaje.nombre_pasajero} {pasaje.apellido_pasajero}'.strip(),
                'dni': pasaje.dni_pasajero,
                'clase': pasaje.get_clase_display(),
                'codigo': pasaje.codigo_pasaje,
                'precio': pasaje.precio,
            }
            for pasaje in reserva.pasajes.all()
        ]
        destinatario = reserva.contacto_email or (reserva.pasajero.email if reserva.pasajero_id else '')
        comprador = reserva.contacto_nombre
        if not comprador and reserva.pasajero_id:
            comprador = f'{reserva.pasajero.nombre} {reserva.pasajero.apellido}'.strip()
    else:
        pasajeros = [
            {
                'nombre': f'Pasajero {indice}',
                'dni': '—',
                'clase': clase.title(),
                'codigo': '—',
                'precio': precio,
            }
            for indice, (clase, precio) in enumerate(reservas_mock.pasajes_de(reserva), start=1)
        ]
        destinatario = reserva.pasajero.email
        comprador = f'{reserva.pasajero.nombre} {reserva.pasajero.apellido}'.strip()

    return {
        'pago': pago,
        'reserva': reserva,
        'vuelo': vuelo,
        'pasajeros': pasajeros,
        'destinatario': destinatario,
        'comprador': comprador,
        'fecha_pago': timezone.localtime(pago.procesado_en),
        'metodo_pago': pago.get_metodo_pago_display(),
        'numero_factura': pago.numero_factura,
    }


def generar_factura_pdf(datos):
    """Crea el PDF del comprobante con el detalle del pago, vuelo y pasajeros."""
    buffer = io.BytesIO()
    documento = canvas.Canvas(buffer, pagesize=letter)
    ancho, alto = letter
    margen = 48

    documento.setFillColor(colors.HexColor('#0f172a'))
    documento.rect(0, alto - 112, ancho, 112, fill=1, stroke=0)
    documento.setFillColor(colors.white)
    documento.setFont('Helvetica-Bold', 22)
    documento.drawString(margen, alto - 48, 'FLY AWAY')
    documento.setFont('Helvetica-Bold', 14)
    documento.drawString(margen, alto - 76, 'FACTURA / COMPROBANTE DE PAGO')
    documento.setFont('Helvetica', 10)
    documento.drawRightString(ancho - margen, alto - 48, datos['numero_factura'])

    pago = datos['pago']
    reserva = datos['reserva']
    vuelo = datos['vuelo']
    origen = vuelo.aeropuerto_origen
    destino = vuelo.aeropuerto_destino
    y = alto - 150

    documento.setFillColor(colors.HexColor('#0f172a'))
    documento.setFont('Helvetica-Bold', 11)
    documento.drawString(margen, y, 'DATOS DE LA OPERACIÓN')
    y -= 23
    documento.setFont('Helvetica', 10)
    documento.drawString(margen, y, f'Fecha: {datos["fecha_pago"].strftime("%d/%m/%Y %H:%M")}')
    documento.drawString(margen + 250, y, f'Medio: {datos["metodo_pago"]}')
    y -= 18
    documento.drawString(margen, y, f'Reserva: {reserva.id}')
    y -= 17
    documento.drawString(margen, y, f'Comprador: {datos["comprador"]}'[:80])
    y -= 17
    documento.drawString(margen, y, f'Email: {datos["destinatario"]}'[:100])
    y -= 30

    documento.setFont('Helvetica-Bold', 11)
    documento.drawString(margen, y, 'DATOS DEL VUELO')
    y -= 21
    documento.setFont('Helvetica', 10)
    documento.drawString(margen, y, f'Vuelo {vuelo.numero_vuelo}: {origen.codigo_iata} - {destino.codigo_iata}')
    y -= 17
    documento.drawString(
        margen,
        y,
        f'Salida: {vuelo.fecha_operacion:%d/%m/%Y} {vuelo.hora_partida:%H:%M}',
    )
    y -= 30

    documento.setFont('Helvetica-Bold', 11)
    documento.drawString(margen, y, 'PASAJEROS Y PASAJES')
    y -= 20
    documento.setFont('Helvetica-Bold', 9)
    documento.drawString(margen, y, 'PASAJERO / DNI')
    documento.drawString(margen + 260, y, 'CLASE')
    documento.drawRightString(ancho - margen, y, 'IMPORTE')
    y -= 15
    documento.setStrokeColor(colors.HexColor('#cbd5e1'))
    documento.line(margen, y + 8, ancho - margen, y + 8)

    documento.setFont('Helvetica', 9)
    for pasajero in datos['pasajeros']:
        documento.drawString(margen, y, f'{pasajero["nombre"]} / DNI {pasajero["dni"]}'[:50])
        documento.drawString(margen + 260, y, pasajero['clase'])
        documento.drawRightString(ancho - margen, y, f'$ {pasajero["precio"]:.2f}')
        y -= 18

    y -= 18
    documento.setStrokeColor(colors.HexColor('#cbd5e1'))
    documento.line(margen, y + 8, ancho - margen, y + 8)
    documento.setFont('Helvetica-Bold', 13)
    documento.drawRightString(ancho - margen, y - 12, f'TOTAL PAGADO: $ {pago.monto:.2f}')
    documento.setFont('Helvetica', 8)
    documento.setFillColor(colors.HexColor('#64748b'))
    documento.drawString(margen, margen, 'Comprobante emitido por Fly Away para una compra confirmada.')
    documento.save()

    buffer.seek(0)
    return buffer.getvalue()


def enviar_factura_confirmada(pago_id):
    """Envía la factura después del commit; cualquier fallo deja la compra confirmada."""
    try:
        pago = Pago.objects.get(id=pago_id)
    except Pago.DoesNotExist:
        logger.error('No se pudo enviar la factura: no existe el pago %s.', pago_id)
        return False

    if pago.estado != Pago.Estado.APROBADO or not pago.numero_factura or not pago.procesado_en:
        logger.error('No se envió factura para el pago %s porque no está confirmado.', pago_id)
        return False

    reserva = reservas_mock.reserva_de_pago(pago)
    if reserva is None:
        logger.error('No se envió la factura %s: no existe la reserva asociada.', pago.numero_factura)
        return False

    datos = _datos_factura(pago, reserva)
    if not datos['destinatario']:
        logger.error('No se envió la factura %s: la compra no tiene correo de contacto.', pago.numero_factura)
        return False

    pdf = generar_factura_pdf(datos)
    texto = render_to_string('pagos/emails/factura.txt', datos)
    html = render_to_string('pagos/emails/factura.html', datos)
    correo = EmailMultiAlternatives(
        subject=f'Factura electrónica Fly Away - {pago.numero_factura}',
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[datos['destinatario']],
    )
    correo.attach_alternative(html, 'text/html')
    correo.attach(f'factura-{pago.numero_factura}.pdf', pdf, 'application/pdf')

    try:
        enviados = correo.send(fail_silently=False)
    except (OSError, smtplib.SMTPException):
        logger.exception('Falló el envío de la factura %s a %s.', pago.numero_factura, datos['destinatario'])
        return False

    if enviados != 1:
        logger.error('El backend de correo no confirmó el envío de la factura %s.', pago.numero_factura)
        return False
    return True
