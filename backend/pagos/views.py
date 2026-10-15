from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from . import reservas_mock
from .serializers import ReservaSerializer


class EsPasajero(BasePermission):
    """Pagar es del rol pasajero. Sin sesión, DRF responde 401; con otro rol, 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'pasajero')


class ReservasView(APIView):
    permission_classes = [EsPasajero]

    def get(self, request):
        return Response(ReservaSerializer(reservas_mock.reservas_de(request.user), many=True).data)
