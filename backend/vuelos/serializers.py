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
            'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'hora_partida', 'hora_llegada',
            'precio_economy', 'precio_primera', 'asientos_disponibles_economy', 'asientos_disponibles_primera',
            'estado',
        ]


class VueloDetalleSerializer(VueloSerializer):
    avion = AvionSerializer()

    class Meta(VueloSerializer.Meta):
        fields = VueloSerializer.Meta.fields + ['avion']
