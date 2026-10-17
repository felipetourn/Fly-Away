import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class Reserva(models.Model):
    """Reserva de pasajes (tabla `reservas` del DBML).

    Representa la reserva inicial realizada por un pasajero (o venta en mostrador).
    Permanece en estado 'pendiente' hasta que el pago se aprueba y confirma (US08).
    """

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PAGADA = 'pagada', 'Pagada'
        CANCELADA = 'cancelada', 'Cancelada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pasajero = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas',
    )
    vendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ventas_mostrador',
    )
    contacto_email = models.CharField(max_length=254)
    contacto_nombre = models.CharField(max_length=150, blank=True, default='')
    vuelo = models.ForeignKey('vuelos.Vuelo', on_delete=models.PROTECT, related_name='reservas')
    cantidad_pasajes = models.IntegerField()
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reservas'
        ordering = ['-creado_en', 'id']
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad_pasajes__gte=1, cantidad_pasajes__lte=9),
                name='reserva_cantidad_pasajes_1_a_9',
            ),
        ]

    def __str__(self):
        return f'Reserva {self.id} ({self.estado})'

    @property
    def monto(self):
        """Monto total a pagar: suma del precio de cada pasaje asociado."""
        return sum((p.precio for p in self.pasajes.all()), Decimal('0.00'))

    @property
    def clase(self):
        """Clase principal de la reserva (tomada del primer pasaje o fallback)."""
        primer_pasaje = self.pasajes.first()
        return primer_pasaje.clase if primer_pasaje else 'economy'

    @property
    def cantidad(self):
        """Alias para compatibilidad con la interfaz de reservas."""
        return self.cantidad_pasajes


class Pasaje(models.Model):
    """Un registro por asiento comprado (tabla `pasajes` del DBML)."""

    class Clase(models.TextChoices):
        ECONOMY = 'economy', 'Economy'
        PRIMERA = 'primera', 'Primera'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reserva = models.ForeignKey(Reserva, on_delete=models.CASCADE, related_name='pasajes')
    codigo_pasaje = models.CharField(max_length=30, unique=True)
    nombre_pasajero = models.CharField(max_length=100)
    apellido_pasajero = models.CharField(max_length=100)
    dni_pasajero = models.CharField(max_length=30)
    clase = models.CharField(max_length=10, choices=Clase.choices)
    asiento = models.CharField(max_length=10, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    ticket_electronico_url = models.CharField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = 'pasajes'
        ordering = ['id']

    def __str__(self):
        return f'{self.codigo_pasaje} - {self.nombre_pasajero} {self.apellido_pasajero}'

