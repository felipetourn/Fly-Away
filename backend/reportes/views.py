import uuid

from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from vuelos.models import Vuelo
from vuelos.permissions import EsAdministrador
from vuelos.serializers import VueloDetalleSerializer, VueloSerializer

from .serializers import FiltrosReporteSerializer
from .servicios import CLASES, con_ocupacion, ocupacion_de, totales


class OcupacionVueloView(generics.RetrieveAPIView):
    """Ocupación de una instancia de vuelo (US12). Incluye cancelados y pasados; id inexistente o malformado: 404."""

    permission_classes = [EsAdministrador]
    queryset = con_ocupacion(Vuelo.objects.all())

    def retrieve(self, request, *args, **kwargs):
        vuelo = self.get_object()
        return Response({'vuelo': VueloDetalleSerializer(vuelo).data, **ocupacion_de(vuelo)})


class PaginacionReporte(PageNumberPagination):
    """De a 50, como el listado de vuelos, más los totales de todo el filtro (no solo de la página)."""

    page_size = 50

    def get_paginated_response(self, data):
        respuesta = super().get_paginated_response(data)
        respuesta.data['totales'] = self.totales
        return respuesta


class ReporteOcupacionView(generics.ListAPIView):
    """Reporte de ocupación (US13): una fila por instancia, con filtros por vuelo, fechas, origen, destino y clase."""

    permission_classes = [EsAdministrador]
    pagination_class = PaginacionReporte

    def list(self, request, *args, **kwargs):
        # Un parámetro vacío (?desde=) cuenta como no enviado, como en el listado de vuelos.
        filtros = FiltrosReporteSerializer(data={k: v for k, v in request.query_params.items() if v != '' and k != 'page'})
        filtros.is_valid(raise_exception=True)
        f = filtros.validated_data
        clases = (f['clase'],) if 'clase' in f else CLASES

        vuelos = Vuelo.objects.all()
        if 'vuelo' in f:
            try:
                vuelos = vuelos.filter(pk=uuid.UUID(f['vuelo']))
            except ValueError:
                vuelos = vuelos.filter(numero_vuelo__icontains=f['vuelo'].strip())
        if 'desde' in f:
            vuelos = vuelos.filter(fecha_operacion__gte=f['desde'])
        if 'hasta' in f:
            vuelos = vuelos.filter(fecha_operacion__lte=f['hasta'])
        if 'origen' in f:
            vuelos = vuelos.filter(aeropuerto_origen__codigo_iata=f['origen'].upper())
        if 'destino' in f:
            vuelos = vuelos.filter(aeropuerto_destino__codigo_iata=f['destino'].upper())

        self.paginator.totales = totales(vuelos, clases)
        pagina = self.paginate_queryset(con_ocupacion(vuelos).order_by('fecha_operacion', 'hora_partida', 'numero_vuelo'))
        filas = [{'vuelo': VueloSerializer(v).data, **ocupacion_de(v, clases)} for v in pagina]
        return self.get_paginated_response(filas)
