"""Datos de ejemplo: aeropuertos, flota y vuelos de los próximos días. Idempotente.

Existe porque todavía no hay ABM de vuelos. Sacarlo de build.sh cuando exista.
Solo crea lo que falta: no pisa correcciones hechas desde el admin.
"""
import datetime as dt
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

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
]


class Command(BaseCommand):
    help = 'Carga aeropuertos, flota y vuelos de ejemplo (no pisa lo que ya existe).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=60, help='Días hacia adelante con vuelos (default 60).')

    def handle(self, *args, dias, **opciones):
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
        aviones = [
            Avion.objects.get_or_create(
                matricula=matricula,
                defaults={'modelo': modelo, 'capacidad_economy': economy, 'capacidad_primera': primera},
            )[0]
            for matricula, modelo, economy, primera in FLOTA
        ]

        hoy = timezone.localdate()
        vuelos = []
        for i, origen in enumerate(aeropuertos):
            for j, destino in enumerate(aeropuertos):
                if origen.ciudad == destino.ciudad:
                    continue
                # Semillas por texto: mismo resultado en cada corrida.
                ruta = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}')
                duracion = 60 + ruta.randrange(30) * 5  # 1 h a 3 h 25 m, fija por ruta
                avion = aviones[ruta.randrange(len(aviones))]
                primer_numero = 1000 + (i * len(aeropuertos) + j) * 10  # bloque de números por ruta
                for n in range(dias):
                    fecha = hoy + dt.timedelta(days=n)
                    r = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}-{fecha}')
                    for k in range(r.randrange(5)):  # 0 a 4 vuelos ese día
                        partida = (6 + k * 4) * 60 + r.randrange(8) * 15  # 06:00 a 19:45: llega antes de medianoche
                        llegada = partida + duracion
                        economy = round((40000 + duracion * 900 + r.random() * 40000) / 10) * 10
                        vuelos.append(Vuelo(
                            numero_vuelo=f'FA {primer_numero + k}',
                            avion=avion,
                            aeropuerto_origen=origen,
                            aeropuerto_destino=destino,
                            fecha_operacion=fecha,
                            fecha_llegada=fecha,
                            hora_partida=dt.time(partida // 60, partida % 60),
                            hora_llegada=dt.time(llegada // 60, llegada % 60),
                            precio_economy=economy,
                            precio_primera=round(economy * 2.2 / 10) * 10,
                            asientos_disponibles_economy=r.randrange(40),
                            asientos_disponibles_primera=r.randrange(10),
                            estado=Vuelo.Estado.CANCELADO if r.random() < 0.1 else Vuelo.Estado.ACTIVO,
                            creado_por=sistema,
                        ))
        # El índice único (numero_vuelo, fecha_operacion) descarta los que ya existen sin pisarlos.
        Vuelo.objects.bulk_create(vuelos, batch_size=1000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f'Seed listo: {len(aeropuertos)} aeropuertos, {len(aviones)} aviones, {Vuelo.objects.count()} vuelos.'
        ))
