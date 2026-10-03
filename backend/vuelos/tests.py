import datetime as dt
import uuid
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
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
        fecha = fecha or HOY + dt.timedelta(days=1)
        sale = dt.time.fromisoformat(partida)
        llega = dt.datetime.combine(fecha, sale) + dt.timedelta(hours=1)  # dura 1 h; puede cruzar medianoche
        datos = dict(
            numero_vuelo=numero,
            avion=self.avion,
            aeropuerto_origen=origen or self.bhi,
            aeropuerto_destino=destino or self.aep,
            fecha_operacion=fecha,
            fecha_llegada=llega.date(),
            hora_partida=sale,
            hora_llegada=llega.time(),
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

    def test_la_llegada_es_posterior_a_la_partida(self):
        nocturno = self.vuelo(partida='23:30')  # llega 00:30 del día siguiente
        self.assertEqual(nocturno.fecha_llegada, nocturno.fecha_operacion + dt.timedelta(days=1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo('FA 2', hora_llegada=dt.time(14, 0))  # mismo día, llega antes de salir
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo('FA 3', fecha_llegada=HOY)  # llega el día anterior


VUELO_CAMPOS = {
    'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'fecha_llegada', 'hora_partida', 'hora_llegada',
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
        self.assertEqual(d['fecha_llegada'], str(HOY + dt.timedelta(days=1)))

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


MANANA = HOY + dt.timedelta(days=1)


class BuscarTests(Datos):
    def buscar(self, **params):
        r = self.client.get('/api/vuelos/buscar/', {'desde': str(HOY), **params})
        self.assertEqual(r.status_code, 200, r.content)
        return [v['numero_vuelo'] for v in r.json()]

    def test_forma_de_la_respuesta(self):
        self.vuelo()
        r = self.client.get('/api/vuelos/buscar/', {'origen': 'BHI', 'desde': str(MANANA)})
        self.assertEqual(set(r.json()[0]), VUELO_CAMPOS)

    def test_filtra_cancelados_y_sin_lugar(self):
        self.vuelo('FA 1')
        self.vuelo('FA 2', estado=Vuelo.Estado.CANCELADO)
        self.vuelo('FA 3', asientos_disponibles_economy=1)
        self.vuelo('FA 4', asientos_disponibles_primera=1)
        self.assertEqual(self.buscar(origen='BHI', desde=str(MANANA), pasajeros=2), ['FA 1', 'FA 4'])
        self.assertEqual(self.buscar(origen='BHI', desde=str(MANANA), pasajeros=2, clase='primera'), ['FA 1', 'FA 3'])

    def test_ruta(self):
        self.vuelo('FA 1', origen=self.bhi, destino=self.aep)
        self.vuelo('FA 2', origen=self.bhi, destino=self.cor)
        self.vuelo('FA 3', origen=self.cor, destino=self.aep)
        d = str(MANANA)
        self.assertEqual(self.buscar(origen='BHI', desde=d), ['FA 1', 'FA 2'])
        self.assertEqual(self.buscar(destino='AEP', desde=d), ['FA 1', 'FA 3'])
        self.assertEqual(self.buscar(origen='BHI', destino='AEP', desde=d), ['FA 1'])

    def test_rango_de_fechas_sin_limite(self):
        self.vuelo('FA 1', fecha=HOY + dt.timedelta(days=1))
        self.vuelo('FA 2', fecha=HOY + dt.timedelta(days=3))
        self.vuelo('FA 3', fecha=HOY + dt.timedelta(days=40))
        desde = str(HOY + dt.timedelta(days=1))
        self.assertEqual(self.buscar(origen='BHI', desde=desde), ['FA 1'], 'sin hasta: solo ese día')
        hasta = str(HOY + dt.timedelta(days=40))
        self.assertEqual(self.buscar(origen='BHI', desde=desde, hasta=hasta), ['FA 1', 'FA 2', 'FA 3'])

    def test_rango_de_precio_en_la_clase_elegida(self):
        self.vuelo('FA 1', precio_economy=Decimal('80000'), precio_primera=Decimal('300000'))
        self.vuelo('FA 2', precio_economy=Decimal('120000'), precio_primera=Decimal('150000'))
        d = str(MANANA)
        self.assertEqual(self.buscar(origen='BHI', desde=d, precio_min='100000'), ['FA 2'])
        self.assertEqual(self.buscar(origen='BHI', desde=d, precio_max='100000'), ['FA 1'])
        self.assertEqual(self.buscar(origen='BHI', desde=d, clase='primera', precio_max='200000'), ['FA 2'])
        self.assertEqual(self.buscar(origen='BHI', desde=d, precio_min='80000', precio_max='120000'), ['FA 1', 'FA 2'])

    def test_no_ofrece_vuelos_que_ya_salieron(self):
        self.vuelo('FA 1', fecha=HOY, partida='11:00')
        self.vuelo('FA 2', fecha=HOY, partida='12:00')  # sale justo ahora
        self.vuelo('FA 3', fecha=HOY, partida='12:30')
        self.vuelo('FA 4', fecha=MANANA, partida='08:00')
        self.assertEqual(self.buscar(origen='BHI', hasta=str(MANANA)), ['FA 3', 'FA 4'])

    def test_hoy_es_la_fecha_de_buenos_aires(self):
        # 23:30 en Buenos Aires = 02:30 UTC del día siguiente.
        noche = dt.datetime(2026, 10, 20, 23, 30, tzinfo=BA)
        self.vuelo('FA 1', fecha=HOY, partida='22:00')
        self.vuelo('FA 2', fecha=HOY, partida='23:45')
        with patch('django.utils.timezone.now', return_value=noche):
            self.assertEqual(self.buscar(origen='BHI'), ['FA 2'])

    def test_orden_por_fecha_y_hora(self):
        self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1), partida='08:00')
        self.vuelo('FA 2', fecha=MANANA, partida='18:00')
        self.vuelo('FA 3', fecha=MANANA, partida='09:00')
        hasta = str(MANANA + dt.timedelta(days=1))
        self.assertEqual(self.buscar(origen='BHI', desde=str(MANANA), hasta=hasta), ['FA 3', 'FA 2', 'FA 1'])

    def test_parametros_vacios_cuentan_como_no_enviados(self):
        self.vuelo('FA 1')
        self.assertEqual(
            self.buscar(origen='BHI', destino='', desde=str(MANANA), hasta='', precio_min='', precio_max=''), ['FA 1']
        )

    def test_iata_en_minusculas(self):
        self.vuelo('FA 1')
        self.assertEqual(self.buscar(origen='bhi', destino='aep', desde=str(MANANA)), ['FA 1'])


class ErroresBusquedaTests(Datos):
    BASE = {'origen': 'BHI', 'desde': str(HOY)}

    def error(self, params, clave, mensaje):
        r = self.client.get('/api/vuelos/buscar/', params)
        self.assertEqual(r.status_code, 400, params)
        self.assertEqual(r.json(), {clave: [mensaje]}, params)

    def test_ruta(self):
        self.error({'desde': str(HOY)}, 'origen', 'Indicá un origen, un destino o ambos.')
        self.error({**self.BASE, 'origen': 'ZZZ'}, 'origen', 'No conocemos el aeropuerto "ZZZ".')
        self.error({**self.BASE, 'destino': 'zzz'}, 'destino', 'No conocemos el aeropuerto "ZZZ".')
        self.error({**self.BASE, 'destino': 'BHI'}, 'destino', 'El destino tiene que ser distinto del origen.')
        self.error({**self.BASE, 'origen': 'AEP', 'destino': 'EZE'}, 'destino', 'Origen y destino están en la misma ciudad.')

    def test_fechas(self):
        fecha_invalida = 'Indicá una fecha válida (AAAA-MM-DD).'
        self.error({'origen': 'BHI'}, 'desde', fecha_invalida)
        self.error({**self.BASE, 'desde': 'mañana'}, 'desde', fecha_invalida)
        self.error({**self.BASE, 'desde': '2027-02-30'}, 'desde', fecha_invalida)
        self.error({**self.BASE, 'desde': str(HOY - dt.timedelta(days=1))}, 'desde', 'La fecha no puede ser en el pasado.')
        self.error({**self.BASE, 'hasta': 'x'}, 'hasta', fecha_invalida)
        self.error(
            {**self.BASE, 'desde': str(MANANA), 'hasta': str(HOY)}, 'hasta', '"Hasta" no puede ser antes de "Desde".'
        )

    def test_pasajeros_y_clase(self):
        for pasajeros in ('0', '10', 'dos', '1.5'):
            self.error({**self.BASE, 'pasajeros': pasajeros}, 'pasajeros', 'Tienen que ser entre 1 y 9 pasajeros.')
        self.error({**self.BASE, 'clase': 'business'}, 'clase', 'La clase tiene que ser economy o primera.')

    def test_precio(self):
        for monto in ('-1', 'abc', 'nan', 'inf'):
            self.error({**self.BASE, 'precio_min': monto}, 'precio_min', 'Ingresá un monto válido.')
            self.error({**self.BASE, 'precio_max': monto}, 'precio_max', 'Ingresá un monto válido.')
        self.error(
            {**self.BASE, 'precio_min': '200', 'precio_max': '100'},
            'precio_min',
            'El mínimo no puede ser mayor que el máximo.',
        )


class SeedTests(Datos):
    def correr(self):
        call_command('seed', dias=3, stdout=StringIO())

    def test_carga_datos_de_ejemplo(self):
        self.correr()
        self.assertEqual(Aeropuerto.objects.count(), 11)
        self.assertEqual(Avion.objects.count(), 4)
        self.assertGreater(Vuelo.objects.count(), 0)
        sistema = get_user_model().objects.get(email='sistema@flyaway.local')
        self.assertEqual(sistema.rol, 'administrador')
        self.assertFalse(sistema.has_usable_password())

    def test_vuelos_coherentes(self):
        self.correr()
        vuelos = Vuelo.objects.select_related('aeropuerto_origen', 'aeropuerto_destino')
        for v in vuelos:
            self.assertNotEqual(v.aeropuerto_origen.ciudad, v.aeropuerto_destino.ciudad, v)
            self.assertGreater(v.hora_llegada, v.hora_partida, v)
            self.assertTrue(HOY <= v.fecha_operacion < HOY + dt.timedelta(days=3), v)

    def test_idempotente_y_no_pisa_cambios(self):
        self.correr()
        cantidades = (Aeropuerto.objects.count(), Avion.objects.count(), Vuelo.objects.count())
        v = Vuelo.objects.first()
        v.asientos_disponibles_economy = 0
        v.save()
        self.correr()
        self.assertEqual((Aeropuerto.objects.count(), Avion.objects.count(), Vuelo.objects.count()), cantidades)
        v.refresh_from_db()
        self.assertEqual(v.asientos_disponibles_economy, 0)

    def test_no_pisa_correcciones_del_admin(self):
        self.correr()
        Aeropuerto.objects.filter(codigo_iata='BHI').update(nombre='Corregido a mano')
        Avion.objects.filter(matricula='LV-FAA').update(capacidad_economy=140)
        self.correr()
        self.assertEqual(Aeropuerto.objects.get(codigo_iata='BHI').nombre, 'Corregido a mano')
        self.assertEqual(Avion.objects.get(matricula='LV-FAA').capacidad_economy, 140)


class MigracionFechaLlegadaTests(TransactionTestCase):
    def migrar(self, destino):
        ejecutor = MigrationExecutor(connection)
        ejecutor.migrate(destino)
        return MigrationExecutor(connection).loader.project_state(destino).apps

    def test_completa_las_filas_existentes(self):
        ultima = MigrationExecutor(connection).loader.graph.leaf_nodes('vuelos')
        self.addCleanup(self.migrar, ultima)  # si falla a mitad de camino, la base vuelve al esquema actual
        apps = self.migrar([('vuelos', '0001_initial')])
        admin = apps.get_model('usuarios', 'Usuario').objects.create(
            email='a@mail.com', password='x', nombre='A', apellido='B', rol='administrador'
        )
        Aeropuerto_ = apps.get_model('vuelos', 'Aeropuerto')
        bhi = Aeropuerto_.objects.create(codigo_iata='BHI', nombre='x', ciudad='Bahía Blanca', pais='Argentina')
        aep = Aeropuerto_.objects.create(codigo_iata='AEP', nombre='x', ciudad='Buenos Aires', pais='Argentina')
        avion = apps.get_model('vuelos', 'Avion').objects.create(
            matricula='LV-FAA', modelo='x', capacidad_economy=10, capacidad_primera=2
        )
        apps.get_model('vuelos', 'Vuelo').objects.create(
            numero_vuelo='FA 1', avion=avion, aeropuerto_origen=bhi, aeropuerto_destino=aep,
            fecha_operacion=HOY, hora_partida=dt.time(10), hora_llegada=dt.time(11),
            precio_economy=1, precio_primera=2, asientos_disponibles_economy=10, asientos_disponibles_primera=2,
            creado_por=admin,
        )
        apps = self.migrar(ultima)
        self.assertEqual(apps.get_model('vuelos', 'Vuelo').objects.get().fecha_llegada, HOY)
