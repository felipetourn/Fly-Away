from rest_framework import generics

from .models import Aeropuerto, Vuelo
from .serializers import AeropuertoSerializer, VueloDetalleSerializer


class AeropuertosView(generics.ListAPIView):
    queryset = Aeropuerto.objects.all()
    serializer_class = AeropuertoSerializer


class VueloDetalleView(generics.RetrieveAPIView):
    """Incluye cancelados: el detalle informa la cancelación. Un id que no es UUID da 404 (no 500)."""

    queryset = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino')
    serializer_class = VueloDetalleSerializer
