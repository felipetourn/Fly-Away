import re

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
            'estado',
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


# Empieza con letra; después letras, espacios, apóstrofos, guiones o puntos (María José, D'Alessandro-Muñoz).
NOMBRE_VALIDO = re.compile(r"[^\W\d_](?:[^\W\d_]|[ '’.\-])*")
# DNI o pasaporte: 6 a 15 letras o números, sin los separadores con que se suele escribir.
DOCUMENTO_VALIDO = re.compile(r'[A-Z0-9]{6,15}')


def _validar_nombre(valor, campo):
    if not NOMBRE_VALIDO.fullmatch(valor):
        raise serializers.ValidationError(
            f'El {campo} solo puede tener letras, espacios, apóstrofos, guiones y puntos.'
        )
    return valor


class PasajeroInputSerializer(serializers.Serializer):
    nombre_pasajero = serializers.CharField(max_length=100)
    apellido_pasajero = serializers.CharField(max_length=100)
    dni_pasajero = serializers.CharField(max_length=30)

    def validate_nombre_pasajero(self, valor):
        return _validar_nombre(valor, 'nombre')

    def validate_apellido_pasajero(self, valor):
        return _validar_nombre(valor, 'apellido')

    def validate_dni_pasajero(self, valor):
        documento = re.sub(r'[\s.\-]', '', valor).upper()
        if not DOCUMENTO_VALIDO.fullmatch(documento):
            raise serializers.ValidationError('Ingresá un DNI o documento de 6 a 15 letras o números.')
        return documento


class DatosReservaSerializer(serializers.Serializer):
    clase = serializers.ChoiceField(choices=Pasaje.Clase.choices)
    cantidad_pasajes = serializers.IntegerField(min_value=1, max_value=9)
    pasajeros = serializers.ListField(child=PasajeroInputSerializer())
    contacto_email = serializers.EmailField(required=False, allow_blank=True)
    contacto_nombre = serializers.CharField(max_length=150, required=False, allow_blank=True)


class CrearReservaSerializer(DatosReservaSerializer):
    vuelo_id = serializers.UUIDField()


class CrearReservaIdaVueltaSerializer(serializers.Serializer):
    vuelo_ida = serializers.UUIDField()
    vuelo_vuelta = serializers.UUIDField()
    ida = DatosReservaSerializer()
    vuelta = DatosReservaSerializer()

    def validate(self, attrs):
        if attrs['vuelo_ida'] == attrs['vuelo_vuelta']:
            raise serializers.ValidationError('La ida y la vuelta deben ser vuelos distintos.')
        return attrs


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
