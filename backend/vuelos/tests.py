import datetime as dt
import uuid
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from .models import Aeropuerto, Avion, Vuelo

BA = ZoneInfo('America/Argentina/Buenos_Aires')
AHORA = dt.datetime(2026, 10, 20, 12, 0, tzinfo=BA)  # mediodía en Buenos Aires
HOY = AHORA.date()


class Datos(APITestCase):
    """Aeropuertos, un avión y un admin; `timezone.now` fijo en AHORA."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_superuser('admin@mail.com', 'x', nombre='Ada', apellido='Admin')
        aeropuerto = lambda iata, ciudad: Aeropuerto.objects.create(
            codigo_iata=iata, nombre=f'Aeropuerto {iata}', ciudad=ciudad, pais='Argentina'
        )
        cls.bhi = aeropuerto('BHI', 'Bahía Blanca')
        cls.aep = aeropuerto('AEP', 'Buenos Aires')
        cls.eze = aeropuerto('EZE', 'Buenos Aires')
        cls.cor = aeropuerto('COR', 'Córdoba')
        cls.avion = Avion.objects.create(
            matricula='LV-FAA', modelo='Airbus A320', capacidad_economy=150, capacidad_primera=12
        )

    def setUp(self):
        reloj = patch('django.utils.timezone.now', return_value=AHORA)
        reloj.start()
        self.addCleanup(reloj.stop)

    def vuelo(self, numero='FA 1000', origen=None, destino=None, fecha=None, partida='15:00', **cambios):
        sale = dt.time.fromisoformat(partida)
        datos = dict(
            numero_vuelo=numero,
            avion=self.avion,
            aeropuerto_origen=origen or self.bhi,
            aeropuerto_destino=destino or self.aep,
            fecha_operacion=fecha or HOY + dt.timedelta(days=1),
            hora_partida=sale,
            hora_llegada=(dt.datetime.combine(HOY, sale) + dt.timedelta(hours=1)).time(),
            precio_economy=Decimal('100000.00'),
            precio_primera=Decimal('220000.00'),
            asientos_disponibles_economy=30,
            asientos_disponibles_primera=5,
            creado_por=self.admin,
        )
        return Vuelo.objects.create(**{**datos, **cambios})


class ModeloVueloTests(Datos):
    def test_crea_un_vuelo_activo(self):
        v = self.vuelo()
        self.assertEqual(v.estado, Vuelo.Estado.ACTIVO)
        self.assertEqual(Vuelo._meta.db_table, 'vuelos')

    def test_origen_y_destino_distintos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo(destino=self.bhi)

    def test_asientos_no_negativos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo(asientos_disponibles_economy=-1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo(asientos_disponibles_primera=-1)

    def test_numero_unico_por_fecha(self):
        self.vuelo()
        self.vuelo(fecha=HOY + dt.timedelta(days=2))  # mismo número, otro día: vale
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo()


VUELO_CAMPOS = {
    'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'hora_partida', 'hora_llegada',
    'precio_economy', 'precio_primera', 'asientos_disponibles_economy', 'asientos_disponibles_primera', 'estado',
}


class AeropuertosTests(Datos):
    def test_lista_ordenada_por_ciudad(self):
        r = self.client.get('/api/aeropuertos/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a['codigo_iata'] for a in r.json()], ['BHI', 'AEP', 'EZE', 'COR'])
        self.assertEqual(set(r.json()[0]), {'id', 'codigo_iata', 'nombre', 'ciudad', 'pais'})


class DetalleTests(Datos):
    def test_detalle_con_avion_y_forma_de_la_api(self):
        v = self.vuelo()
        r = self.client.get(f'/api/vuelos/{v.id}/')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(set(d), VUELO_CAMPOS | {'avion'})
        self.assertEqual(d['id'], str(v.id))
        self.assertEqual(d['avion'], {'matricula': 'LV-FAA', 'modelo': 'Airbus A320'})
        self.assertEqual(d['origen']['codigo_iata'], 'BHI')
        self.assertEqual(d['destino']['ciudad'], 'Buenos Aires')
        self.assertEqual(d['precio_economy'], '100000.00')
        self.assertEqual(d['hora_partida'], '15:00:00')
        self.assertEqual(d['fecha_operacion'], str(HOY + dt.timedelta(days=1)))

    def test_detalle_de_un_cancelado(self):
        v = self.vuelo(estado=Vuelo.Estado.CANCELADO)
        r = self.client.get(f'/api/vuelos/{v.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['estado'], 'cancelado')

    def test_404_en_json(self):
        for id_ in (uuid.uuid4(), 'no-es-un-uuid'):
            r = self.client.get(f'/api/vuelos/{id_}/')
            self.assertEqual(r.status_code, 404, id_)
            self.assertIn('detail', r.json())
