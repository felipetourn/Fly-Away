from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Reserva
from .permissions import EsPasajero
from .serializers import CrearReservaSerializer, ReservaSerializer
from .servicios import crear_reserva


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

