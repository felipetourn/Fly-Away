import datetime as dt
from collections import Counter
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import Aeropuerto, Avion, Vuelo
from .servicios import errores_de_ruta_y_horas, fechas_de_periodo


class AeropuertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aeropuerto
        fields = ['id', 'codigo_iata', 'nombre', 'ciudad', 'pais']


class AvionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avion
        fields = ['id', 'matricula', 'modelo', 'capacidad_economy', 'capacidad_primera']


class VueloSerializer(serializers.ModelSerializer):
    """Forma de `Vuelo` en frontend/src/lib/vuelos.ts: origen y destino anidados."""

    origen = AeropuertoSerializer(source='aeropuerto_origen')
    destino = AeropuertoSerializer(source='aeropuerto_destino')

    class Meta:
        model = Vuelo
        fields = [
            'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'fecha_llegada', 'hora_partida',
            'hora_llegada', 'precio_economy', 'precio_primera', 'asientos_disponibles_economy', 'asientos_disponibles_primera',
            'estado',
        ]


class VueloDetalleSerializer(VueloSerializer):
    avion = AvionSerializer()

    class Meta(VueloSerializer.Meta):
        fields = VueloSerializer.Meta.fields + ['avion']


FECHA_INVALIDA = 'Indicá una fecha válida (AAAA-MM-DD).'
MONTO_INVALIDO = 'Ingresá un monto válido.'
PASAJEROS_INVALIDO = 'Tienen que ser entre 1 y 9 pasajeros.'
MAX_PASAJEROS = 9


def _errores(mensaje, *claves):
    return {clave: mensaje for clave in claves}


class BusquedaSerializer(serializers.Serializer):
    """Parámetros de GET /vuelos/buscar/. Los mensajes son los mismos que muestra el front."""

    origen = serializers.CharField(required=False)
    destino = serializers.CharField(required=False)
    desde = serializers.DateField(error_messages=_errores(FECHA_INVALIDA, 'required', 'invalid', 'null'))
    hasta = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid', 'null'))
    pasajeros = serializers.IntegerField(
        default=1,
        min_value=1,
        max_value=MAX_PASAJEROS,
        error_messages=_errores(PASAJEROS_INVALIDO, 'invalid', 'min_value', 'max_value', 'max_string_length'),
    )
    clase = serializers.ChoiceField(
        choices=['economy', 'primera'],
        default='economy',
        error_messages={'invalid_choice': 'La clase tiene que ser economy o primera.'},
    )
    precio_min = serializers.DecimalField(
        max_digits=None, decimal_places=None, min_value=0, required=False,
        error_messages=_errores(MONTO_INVALIDO, 'invalid', 'min_value', 'max_string_length'),
    )
    precio_max = serializers.DecimalField(
        max_digits=None, decimal_places=None, min_value=0, required=False,
        error_messages=_errores(MONTO_INVALIDO, 'invalid', 'min_value', 'max_string_length'),
    )

    def _aeropuerto(self, codigo):
        codigo = codigo.upper()
        try:
            return Aeropuerto.objects.get(codigo_iata=codigo)
        except Aeropuerto.DoesNotExist:
            raise serializers.ValidationError(f'No conocemos el aeropuerto "{codigo}".')

    def validate_origen(self, valor):
        return self._aeropuerto(valor)

    def validate_destino(self, valor):
        return self._aeropuerto(valor)

    def validate_desde(self, valor):
        if valor < timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser en el pasado.')
        return valor

    def validate(self, datos):
        origen, destino = datos.get('origen'), datos.get('destino')
        errores = {}
        if not origen and not destino:
            errores['origen'] = 'Indicá un origen, un destino o ambos.'
        elif origen and destino and origen == destino:
            errores['destino'] = 'El destino tiene que ser distinto del origen.'
        elif origen and destino and origen.ciudad == destino.ciudad:
            errores['destino'] = 'Origen y destino están en la misma ciudad.'
        if 'hasta' in datos and datos['hasta'] < datos['desde']:
            errores['hasta'] = '"Hasta" no puede ser antes de "Desde".'
        if 'precio_min' in datos and 'precio_max' in datos and datos['precio_min'] > datos['precio_max']:
            errores['precio_min'] = 'El mínimo no puede ser mayor que el máximo.'
        if errores:
            raise serializers.ValidationError(errores)
        return datos


class FiltrosListadoSerializer(serializers.Serializer):
    """Parámetros de GET /vuelos/ (listado del administrador). Todos opcionales."""

    q = serializers.CharField(required=False)
    origen = serializers.CharField(required=False)
    destino = serializers.CharField(required=False)
    desde = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid'))
    hasta = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid'))
    estado = serializers.ChoiceField(choices=Vuelo.Estado.choices, required=False)


def _aeropuerto():
    return serializers.SlugRelatedField(
        slug_field='codigo_iata',
        queryset=Aeropuerto.objects.all(),
        error_messages={'does_not_exist': 'No conocemos el aeropuerto "{value}".'},
    )


def _precio():
    return serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
        error_messages={'min_value': 'El precio tiene que ser mayor a cero.'},
    )


MAX_DIAS_ADELANTE = 365


class PeriodoSerializer(serializers.Serializer):
    desde = serializers.DateField()
    hasta = serializers.DateField()
    dias = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), allow_empty=False)
    avion = serializers.PrimaryKeyRelatedField(queryset=Avion.objects.all())
    precio_economy = _precio()
    precio_primera = _precio()

    def validate(self, periodo):
        hoy = timezone.localdate()
        errores = {}
        if periodo['desde'] < hoy:
            errores['desde'] = 'La fecha no puede ser en el pasado.'
        if periodo['hasta'] < periodo['desde']:
            errores['hasta'] = '"Hasta" no puede ser antes de "Desde".'
        elif periodo['hasta'] > hoy + dt.timedelta(days=MAX_DIAS_ADELANTE):
            errores['hasta'] = 'El período no puede pasar de un año desde hoy.'
        else:
            periodo['fechas'] = fechas_de_periodo(periodo['desde'], periodo['hasta'], periodo['dias'])
            if not periodo['fechas']:
                errores['dias'] = 'Ningún día del rango cae en los días elegidos.'
        if errores:
            raise serializers.ValidationError(errores)
        return periodo


class AltaVueloSerializer(serializers.Serializer):
    """Cuerpo de POST /vuelos/. Lo común al alta y sus períodos; cada período sale con sus `fechas`."""

    origen = _aeropuerto()
    destino = _aeropuerto()
    hora_partida = serializers.TimeField()
    hora_llegada = serializers.TimeField()
    periodos = PeriodoSerializer(many=True, allow_empty=False)

    def validate(self, datos):
        errores = errores_de_ruta_y_horas(
            datos['origen'], datos['destino'], datos['hora_partida'], datos['hora_llegada']
        )
        veces = Counter(fecha for periodo in datos['periodos'] for fecha in periodo['fechas'])
        ahora = timezone.localtime()
        if ahora.date() in veces and datos['hora_partida'] <= ahora.time():
            errores['hora_partida'] = 'Ese horario ya pasó para hoy.'
        if errores:
            raise serializers.ValidationError(errores)
        repetidas = sorted(fecha for fecha, n in veces.items() if n > 1)
        if repetidas:
            raise serializers.ValidationError(
                f'Hay fechas repetidas entre períodos: {", ".join(map(str, repetidas))}.'
            )
        return datos
