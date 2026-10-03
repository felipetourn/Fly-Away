import uuid

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Aeropuerto, Avion, Vuelo
from .permissions import EsAdministrador
from .serializers import (
    AeropuertoSerializer,
    AltaVueloSerializer,
    AvionSerializer,
    BusquedaSerializer,
    FiltrosListadoSerializer,
    VueloDetalleSerializer,
    VueloSerializer,
)
from .servicios import crear_vuelos, error_general


class AeropuertosView(generics.ListAPIView):
    queryset = Aeropuerto.objects.all()
    serializer_class = AeropuertoSerializer


class BuscarVuelosView(APIView):
    """Vuelos activos, con lugar para todos, en el rango de precio y que todavía no salieron."""

    def get(self, request):
        # Un parámetro vacío (?hasta=) cuenta como no enviado.
        busqueda = BusquedaSerializer(data={k: v for k, v in request.query_params.items() if v != ''})
        busqueda.is_valid(raise_exception=True)
        d = busqueda.validated_data
        clase = d['clase']
        ahora = timezone.localtime()  # hora de Buenos Aires (TIME_ZONE)

        vuelos = (
            Vuelo.objects.select_related('aeropuerto_origen', 'aeropuerto_destino')
            .filter(
                estado=Vuelo.Estado.ACTIVO,
                fecha_operacion__range=(d['desde'], d.get('hasta', d['desde'])),
                **{f'asientos_disponibles_{clase}__gte': d['pasajeros']},
            )
            .exclude(fecha_operacion=ahora.date(), hora_partida__lte=ahora.time())
            .order_by('fecha_operacion', 'hora_partida', 'numero_vuelo')  # numero_vuelo: desempate estable
        )
        if d.get('origen'):
            vuelos = vuelos.filter(aeropuerto_origen=d['origen'])
        if d.get('destino'):
            vuelos = vuelos.filter(aeropuerto_destino=d['destino'])
        if 'precio_min' in d:
            vuelos = vuelos.filter(**{f'precio_{clase}__gte': d['precio_min']})
        if 'precio_max' in d:
            vuelos = vuelos.filter(**{f'precio_{clase}__lte': d['precio_max']})
        # ponytail: sin paginación; sumar PageNumberPagination si un rango largo devuelve demasiados vuelos.
        return Response(VueloSerializer(vuelos, many=True).data)


class VueloDetalleView(generics.RetrieveAPIView):
    """Incluye cancelados: el detalle informa la cancelación. Un id que no es UUID da 404 (no 500)."""

    queryset = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino')
    serializer_class = VueloDetalleSerializer


class Paginacion(PageNumberPagination):
    page_size = 50


class AvionesView(generics.ListAPIView):
    permission_classes = [EsAdministrador]
    queryset = Avion.objects.order_by('matricula')
    serializer_class = AvionSerializer


class VuelosView(generics.ListAPIView):
    """ABM de vuelos del administrador: listado paginado con filtros y alta con recurrencia."""

    permission_classes = [EsAdministrador]
    serializer_class = VueloDetalleSerializer
    pagination_class = Paginacion

    def get_queryset(self):
        filtros = FiltrosListadoSerializer(data={k: v for k, v in self.request.query_params.items() if v != ''})
        filtros.is_valid(raise_exception=True)
        f = filtros.validated_data
        vuelos = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino').order_by(
            'fecha_operacion', 'hora_partida', 'numero_vuelo'
        )
        q = f.get('q')
        if q:
            try:
                vuelos = vuelos.filter(pk=uuid.UUID(q))
            except ValueError:
                vuelos = vuelos.filter(numero_vuelo__icontains=q)
        # Sin `desde` ni `q`, desde hoy; con `q` se busca en todas las fechas (un id puede ser de un vuelo pasado).
        desde = f.get('desde') or (None if q else timezone.localdate())
        if desde:
            vuelos = vuelos.filter(fecha_operacion__gte=desde)
        if 'hasta' in f:
            vuelos = vuelos.filter(fecha_operacion__lte=f['hasta'])
        if 'estado' in f:
            vuelos = vuelos.filter(estado=f['estado'])
        if 'origen' in f:
            vuelos = vuelos.filter(aeropuerto_origen__codigo_iata=f['origen'].upper())
        if 'destino' in f:
            vuelos = vuelos.filter(aeropuerto_destino__codigo_iata=f['destino'].upper())
        return vuelos

    def post(self, request):
        alta = AltaVueloSerializer(data=request.data)
        alta.is_valid(raise_exception=True)
        try:
            numero, cantidad = crear_vuelos(alta.validated_data, request.user)
        except IntegrityError:
            # Dos altas a la vez tomaron el mismo número: el índice único frena a la segunda.
            raise error_general('No se pudo asignar el número de vuelo. Probá de nuevo.')
        return Response({'numero_vuelo': numero, 'cantidad': cantidad}, status=201)
