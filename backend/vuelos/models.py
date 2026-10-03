import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Aeropuerto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_iata = models.CharField(max_length=3, unique=True)
    nombre = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)

    class Meta:
        db_table = 'aeropuertos'
        ordering = ['ciudad', 'codigo_iata']

    def __str__(self):
        return f'{self.ciudad} ({self.codigo_iata})'


class Avion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matricula = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=100)
    capacidad_economy = models.IntegerField()
    capacidad_primera = models.IntegerField()

    class Meta:
        db_table = 'aviones'
        verbose_name_plural = 'aviones'

    def __str__(self):
        return f'{self.matricula} ({self.modelo})'


class Vuelo(models.Model):
    """Una fila por vuelo real en una fecha; independiente de las demás (ver modelo.dbml)."""

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        CANCELADO = 'cancelado', 'Cancelado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_vuelo = models.CharField(max_length=10)
    avion = models.ForeignKey(Avion, on_delete=models.PROTECT, related_name='vuelos')
    aeropuerto_origen = models.ForeignKey(Aeropuerto, on_delete=models.PROTECT, related_name='vuelos_salida')
    aeropuerto_destino = models.ForeignKey(Aeropuerto, on_delete=models.PROTECT, related_name='vuelos_llegada')
    fecha_operacion = models.DateField()
    fecha_llegada = models.DateField()
    hora_partida = models.TimeField()
    hora_llegada = models.TimeField()
    precio_economy = models.DecimalField(max_digits=10, decimal_places=2)
    precio_primera = models.DecimalField(max_digits=10, decimal_places=2)
    asientos_disponibles_economy = models.IntegerField()
    asientos_disponibles_primera = models.IntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vuelos_creados')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vuelos'
        ordering = ['fecha_operacion', 'hora_partida']
        constraints = [
            models.UniqueConstraint(fields=['numero_vuelo', 'fecha_operacion'], name='vuelo_numero_fecha_unico'),
            models.CheckConstraint(
                condition=~Q(aeropuerto_origen=F('aeropuerto_destino')), name='vuelo_origen_distinto_destino'
            ),
            models.CheckConstraint(condition=Q(asientos_disponibles_economy__gte=0), name='vuelo_asientos_economy_no_negativos'),
            models.CheckConstraint(condition=Q(asientos_disponibles_primera__gte=0), name='vuelo_asientos_primera_no_negativos'),
            models.CheckConstraint(
                condition=Q(fecha_llegada__gt=F('fecha_operacion'))
                | Q(fecha_llegada=F('fecha_operacion'), hora_llegada__gt=F('hora_partida')),
                name='vuelo_llegada_posterior_a_partida',
            ),
        ]

    def __str__(self):
        return f'{self.numero_vuelo} {self.fecha_operacion}'
