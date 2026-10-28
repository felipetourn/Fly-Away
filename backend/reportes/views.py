from rest_framework import generics
from rest_framework.response import Response

from vuelos.models import Vuelo
from vuelos.permissions import EsAdministrador
from vuelos.serializers import VueloDetalleSerializer

from .servicios import con_ocupacion, ocupacion_de


class OcupacionVueloView(generics.RetrieveAPIView):
    """Ocupación de una instancia de vuelo (US12). Incluye cancelados y pasados; id inexistente o malformado: 404."""

    permission_classes = [EsAdministrador]
    queryset = con_ocupacion(Vuelo.objects.all())

    def retrieve(self, request, *args, **kwargs):
        vuelo = self.get_object()
        return Response({'vuelo': VueloDetalleSerializer(vuelo).data, **ocupacion_de(vuelo)})
