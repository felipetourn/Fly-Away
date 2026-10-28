from rest_framework import serializers

from vuelos.serializers import FECHA_INVALIDA

from .servicios import CLASES

FALTA_CRITERIO = 'Elegí al menos un criterio: vuelo, fechas, origen o destino.'


class FiltrosReporteSerializer(serializers.Serializer):
    """Parámetros de GET /reportes/ocupacion/ (US13). Hace falta un vuelo, una fecha, el origen o el destino;
    la clase sola no alcanza."""

    vuelo = serializers.CharField(required=False)  # id de la instancia o parte del número
    origen = serializers.CharField(required=False)  # código IATA, como el listado de vuelos
    destino = serializers.CharField(required=False)
    desde = serializers.DateField(required=False, error_messages={'invalid': FECHA_INVALIDA})
    hasta = serializers.DateField(required=False, error_messages={'invalid': FECHA_INVALIDA})
    clase = serializers.ChoiceField(
        choices=CLASES, required=False, error_messages={'invalid_choice': 'La clase debe ser economy o primera.'}
    )

    def validate(self, datos):
        if not ({'vuelo', 'desde', 'hasta', 'origen', 'destino'} & datos.keys()):
            raise serializers.ValidationError(FALTA_CRITERIO)
        if 'desde' in datos and 'hasta' in datos and datos['hasta'] < datos['desde']:
            raise serializers.ValidationError({'hasta': 'La fecha hasta no puede ser anterior a desde.'})
        return datos
