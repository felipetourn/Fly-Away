from django.utils import timezone
from rest_framework import serializers

from vuelos.models import Vuelo

from . import reservas_mock, tarjeta
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

    class Meta:
        model = ReservaDemo
        fields = ['id', 'vuelo', 'clase', 'cantidad', 'monto', 'estado']

    def get_monto(self, reserva):
        return str(reservas_mock.monto_de(reserva))


class ReservaIdSerializer(serializers.Serializer):
    reserva_id = serializers.UUIDField()


class TarjetaSerializer(ReservaIdSerializer):
    # allow_blank: los vacíos los valida `tarjeta`, así todos los errores salen juntos y con los mismos mensajes del front.
    numero = serializers.CharField(allow_blank=True)
    titular = serializers.CharField(max_length=100, allow_blank=True)
    vencimiento = serializers.CharField(allow_blank=True)
    cvv = serializers.CharField(allow_blank=True)

    def validate(self, datos):
        datos['numero'] = tarjeta.limpiar_numero(datos['numero'])
        errores = tarjeta.errores_de_tarjeta(
            datos['numero'], datos['titular'], datos['vencimiento'], datos['cvv'], timezone.localdate()
        )
        if errores:
            raise serializers.ValidationError({campo: [mensaje] for campo, mensaje in errores.items()})
        return datos


class PagoSerializer(serializers.ModelSerializer):
    """`context['reservas']`: {reserva_id: ReservaDemo} del usuario, para el resumen del vuelo."""

    vuelo = serializers.SerializerMethodField()
    cantidad_pasajes = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            'id', 'reserva_id', 'vuelo', 'cantidad_pasajes', 'metodo_pago', 'ultimos_4', 'marca', 'cuenta_mp',
            'monto', 'estado', 'detalle', 'transaccion_externa_id', 'creado_en', 'procesado_en',
        ]

    def get_vuelo(self, pago):
        reserva = self.context['reservas'].get(pago.reserva_id)
        return VueloResumenSerializer(reserva.vuelo).data if reserva else None

    def get_cantidad_pasajes(self, pago):
        reserva = self.context['reservas'].get(pago.reserva_id)
        return len(reservas_mock.pasajes_de(reserva)) if reserva else None
