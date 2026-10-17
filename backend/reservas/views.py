from django.core.exceptions import ValidationError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pasaje, Reserva
from .permissions import EsPasajero
from .serializers import CrearReservaSerializer, PasajeDetalleSerializer, ReservaSerializer
from .servicios import crear_reserva
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
        datos = serializer.validated_data

        reserva = crear_reserva(
            usuario=request.user,
            vuelo_id=datos['vuelo_id'],
            clase=datos['clase'],
            cantidad_pasajes=datos['cantidad_pasajes'],
            pasajeros=datos.get('pasajeros'),
            contacto_email=datos.get('contacto_email'),
            contacto_nombre=datos.get('contacto_nombre'),
        )
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)


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


class PasajeDetalleView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request, codigo):
        """Detalle del pasaje para visualización del ticket electrónico."""
        pasaje = (
            Pasaje.objects.select_related(
                'reserva__pasajero',
                'reserva__vuelo__avion',
                'reserva__vuelo__aeropuerto_origen',
                'reserva__vuelo__aeropuerto_destino',
            )
            .filter(codigo_pasaje=codigo)
            .first()
        )
        if not pasaje:
            raise NotFound('No encontramos el pasaje.')

        if pasaje.reserva.pasajero_id != request.user.id and not request.user.is_staff:
            raise NotFound('No encontramos el pasaje.')

        if pasaje.reserva.estado != Reserva.Estado.PAGADA:
            return Response(
                {'detail': 'El ticket electrónico solo está disponible para compras confirmadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(PasajeDetalleSerializer(pasaje).data)


class TicketPdfView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request, codigo):
        """Descarga del ticket electrónico en formato PDF."""
        pasaje = (
            Pasaje.objects.select_related(
                'reserva__pasajero',
                'reserva__vuelo__avion',
                'reserva__vuelo__aeropuerto_origen',
                'reserva__vuelo__aeropuerto_destino',
            )
            .filter(codigo_pasaje=codigo)
            .first()
        )
        if not pasaje:
            raise NotFound('No encontramos el pasaje.')

        if pasaje.reserva.pasajero_id != request.user.id and not request.user.is_staff:
            raise NotFound('No encontramos el pasaje.')

        if pasaje.reserva.estado != Reserva.Estado.PAGADA:
            return Response(
                {'detail': 'El ticket electrónico solo está disponible para compras confirmadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pdf_bytes = generar_ticket_pdf(pasaje)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket-{pasaje.codigo_pasaje}.pdf"'
        return response

