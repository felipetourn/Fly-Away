from django.core.exceptions import ValidationError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pasaje, Reserva
from .permissions import EsPasajero
from .serializers import (
    CrearReservaIdaVueltaSerializer,
    CrearReservaSerializer,
    PasajeDetalleSerializer,
    ReservaSerializer,
)
from .servicios import crear_reserva, crear_reservas_ida_vuelta
from .tickets import generar_ticket_pdf


class ReservasView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request):
        """Listado de reservas del pasajero autenticado."""
        reservas = (
            Reserva.objects.filter(pasajero=request.user)
            .select_related('vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino')
            .prefetch_related('pasajes')
            .order_by('-creado_en')
        )
        return Response(ReservaSerializer(reservas, many=True).data)

    def post(self, request):
        """Crea una nueva reserva asociada al pasajero autenticado."""
        serializer = CrearReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserva = crear_reserva(usuario=request.user, **serializer.validated_data)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)


class ReservaIdaVueltaView(APIView):
    permission_classes = [EsPasajero]

    def post(self, request):
        serializer = CrearReservaIdaVueltaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ida, vuelta = crear_reservas_ida_vuelta(request.user, **serializer.validated_data)
        return Response(
            {'ida': ReservaSerializer(ida).data, 'vuelta': ReservaSerializer(vuelta).data},
            status=status.HTTP_201_CREATED,
        )


class ReservaDetalleView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request, pk):
        """Detalle de una reserva propia."""
        try:
            reserva = (
                Reserva.objects.select_related('vuelo__aeropuerto_origen', 'vuelo__aeropuerto_destino')
                .prefetch_related('pasajes')
                .get(id=pk, pasajero=request.user)
            )
        except (Reserva.DoesNotExist, ValidationError, ValueError):
            raise NotFound('No encontramos la reserva.')

        return Response(ReservaSerializer(reserva).data)


class TicketNoDisponible(APIException):
    status_code = 400
    default_detail = 'El ticket electrónico solo está disponible para compras confirmadas.'


def pasaje_pagado_o_error(usuario, codigo):
    """El pasaje si es del pasajero y la compra está confirmada; si no, 404 o 400 (el ticket no existe todavía)."""
    pasaje = (
        Pasaje.objects.select_related(
            'reserva__pasajero',
            'reserva__vuelo__avion',
            'reserva__vuelo__aeropuerto_origen',
            'reserva__vuelo__aeropuerto_destino',
        )
        .filter(codigo_pasaje=codigo, reserva__pasajero=usuario)
        .first()
    )
    if not pasaje:
        raise NotFound('No encontramos el pasaje.')
    if pasaje.reserva.estado != Reserva.Estado.PAGADA:
        raise TicketNoDisponible()
    return pasaje


class PasajeDetalleView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request, codigo):
        """Detalle del pasaje para visualización del ticket electrónico."""
        return Response(PasajeDetalleSerializer(pasaje_pagado_o_error(request.user, codigo)).data)


class TicketPdfView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request, codigo):
        """Descarga del ticket electrónico en formato PDF."""
        pasaje = pasaje_pagado_o_error(request.user, codigo)
        response = HttpResponse(generar_ticket_pdf(pasaje), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket-{pasaje.codigo_pasaje}.pdf"'
        return response
