from rest_framework import serializers

from vuelos.models import Vuelo

from . import reservas_mock
from .models import Pago, ReservaDemo


class VueloResumenSerializer(serializers.ModelSerializer):
    origen = serializers.CharField(source='aeropuerto_origen.codigo_iata')
    destino = serializers.CharField(source='aeropuerto_destino.codigo_iata')

    class Meta:
        model = Vuelo
        fields = ['id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'hora_partida']


class ReservaSerializer(serializers.ModelSerializer):
    vuelo = VueloResumenSerializer()
    monto = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()

    class Meta:
        model = ReservaDemo
        fields = ['id', 'vuelo', 'clase', 'cantidad', 'monto', 'estado']

    def get_monto(self, reserva):
        return str(reservas_mock.monto_de(reserva))

    def get_estado(self, reserva):
        pagada = Pago.objects.filter(reserva_id=reserva.id, estado=Pago.Estado.APROBADO).exists()
        return 'pagada' if pagada else 'pendiente'
