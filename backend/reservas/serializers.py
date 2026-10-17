from rest_framework import serializers

from vuelos.models import Vuelo

from .models import Pasaje, Reserva


class VueloResumenSerializer(serializers.ModelSerializer):
    origen = serializers.CharField(source='aeropuerto_origen.codigo_iata')
    destino = serializers.CharField(source='aeropuerto_destino.codigo_iata')

    class Meta:
        model = Vuelo
        fields = [
            'id',
            'numero_vuelo',
            'origen',
            'destino',
            'fecha_operacion',
            'fecha_llegada',
            'hora_partida',
            'hora_llegada',
        ]


class PasajeSerializer(serializers.ModelSerializer):
    ticket_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Pasaje
        fields = [
            'id',
            'codigo_pasaje',
            'nombre_pasajero',
            'apellido_pasajero',
            'dni_pasajero',
            'clase',
            'asiento',
            'precio',
            'ticket_electronico_url',
            'ticket_pdf_url',
        ]

    def get_ticket_pdf_url(self, obj):
        return f'/api/pasajes/{obj.codigo_pasaje}/pdf/'


class PasajeDetalleSerializer(serializers.ModelSerializer):
    vuelo = VueloResumenSerializer(source='reserva.vuelo', read_only=True)
    ticket_pdf_url = serializers.SerializerMethodField()
    estado_compra = serializers.CharField(source='reserva.estado', read_only=True)
    reserva_id = serializers.UUIDField(source='reserva.id', read_only=True)

    class Meta:
        model = Pasaje
        fields = [
            'id',
            'codigo_pasaje',
            'nombre_pasajero',
            'apellido_pasajero',
            'dni_pasajero',
            'clase',
            'asiento',
            'precio',
            'vuelo',
            'reserva_id',
            'estado_compra',
            'ticket_pdf_url',
        ]

    def get_ticket_pdf_url(self, obj):
        return f'/api/pasajes/{obj.codigo_pasaje}/pdf/'


class PasajeroInputSerializer(serializers.Serializer):
    nombre_pasajero = serializers.CharField(max_length=100, required=False, allow_blank=True)
    apellido_pasajero = serializers.CharField(max_length=100, required=False, allow_blank=True)
    dni_pasajero = serializers.CharField(max_length=30, required=False, allow_blank=True)


class CrearReservaSerializer(serializers.Serializer):
    vuelo_id = serializers.UUIDField()
    clase = serializers.ChoiceField(choices=Pasaje.Clase.choices)
    cantidad_pasajes = serializers.IntegerField(min_value=1, max_value=9)
    pasajeros = serializers.ListField(
        child=PasajeroInputSerializer(),
        required=False,
        allow_empty=True,
    )
    contacto_email = serializers.EmailField(required=False, allow_blank=True)
    contacto_nombre = serializers.CharField(max_length=150, required=False, allow_blank=True)


class ReservaSerializer(serializers.ModelSerializer):
    vuelo = VueloResumenSerializer(read_only=True)
    pasajes = PasajeSerializer(many=True, read_only=True)
    monto = serializers.SerializerMethodField()
    clase = serializers.ReadOnlyField()
    cantidad = serializers.ReadOnlyField()

    class Meta:
        model = Reserva
        fields = [
            'id',
            'vuelo',
            'clase',
            'cantidad',
            'cantidad_pasajes',
            'monto',
            'estado',
            'contacto_email',
            'contacto_nombre',
            'pasajes',
            'creado_en',
        ]

    def get_monto(self, obj):
        return str(obj.monto)
