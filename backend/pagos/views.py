from django.core.exceptions import ValidationError
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import reservas_mock, servicios
from .models import Pago
from .serializers import PagoSerializer, ReservaSerializer, TarjetaSerializer


class EsPasajero(BasePermission):
    """Pagar es del rol pasajero. Sin sesión, DRF responde 401; con otro rol, 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'pasajero')


def reservas_por_id(usuario):
    return {reserva.id: reserva for reserva in reservas_mock.reservas_de(usuario)}


def reserva_o_404(usuario, reserva_id):
    reserva = reservas_mock.reserva_de(usuario, reserva_id)
    if reserva is None:
        raise NotFound('No encontramos la reserva.')
    return reserva


class ReservasView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request):
        return Response(ReservaSerializer(reservas_mock.reservas_de(request.user), many=True).data)


class PagosView(APIView):
    """Pagos del pasajero, del más nuevo al más viejo. No consulta a MP: muestra el estado guardado."""

    permission_classes = [EsPasajero]

    def get(self, request):
        reservas = reservas_por_id(request.user)
        pagos = Pago.objects.filter(reserva_id__in=reservas)
        return Response(PagoSerializer(pagos, many=True, context={'reservas': reservas}).data)


class PagoDetalleView(APIView):
    """Un pago propio; si es de MP y está pendiente, primero se actualiza. Id ajeno o malformado: 404."""

    permission_classes = [EsPasajero]

    def get(self, request, pk):
        reservas = reservas_por_id(request.user)
        try:
            pago = Pago.objects.get(id=pk, reserva_id__in=reservas)
        except (Pago.DoesNotExist, ValidationError):
            raise NotFound('No encontramos el pago.')
        pago = servicios.actualizar_pago(pago)
        return Response(PagoSerializer(pago, context={'reservas': reservas}).data)


class PagoTarjetaView(APIView):
    permission_classes = [EsPasajero]

    def post(self, request):
        datos = TarjetaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        reserva = reserva_o_404(request.user, datos.validated_data['reserva_id'])
        pago = servicios.pagar_con_tarjeta(reserva, datos.validated_data['numero'])
        return Response(PagoSerializer(pago, context={'reservas': {reserva.id: reserva}}).data, status=201)
