import uuid

from django.db import models
from django.db.models import Q


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
    reserva = models.ForeignKey('reservas.Reserva', on_delete=models.PROTECT, related_name='pagos')
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
                fields=['reserva'], condition=Q(estado='aprobado'), name='pago_un_aprobado_por_reserva'
            ),
        ]

    def __str__(self):
        return f'{self.get_metodo_pago_display()} {self.monto} ({self.estado})'
