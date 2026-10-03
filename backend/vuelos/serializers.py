from django.utils import timezone
from rest_framework import serializers

from .models import Aeropuerto, Avion, Vuelo


class AeropuertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aeropuerto
        fields = ['id', 'codigo_iata', 'nombre', 'ciudad', 'pais']


class AvionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avion
        fields = ['matricula', 'modelo']


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
