"""Catálogo (aeropuertos, flota, usuario sistema) y, con --vuelos, vuelos de ejemplo. Idempotente.

El catálogo corre en build.sh porque aeropuertos y aviones no tienen ABM.
Los vuelos los carga el administrador; --vuelos queda para desarrollo local.
Solo crea lo que falta: no pisa correcciones hechas desde el admin.

Cada vuelo de ejemplo trae de 0 a 5 lugares vendidos, y cada uno es una compra confirmada de verdad
(reserva pagada + pasajes + pago aprobado, a nombre del usuario sistema): vendidos + disponibles = capacidad.
Los vuelos de ejemplo se reparten alternando todos los aviones disponibles sin superponer horarios de un mismo avión.
--regenerar borra los vuelos de ejemplo y sus ventas de ejemplo y los vuelve a generar desde hoy en adelante;
los que tienen reservas reales se conservan.
"""
from collections import defaultdict
import datetime as dt
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, Max, Min, Q
from django.utils import timezone

from pagos.factura import generar_numero_factura
from pagos.models import Pago
from reservas.models import Pasaje, Reserva
from vuelos.models import Aeropuerto, Avion, Vuelo

AEROPUERTOS = [
    ('AEP', 'Buenos Aires', 'Aeroparque Jorge Newbery'),
    ('EZE', 'Buenos Aires', 'Aeropuerto Internacional Ministro Pistarini'),
    ('BHI', 'Bahía Blanca', 'Aeropuerto Comandante Espora'),
    ('BRC', 'San Carlos de Bariloche', 'Aeropuerto Teniente Luis Candelaria'),
    ('COR', 'Córdoba', 'Aeropuerto Ingeniero Ambrosio Taravella'),
    ('MDZ', 'Mendoza', 'Aeropuerto El Plumerillo'),
    ('IGR', 'Puerto Iguazú', 'Aeropuerto Cataratas del Iguazú'),
    ('USH', 'Ushuaia', 'Aeropuerto Malvinas Argentinas'),
    ('FTE', 'El Calafate', 'Aeropuerto Comandante Armando Tola'),
    ('SLA', 'Salta', 'Aeropuerto Martín Miguel de Güemes'),
    ('JUJ', 'San Salvador de Jujuy', 'Aeropuerto Horacio Guzmán'),
]

FLOTA = [
    ('LV-FAA', 'Airbus A320', 150, 12),
    ('LV-FAB', 'Boeing 737-800', 162, 12),
    ('LV-FAC', 'Embraer E190', 96, 8),
    ('LV-FAD', 'Airbus A330-200', 250, 24),
    ('LV-FAE', 'Airbus A320', 150, 12),
    ('LV-FAF', 'Boeing 737-800', 162, 12),
    ('LV-FAG', 'Embraer E190', 96, 8),
    ('LV-FAH', 'Airbus A321', 190, 16),
    ('LV-FAI', 'Boeing 737 MAX 8', 170, 12),
    ('LV-FAJ', 'Embraer E195-E2', 120, 12),
]
MARGEN_ENTRE_VUELOS = 30  # minutos libres entre vuelos del mismo avión para permitir ediciones de horario
MAX_VENDIDOS = 5  # por vuelo de ejemplo: pocos pasajes en la base
CLASES = ('economy', 'primera')
NOMBRES = ['Ana', 'Bruno', 'Carla', 'Diego', 'Elena', 'Facundo', 'Gabriela', 'Hernán', 'Inés', 'Julián', 'Lucía', 'Martín']
APELLIDOS = ['Pérez', 'Gómez', 'Fernández', 'López', 'Díaz', 'Martínez', 'Romero', 'Sosa', 'Álvarez', 'Torres']


class Command(BaseCommand):
    help = 'Carga aeropuertos y flota; con --vuelos, también vuelos de ejemplo (no pisa lo que ya existe).'

    def add_arguments(self, parser):
        parser.add_argument('--vuelos', action='store_true', help='Agrega vuelos de ejemplo (desarrollo local).')
        parser.add_argument('--dias', type=int, default=60, help='Días hacia adelante con vuelos (default 60).')
        parser.add_argument(
            '--regenerar', action='store_true',
            help='Borra los vuelos de ejemplo (y sus ventas de ejemplo) y los vuelve a generar desde hoy en adelante.',
        )

    def handle(self, *args, dias, vuelos, regenerar=False, **opciones):
        sistema, creado = get_user_model().objects.get_or_create(
            email='sistema@flyaway.local',
            defaults={'nombre': 'Sistema', 'apellido': 'Fly Away', 'rol': 'administrador'},
        )
        if creado:
            sistema.set_unusable_password()
            sistema.save()

        aeropuertos = [
            Aeropuerto.objects.get_or_create(
                codigo_iata=iata, defaults={'ciudad': ciudad, 'nombre': nombre, 'pais': 'Argentina'}
            )[0]
            for iata, ciudad, nombre in AEROPUERTOS
        ]
        for matricula, modelo, economy, primera in FLOTA:
            Avion.objects.get_or_create(
                matricula=matricula,
                defaults={'modelo': modelo, 'capacidad_economy': economy, 'capacidad_primera': primera},
            )
        aviones = list(Avion.objects.order_by('matricula'))

        hoy = timezone.localdate()
        if regenerar:
            self.regenerar(sistema, aeropuertos, aviones, hoy, dias)
        elif vuelos:
            self.cargar_vuelos(sistema, aeropuertos, aviones, hoy, dias)
        self.stdout.write(self.style.SUCCESS(
            f'Seed listo: {len(aeropuertos)} aeropuertos, {len(aviones)} aviones, {Vuelo.objects.count()} vuelos.'
        ))

    @transaction.atomic
    def regenerar(self, sistema, aeropuertos, aviones, hoy, dias):
        """Los vuelos de ejemplo se borran y se generan de nuevo desde hoy en adelante, sin superponer aviones.

        Las ventas de ejemplo (reservas de `sistema`) se borran con ellos. Los vuelos con reservas reales se
        conservan y sus disponibles pasan a capacidad − vendidos reales. Los del administrador no se tocan.
        """
        de_ejemplo = Vuelo.objects.filter(creado_por=sistema)
        rango = de_ejemplo.aggregate(desde=Min('fecha_operacion'), hasta=Max('fecha_operacion'))
        if not rango['desde']:
            return
        ventas_de_ejemplo = Reserva.objects.filter(pasajero=sistema, vuelo__in=de_ejemplo)
        Pago.objects.filter(reserva__in=ventas_de_ejemplo).delete()  # PROTECT: antes que las reservas
        ventas_de_ejemplo.delete()  # y sus pasajes, en cascada
        borrados, _ = de_ejemplo.filter(reservas__isnull=True).delete()
        conservados = list(de_ejemplo.select_related('avion').annotate(**{
            f'vendidos_{clase}': Count(
                'reservas__pasajes', filter=Q(reservas__estado=Reserva.Estado.PAGADA, reservas__pasajes__clase=clase)
            )
            for clase in CLASES
        }))
        for vuelo in conservados:
            for clase in CLASES:
                capacidad = getattr(vuelo.avion, f'capacidad_{clase}')
                setattr(vuelo, f'asientos_disponibles_{clase}', capacidad - getattr(vuelo, f'vendidos_{clase}'))
            vuelo.save(update_fields=['asientos_disponibles_economy', 'asientos_disponibles_primera', 'actualizado_en'])
        desde = max(rango['desde'], hoy)
        hasta = rango['hasta'] if rango['hasta'] >= desde else desde + dt.timedelta(days=dias - 1)
        cantidad_dias = (hasta - desde).days + 1
        creados = self.cargar_vuelos(sistema, aeropuertos, aviones, desde, cantidad_dias)
        self.stdout.write(
            f'Regenerados del {desde} al {hasta}: {borrados} filas borradas, '
            f'{len(conservados)} vuelos con reservas conservados, {creados} vuelos nuevos.'
        )

    def cargar_vuelos(self, sistema, aeropuertos, aviones, desde, dias):
        """Crea vuelos de ejemplo entre `desde` y `desde + dias` alternando aviones sin superponerse."""
        if not aviones or dias <= 0:
            return 0
        hasta = desde + dt.timedelta(days=dias - 1)
        existentes = set(
            Vuelo.objects.filter(fecha_operacion__range=(desde, hasta))
            .values_list('numero_vuelo', 'fecha_operacion')
        )
        # Intervalos ya ocupados en la base por vuelos ajenos al seed o vuelos de ejemplo conservados con compras reales.
        ocupados_base = defaultdict(list)
        vuelos_fijos = (
            Vuelo.objects.filter(
                estado=Vuelo.Estado.ACTIVO,
                fecha_operacion__range=(desde - dt.timedelta(days=1), hasta + dt.timedelta(days=1)),
            )
            .exclude(creado_por=sistema, reservas__isnull=True)
            .exclude(creado_por=sistema, reservas__pasajero=sistema)
        )
        for fijo in vuelos_fijos:
            ocupados_base[(fijo.avion_id, fijo.fecha_operacion)].append(
                (fijo.hora_partida.hour * 60 + fijo.hora_partida.minute, fijo.hora_llegada.hour * 60 + fijo.hora_llegada.minute)
            )

        rutas = []
        for i, origen in enumerate(aeropuertos):
            for j, destino in enumerate(aeropuertos):
                if origen.ciudad == destino.ciudad:
                    continue
                ruta_rng = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}')
                duracion = 60 + ruta_rng.randrange(30) * 5  # 1 h a 3 h 25 m, fija por ruta
                primer_numero = 1000 + (i * len(aeropuertos) + j) * 10  # bloque de números por ruta
                rutas.append((origen, destino, duracion, primer_numero))

        nuevos = []
        ventas = []  # (vuelo, vendidos)
        for n in range(dias):
            fecha = desde + dt.timedelta(days=n)
            candidatos = []
            for origen, destino, duracion, primer_numero in rutas:
                r = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}-{fecha}')
                for k in range(r.randrange(5)):  # 0 a 4 candidatos por ruta ese día
                    partida = (6 + k * 4) * 60 + r.randrange(8) * 15  # 06:00 a 19:45: llega antes de medianoche
                    llegada = partida + duracion
                    economy = round((40000 + duracion * 900 + r.random() * 40000) / 10) * 10
                    numero = f'FA {primer_numero + k}'
                    cancelado = r.random() < 0.1
                    candidatos.append((numero, origen, destino, partida, llegada, economy, cancelado))

            # Mezclar candidatos del día de forma determinística para repartir aviones entre todas las rutas.
            random.Random(f'orden-{fecha}').shuffle(candidatos)
            ocupados_dia = defaultdict(list, {
                avion.id: list(ocupados_base.get((avion.id, fecha), [])) for avion in aviones
            })
            turno = n % len(aviones)

            for numero, origen, destino, partida, llegada, economy, cancelado in candidatos:
                avion_elegido = None
                for paso in range(len(aviones)):
                    indice = (turno + paso) % len(aviones)
                    candidato_avion = aviones[indice]
                    if self._avion_libre(ocupados_dia[candidato_avion.id], partida, llegada):
                        avion_elegido = candidato_avion
                        turno = (indice + 1) % len(aviones)
                        break
                if avion_elegido is None:
                    continue

                ocupados_dia[avion_elegido.id].append((partida, llegada))
                if (numero, fecha) in existentes:
                    continue  # no pisa lo que ya existe

                vendidos = self.vendidos_de_ejemplo(random.Random(f'{numero}-{fecha}-ventas'))
                vuelo = Vuelo(
                    numero_vuelo=numero,
                    avion=avion_elegido,
                    aeropuerto_origen=origen,
                    aeropuerto_destino=destino,
                    fecha_operacion=fecha,
                    fecha_llegada=fecha,
                    hora_partida=dt.time(partida // 60, partida % 60),
                    hora_llegada=dt.time(llegada // 60, llegada % 60),
                    precio_economy=economy,
                    precio_primera=round(economy * 2.2 / 10) * 10,
                    asientos_disponibles_economy=avion_elegido.capacidad_economy - vendidos['economy'],
                    asientos_disponibles_primera=avion_elegido.capacidad_primera - vendidos['primera'],
                    estado=Vuelo.Estado.CANCELADO if cancelado else Vuelo.Estado.ACTIVO,
                    creado_por=sistema,
                )
                nuevos.append(vuelo)
                ventas.append((vuelo, vendidos))

        with transaction.atomic():
            Vuelo.objects.bulk_create(nuevos, batch_size=1000)
            self.crear_ventas(sistema, ventas)
        return len(nuevos)

    @staticmethod
    def _avion_libre(intervalos, partida, llegada):
        """True si `[partida, llegada]` no se superpone (con margen) con ningún intervalo ya asignado al avión."""
        for otro_sale, otro_llega in intervalos:
            if partida - MARGEN_ENTRE_VUELOS < otro_llega and otro_sale < llegada + MARGEN_ENTRE_VUELOS:
                return False
        return True

    @staticmethod
    def vendidos_de_ejemplo(r):
        """De 0 a MAX_VENDIDOS pasajes; uno de cada cinco, en primera."""
        clases = [('primera' if r.random() < 0.2 else 'economy') for _ in range(r.randrange(MAX_VENDIDOS + 1))]
        return {clase: clases.count(clase) for clase in CLASES}

    @staticmethod
    def crear_ventas(sistema, ventas):
        """Una compra confirmada por clase vendida: reserva pagada, sus pasajes y un pago aprobado."""
        reservas, pasajes, pagos = [], [], []
        ahora = timezone.now()
        for vuelo, vendidos in ventas:
            r = random.Random(f'{vuelo.numero_vuelo}-{vuelo.fecha_operacion}-pasajeros')
            n = 0
            for clase, cantidad in vendidos.items():
                if not cantidad:
                    continue
                reserva = Reserva(
                    pasajero=sistema, contacto_email=sistema.email, contacto_nombre='Venta de ejemplo', vuelo=vuelo,
                    cantidad_pasajes=cantidad, estado=Reserva.Estado.PAGADA,
                )
                precio = getattr(vuelo, f'precio_{clase}')
                for _ in range(cantidad):
                    n += 1
                    pasajes.append(Pasaje(
                        reserva=reserva,
                        # Único por vuelo (número + fecha) y termina en el número de pasajero, como los reales.
                        codigo_pasaje=f'{vuelo.numero_vuelo.replace(" ", "")}-{vuelo.fecha_operacion:%y%m%d}-{n:02d}',
                        nombre_pasajero=r.choice(NOMBRES), apellido_pasajero=r.choice(APELLIDOS),
                        dni_pasajero=str(r.randrange(20_000_000, 45_000_000)), clase=clase, precio=precio,
                    ))
                pago = Pago(
                    reserva=reserva, monto=precio * cantidad, estado=Pago.Estado.APROBADO,
                    metodo_pago=Pago.Metodo.TARJETA, ultimos_4='4242', marca='visa',
                    detalle='Venta de ejemplo (seed).', procesado_en=ahora,
                )
                pago.numero_factura = generar_numero_factura(pago)
                reservas.append(reserva)
                pagos.append(pago)
        Reserva.objects.bulk_create(reservas, batch_size=1000)
        Pasaje.objects.bulk_create(pasajes, batch_size=1000)
        Pago.objects.bulk_create(pagos, batch_size=1000)
