import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ReservaDemo(models.Model):
    """ponytail: reserva temporal hasta la US06; la reemplaza `reservas` del DBML.

    Ver "Contrato entre reservas (US06) y pagos" en docs/arquitectura.md. Se borra con una migración al integrar.
    """

    class Clase(models.TextChoices):
        ECONOMY = 'economy', 'Economy'
        PRIMERA = 'primera', 'Primera'

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PAGADA = 'pagada', 'Pagada'  # compra confirmada (US08)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pasajero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservas_demo')
    vuelo = models.ForeignKey('vuelos.Vuelo', on_delete=models.PROTECT, related_name='reservas_demo')
    clase = models.CharField(max_length=10, choices=Clase.choices)
    cantidad = models.IntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reservas_demo'
        ordering = ['vuelo__fecha_operacion', 'vuelo__hora_partida', 'id']
        constraints = [
            models.CheckConstraint(condition=Q(cantidad__gte=1, cantidad__lte=9), name='reserva_demo_cantidad_1_a_9'),
        ]


class Pago(models.Model):
    """Un intento de pago de una reserva (tabla `pagos` del DBML). Una reserva puede tener varios; aprobado, uno solo."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        APROBADO = 'aprobado', 'Aprobado'
        RECHAZADO = 'rechazado', 'Rechazado'

    class Metodo(models.TextChoices):
        TARJETA = 'tarjeta', 'Tarjeta'
        MERCADOPAGO = 'mercadopago', 'Mercado Pago'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # ponytail: UUID sin FK mientras las reservas sean demo; pasa a ForeignKey a `reservas` con la US06.
    reserva_id = models.UUIDField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo_pago = models.CharField(max_length=20, choices=Metodo.choices)
    ultimos_4 = models.CharField(max_length=4, null=True, blank=True)
    marca = models.CharField(max_length=20, null=True, blank=True)  # visa | mastercard | amex
    cuenta_mp = models.CharField(max_length=254, null=True, blank=True)  # mail del comprador en MP
    numero_factura = models.CharField(max_length=30, unique=True, null=True, blank=True)
    transaccion_externa_id = models.CharField(max_length=100, null=True, blank=True)
    detalle = models.CharField(max_length=200, blank=True, default='')
    procesado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pagos'
        ordering = ['-creado_en', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['reserva_id'], condition=Q(estado='aprobado'), name='pago_un_aprobado_por_reserva'
            ),
        ]

    def __str__(self):
        return f'{self.get_metodo_pago_display()} {self.monto} ({self.estado})'
