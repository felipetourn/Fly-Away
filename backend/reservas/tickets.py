import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generar_ticket_pdf(pasaje) -> bytes:
    """Genera el documento PDF del ticket electrónico individual para un pasaje.

    Incluye: pasajero (nombre, apellido, DNI), vuelo (número, avión), fecha,
    horarios, origen, destino, clase, asiento y código identificador único.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    ancho, alto = letter

    # Colores corporativos
    marino = colors.HexColor('#0f172a')
    cielo = colors.HexColor('#0284c7')
    naranja = colors.HexColor('#ea580c')
    gris_fondo = colors.HexColor('#f8fafc')
    gris_borde = colors.HexColor('#e2e8f0')
    texto_gris = colors.HexColor('#64748b')
    blanco = colors.white

    reserva = pasaje.reserva
    vuelo = reserva.vuelo
    avion = vuelo.avion
    origen = vuelo.aeropuerto_origen
    destino = vuelo.aeropuerto_destino

    # Margen y caja principal de la tarjeta de embarque
    x = 40
    y = alto - 450
    w = ancho - 80
    h = 390

    # Fondo de la tarjeta
    c.setFillColor(blanco)
    c.setStrokeColor(gris_borde)
    c.setLineWidth(1.5)
    c.roundRect(x, y, w, h, 14, fill=1, stroke=1)

    # Cabecera azul marino
    c.setFillColor(marino)
    c.roundRect(x, y + h - 75, w, 75, 14, fill=1, stroke=0)
    # Rellenar las esquinas inferiores del encabezado para que quede recto abajo
    c.rect(x, y + h - 75, w, 20, fill=1, stroke=0)

    # Texto encabezado
    c.setFillColor(blanco)
    c.setFont('Helvetica-Bold', 22)
    c.drawString(x + 24, y + h - 42, 'FLY AWAY')

    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(colors.HexColor('#38bdf8'))
    c.drawString(x + 24, y + h - 60, 'TICKET ELECTRÓNICO / BOARDING PASS')

    # Chip clase en la cabecera
    nombre_clase = pasaje.clase.upper()
    c.setFillColor(naranja)
    c.roundRect(x + w - 140, y + h - 55, 116, 26, 8, fill=1, stroke=0)
    c.setFillColor(blanco)
    c.setFont('Helvetica-Bold', 11)
    c.drawCentredString(x + w - 82, y + h - 46, f'CLASE {nombre_clase}')

    # Bloque: Código de pasaje (destacado)
    c.setFillColor(gris_fondo)
    c.roundRect(x + 20, y + h - 140, w - 40, 50, 8, fill=1, stroke=0)

    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 36, y + h - 105, 'CÓDIGO DE TICKET')

    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(x + 36, y + h - 126, pasaje.codigo_pasaje)

    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 260, y + h - 105, 'ESTADO')

    c.setFillColor(colors.HexColor('#16a34a'))
    c.setFont('Helvetica-Bold', 13)
    c.drawString(x + 260, y + h - 124, 'CONFIRMADO')

    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 400, y + h - 105, 'N° DE VUELO')

    c.setFillColor(cielo)
    c.setFont('Helvetica-Bold', 15)
    c.drawString(x + 400, y + h - 125, vuelo.numero_vuelo)

    # Separador
    c.setStrokeColor(gris_borde)
    c.setLineWidth(1)
    c.line(x + 20, y + h - 155, x + w - 20, y + h - 155)

    # Bloque: Datos del pasajero
    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 24, y + h - 175, 'PASAJERO')
    c.drawString(x + 260, y + h - 175, 'DOCUMENTO (DNI)')
    c.drawString(x + 400, y + h - 175, 'ASIENTO')

    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 13)
    nombre_completo = f'{pasaje.nombre_pasajero} {pasaje.apellido_pasajero}'.strip()
    c.drawString(x + 24, y + h - 193, nombre_completo.upper())

    c.setFont('Helvetica', 12)
    c.drawString(x + 260, y + h - 193, pasaje.dni_pasajero)

    asiento_txt = pasaje.asiento or 'Asignado en puerta'
    c.drawString(x + 400, y + h - 193, asiento_txt)

    # Separador
    c.line(x + 20, y + h - 210, x + w - 20, y + h - 210)

    # Bloque: Ruta y Horarios
    # Origen
    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 24, y + h - 230, 'ORIGEN')

    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 28)
    c.drawString(x + 24, y + h - 262, origen.codigo_iata)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(x + 24, y + h - 280, origen.ciudad)
    c.setFont('Helvetica', 9)
    c.setFillColor(texto_gris)
    c.drawString(x + 24, y + h - 294, origen.nombre[:30])

    # Destino
    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 240, y + h - 230, 'DESTINO')

    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 28)
    c.drawString(x + 240, y + h - 262, destino.codigo_iata)

    c.setFont('Helvetica-Bold', 12)
    c.drawString(x + 240, y + h - 280, destino.ciudad)
    c.setFont('Helvetica', 9)
    c.setFillColor(texto_gris)
    c.drawString(x + 240, y + h - 294, destino.nombre[:30])

    # Fechas y Horas
    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 400, y + h - 230, 'FECHA DE SALIDA')
    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(x + 400, y + h - 248, str(vuelo.fecha_operacion))

    c.setFillColor(texto_gris)
    c.setFont('Helvetica-Bold', 9)
    c.drawString(x + 400, y + h - 268, 'HORARIO')
    c.setFillColor(marino)
    c.setFont('Helvetica-Bold', 14)
    c.drawString(x + 400, y + h - 286, f'{vuelo.hora_partida.strftime("%H:%M")} → {vuelo.hora_llegada.strftime("%H:%M")}')

    # Separador inferior
    c.setStrokeColor(gris_borde)
    c.line(x + 20, y + 65, x + w - 20, y + 65)

    # Pie de la tarjeta: Información de aeronave y compra
    c.setFont('Helvetica', 9)
    c.setFillColor(texto_gris)
    c.drawString(x + 24, y + 45, f'Aeronave: {avion.modelo} ({avion.matricula})')
    c.drawString(x + 24, y + 30, f'Reserva ID: {reserva.id}')

    c.drawRightString(x + w - 24, y + 45, f'Importe pasaje: $ {pasaje.precio}')
    c.drawRightString(x + w - 24, y + 30, f'Comprador: {reserva.contacto_email}')

    # Nota al pie exterior
    c.setFont('Helvetica', 8)
    c.setFillColor(texto_gris)
    c.drawString(
        x,
        y - 25,
        'IMPORTANTE: Presentarse en el aeropuerto 2 horas antes de la partida con este comprobante y documento nacional de identidad original.',
    )
    c.drawString(
        x,
        y - 38,
        'Fly Away Líneas Aéreas S.A. - Operación sujeta a las condiciones generales de transporte aéreo.',
    )

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()
