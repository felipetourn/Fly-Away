import datetime as dt
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from vuelos.models import Aeropuerto, Avion, Vuelo

from . import reservas_mock
from .models import Pago, ReservaDemo

BA = ZoneInfo('America/Argentina/Buenos_Aires')
AHORA = dt.datetime(2026, 10, 20, 12, 0, tzinfo=BA)  # mediodía en Buenos Aires
HOY = AHORA.date()
Usuario = get_user_model()


class Datos(APITestCase):
    """Dos pasajeros, un admin y cuatro vuelos AEP → COR en los próximos días; `timezone.now` fijo en AHORA."""

    @classmethod
    def setUpTestData(cls):
        cls.pasajero = Usuario.objects.create_user('ana@mail.com', 'x', nombre='Ana', apellido='Pérez')
        cls.otro = Usuario.objects.create_user('beto@mail.com', 'x', nombre='Beto', apellido='Gómez')
        cls.admin = Usuario.objects.create_superuser('admin@mail.com', 'x', nombre='Ada', apellido='Admin')
        cls.aep = Aeropuerto.objects.create(codigo_iata='AEP', nombre='Aeroparque', ciudad='Buenos Aires', pais='Argentina')
        cls.cor = Aeropuerto.objects.create(codigo_iata='COR', nombre='Pajas Blancas', ciudad='Córdoba', pais='Argentina')
        cls.avion = Avion.objects.create(matricula='LV-FAA', modelo='Airbus A320', capacidad_economy=150, capacidad_primera=12)
        cls.vuelos = [cls.crear_vuelo(f'FA {1000 + n}', HOY + dt.timedelta(days=n + 1)) for n in range(4)]

    @classmethod
    def crear_vuelo(cls, numero, fecha, **cambios):
        datos = dict(
            numero_vuelo=numero,
            avion=cls.avion,
            aeropuerto_origen=cls.aep,
            aeropuerto_destino=cls.cor,
            fecha_operacion=fecha,
            fecha_llegada=fecha,
            hora_partida=dt.time(15, 0),
            hora_llegada=dt.time(16, 30),
            precio_economy=Decimal('100000.00'),
            precio_primera=Decimal('250000.00'),
            asientos_disponibles_economy=30,
            asientos_disponibles_primera=12,
            creado_por=cls.admin,
        )
        datos.update(cambios)
        return Vuelo.objects.create(**datos)

    def setUp(self):
        reloj = patch('django.utils.timezone.now', return_value=AHORA)
        reloj.start()
        self.addCleanup(reloj.stop)
        self.client.force_authenticate(self.pasajero)

    def reserva(self, clase='economy', cantidad=1, vuelo=None, pasajero=None):
        return ReservaDemo.objects.create(
            pasajero=pasajero or self.pasajero, vuelo=vuelo or self.vuelos[0], clase=clase, cantidad=cantidad
        )

    def pago(self, reserva, estado=Pago.Estado.APROBADO, metodo=Pago.Metodo.TARJETA, **campos):
        return Pago.objects.create(reserva_id=reserva.id, monto=Decimal('100000.00'), estado=estado, metodo_pago=metodo, **campos)


class ModeloTests(Datos):
    def test_tablas_con_los_nombres_del_dbml(self):
        self.assertEqual(Pago._meta.db_table, 'pagos')
        self.assertEqual(ReservaDemo._meta.db_table, 'reservas_demo')

    def test_una_reserva_no_admite_dos_pagos_aprobados(self):
        reserva = self.reserva()
        self.pago(reserva)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.pago(reserva)

    def test_una_reserva_admite_varios_rechazados(self):
        reserva = self.reserva()
        self.pago(reserva, estado=Pago.Estado.RECHAZADO)
        self.pago(reserva, estado=Pago.Estado.RECHAZADO)
        self.pago(reserva)
        self.assertEqual(Pago.objects.filter(reserva_id=reserva.id).count(), 3)

    def test_reserva_demo_entre_1_y_9_pasajes(self):
        for cantidad in (0, 10):
            with self.assertRaises(IntegrityError), transaction.atomic():
                self.reserva(cantidad=cantidad)


class ReservasDemoTests(Datos):
    def test_la_primera_vez_crea_tres_reservas_en_vuelos_distintos(self):
        reservas = reservas_mock.reservas_de(self.pasajero)
        self.assertEqual([(r.clase, r.cantidad) for r in reservas], [('economy', 1), ('primera', 2), ('economy', 9)])
        self.assertEqual([r.vuelo for r in reservas], self.vuelos[:3])

    def test_despues_devuelve_siempre_las_mismas(self):
        primeras = [r.id for r in reservas_mock.reservas_de(self.pasajero)]
        Vuelo.objects.filter(id=self.vuelos[2].id).update(asientos_disponibles_economy=0)
        self.crear_vuelo('FA 2000', HOY, hora_partida=dt.time(20, 0), hora_llegada=dt.time(21, 0))
        self.assertEqual([r.id for r in reservas_mock.reservas_de(self.pasajero)], primeras)

    def test_saltea_vuelos_cancelados_salidos_o_sin_lugar(self):
        Vuelo.objects.filter(id=self.vuelos[0].id).update(estado=Vuelo.Estado.CANCELADO)
        self.crear_vuelo('FA 2001', HOY, hora_partida=dt.time(9, 0), hora_llegada=dt.time(10, 0))  # ya salió
        reservas = reservas_mock.reservas_de(self.pasajero)
        self.assertNotIn(self.vuelos[0], [r.vuelo for r in reservas])
        self.assertEqual(reservas[0].vuelo, self.vuelos[1])

    def test_monto_es_la_suma_de_los_pasajes(self):
        reserva = self.reserva(clase='primera', cantidad=2)
        self.assertEqual(reservas_mock.pasajes_de(reserva), [('primera', Decimal('250000.00'))] * 2)
        self.assertEqual(reservas_mock.monto_de(reserva), Decimal('500000.00'))

    def test_reserva_de_solo_devuelve_las_propias(self):
        propia = self.reserva()
        ajena = self.reserva(pasajero=self.otro)
        self.assertEqual(reservas_mock.reserva_de(self.pasajero, propia.id), propia)
        self.assertIsNone(reservas_mock.reserva_de(self.pasajero, ajena.id))
        self.assertIsNone(reservas_mock.reserva_de(self.pasajero, 'no-es-un-uuid'))


class ReservasApiTests(Datos):
    def test_lista_las_reservas_con_monto_y_estado(self):
        r = self.client.get('/api/pagos/reservas/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 3)
        primera = r.data[0]
        self.assertEqual(primera['vuelo']['numero_vuelo'], 'FA 1000')
        self.assertEqual(primera['vuelo']['origen'], 'AEP')
        self.assertEqual(primera['monto'], '100000.00')
        self.assertEqual(primera['estado'], 'pendiente')

    def test_una_reserva_con_pago_aprobado_figura_pagada(self):
        reserva = reservas_mock.reservas_de(self.pasajero)[0]
        self.pago(reserva)
        self.assertEqual(self.client.get('/api/pagos/reservas/').data[0]['estado'], 'pagada')

    def test_solo_pasajeros(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/pagos/reservas/').status_code, 401)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/pagos/reservas/').status_code, 403)
