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

from reservas.models import Pasaje, Reserva

from .models import Aeropuerto, Avion, Vuelo

BA = ZoneInfo('America/Argentina/Buenos_Aires')
AHORA = dt.datetime(2026, 10, 20, 12, 0, tzinfo=BA)  # mediodía en Buenos Aires
HOY = AHORA.date()
MANANA = HOY + dt.timedelta(days=1)


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
        self.assertEqual(d['avion'], {
            'id': str(self.avion.id), 'matricula': 'LV-FAA', 'modelo': 'Airbus A320',
            'capacidad_economy': 150, 'capacidad_primera': 12,
        })
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
    def correr(self, vuelos=True):
        call_command('seed', dias=3, vuelos=vuelos, stdout=StringIO())

    def test_sin_vuelos_carga_solo_el_catalogo(self):
        self.correr(vuelos=False)
        self.assertEqual((Aeropuerto.objects.count(), Avion.objects.count(), Vuelo.objects.count()), (11, 10, 0))

    def test_los_vuelos_de_ejemplo_usan_los_primeros_cuatro_aviones(self):
        self.correr()
        usados = set(Vuelo.objects.values_list('avion__matricula', flat=True))
        self.assertLessEqual(usados, {'LV-FAA', 'LV-FAB', 'LV-FAC', 'LV-FAD'})

    def test_carga_datos_de_ejemplo(self):
        self.correr()
        self.assertEqual(Aeropuerto.objects.count(), 11)
        self.assertEqual(Avion.objects.count(), 10)
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

    def vendidos(self, vuelo, clase):
        return Pasaje.objects.filter(reserva__vuelo=vuelo, reserva__estado='pagada', clase=clase).count()

    def assert_ventas_reales(self, vuelos):
        """Cada lugar vendido es una compra confirmada: vendidos + disponibles = capacidad, por clase."""
        for v in vuelos.select_related('avion'):
            for clase in ('economy', 'primera'):
                self.assertEqual(
                    self.vendidos(v, clase) + getattr(v, f'asientos_disponibles_{clase}'),
                    getattr(v.avion, f'capacidad_{clase}'),
                    f'{v} {clase}',
                )

    def test_los_vendidos_de_ejemplo_son_compras_reales(self):
        self.correr()
        vuelos = Vuelo.objects.all()
        self.assert_ventas_reales(vuelos)
        por_vuelo = [Pasaje.objects.filter(reserva__vuelo=v).count() for v in vuelos]
        self.assertTrue(all(0 <= n <= 5 for n in por_vuelo), max(por_vuelo))
        self.assertGreater(sum(por_vuelo), 0)
        for reserva in Reserva.objects.all():
            self.assertEqual(reserva.estado, 'pagada')
            self.assertEqual(reserva.cantidad_pasajes, reserva.pasajes.count())
            self.assertEqual(list(reserva.pagos.values_list('estado', flat=True)), ['aprobado'])
            self.assertEqual(reserva.pagos.get().monto, reserva.monto)

    def test_correr_dos_veces_no_duplica_ventas(self):
        self.correr()
        pasajes = Pasaje.objects.count()
        self.correr()
        self.assertEqual(Pasaje.objects.count(), pasajes)

    def test_regenerar_limpia_los_vuelos_de_ejemplo_viejos(self):
        sistema = get_user_model().objects.create_user(
            'sistema@flyaway.local', None, nombre='Sistema', apellido='Fly Away', rol='administrador'
        )
        # Vuelos de ejemplo como los del seed anterior: lugares "vendidos" sin pasajes.
        viejo = self.vuelo('FA 9990', creado_por=sistema, asientos_disponibles_economy=3, asientos_disponibles_primera=1)
        con_compra = self.vuelo(
            'FA 9991', fecha=HOY + dt.timedelta(days=2), creado_por=sistema,
            asientos_disponibles_economy=5, asientos_disponibles_primera=2,
        )
        reserva = Reserva.objects.create(
            pasajero=self.admin, contacto_email='a@mail.com', vuelo=con_compra, cantidad_pasajes=2, estado='pagada'
        )
        for i in range(2):
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=f'X-{i}', nombre_pasajero='Ana', apellido_pasajero='Pérez',
                dni_pasajero='12345678', clase='economy', precio=Decimal('1.00'),
            )
        del_admin = self.vuelo('FA 1', fecha=HOY + dt.timedelta(days=3), asientos_disponibles_economy=30)

        call_command('seed', vuelos=True, regenerar=True, stdout=StringIO())

        self.assertFalse(Vuelo.objects.filter(id=viejo.id).exists())
        con_compra.refresh_from_db()
        self.assertEqual((con_compra.asientos_disponibles_economy, con_compra.asientos_disponibles_primera), (148, 12))
        del_admin.refresh_from_db()
        self.assertEqual(del_admin.asientos_disponibles_economy, 30, 'no toca los vuelos cargados por el admin')
        regenerados = Vuelo.objects.filter(creado_por=sistema)
        self.assertGreater(regenerados.count(), 1)
        self.assertEqual(
            set(regenerados.values_list('fecha_operacion', flat=True)), {HOY + dt.timedelta(days=1), HOY + dt.timedelta(days=2)},
            'las mismas fechas que tenían los vuelos de ejemplo',
        )
        self.assert_ventas_reales(regenerados)


    def test_regenerar_tambien_rehace_los_vuelos_con_ventas_de_ejemplo(self):
        self.correr()
        vendido = Vuelo.objects.filter(reservas__pasajero__email='sistema@flyaway.local').distinct().first()
        precio = vendido.precio_economy
        Vuelo.objects.filter(id=vendido.id).update(precio_economy=Decimal('1.00'))

        call_command('seed', vuelos=True, regenerar=True, stdout=StringIO())

        self.assertFalse(Vuelo.objects.filter(id=vendido.id).exists(), 'sus ventas eran de ejemplo: se regenera')
        nuevo = Vuelo.objects.get(numero_vuelo=vendido.numero_vuelo, fecha_operacion=vendido.fecha_operacion)
        self.assertEqual(nuevo.precio_economy, precio)
        self.assert_ventas_reales(Vuelo.objects.all())


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
        # Una fila cargada a mano que llega "antes" de salir: cruzaba medianoche.
        apps.get_model('vuelos', 'Vuelo').objects.create(
            numero_vuelo='FA 2', avion=avion, aeropuerto_origen=bhi, aeropuerto_destino=aep,
            fecha_operacion=HOY, hora_partida=dt.time(23), hora_llegada=dt.time(1),
            precio_economy=1, precio_primera=2, asientos_disponibles_economy=10, asientos_disponibles_primera=2,
            creado_por=admin,
        )
        apps = self.migrar(ultima)
        llegadas = dict(apps.get_model('vuelos', 'Vuelo').objects.values_list('numero_vuelo', 'fecha_llegada'))
        self.assertEqual(llegadas, {'FA 1': HOY, 'FA 2': HOY + dt.timedelta(days=1)})


class AdminDatos(Datos):
    """Sesión de administrador. HOY es martes 2026-10-20."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        crear = get_user_model().objects.create_user
        cls.pasajero = crear('pasajero@mail.com', 'x', nombre='Pepe', apellido='P', rol='pasajero')
        cls.empleado = crear('empleado@mail.com', 'x', nombre='Eva', apellido='E', rol='empleado_mostrador')
        cls.avion2 = Avion.objects.create(
            matricula='LV-FAB', modelo='Embraer E190', capacidad_economy=96, capacidad_primera=8
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.admin)

    def solo_admin(self, metodo, url):
        pedir = getattr(self.client, metodo)
        extra = {} if metodo == 'get' else {'data': {}, 'format': 'json'}
        self.client.force_authenticate(None)
        self.assertEqual(pedir(url, **extra).status_code, 401, url)
        for usuario in (self.pasajero, self.empleado):
            self.client.force_authenticate(usuario)
            self.assertEqual(pedir(url, **extra).status_code, 403, url)
        self.client.force_authenticate(self.admin)


class AltaTests(AdminDatos):
    def periodo(self, **cambios):
        # Del miércoles 21/10 al martes 3/11, lunes y miércoles: 21/10, 26/10, 28/10 y 2/11.
        return {
            'desde': str(MANANA), 'hasta': str(MANANA + dt.timedelta(days=13)), 'dias': [0, 2],
            'avion': str(self.avion.id), 'precio_economy': '85000.00', 'precio_primera': '190000.00', **cambios,
        }

    def datos(self, **cambios):
        return {
            'origen': 'BHI', 'destino': 'AEP', 'hora_partida': '08:30', 'hora_llegada': '10:45',
            'periodos': [self.periodo()], **cambios,
        }

    def crear(self, datos):
        return self.client.post('/api/vuelos/', datos, format='json')

    def rechaza(self, datos, vuelos_antes=0):
        r = self.crear(datos)
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(Vuelo.objects.count(), vuelos_antes, 'el alta es atómica')
        return r.json()

    def test_solo_el_administrador(self):
        self.solo_admin('post', '/api/vuelos/')

    def test_genera_una_instancia_por_fecha(self):
        r = self.crear(self.datos())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json(), {'numero_vuelo': 'FA 1000', 'cantidad': 4})
        vuelos = list(Vuelo.objects.filter(numero_vuelo='FA 1000'))
        self.assertEqual(
            [v.fecha_operacion for v in vuelos],
            [dt.date(2026, 10, 21), dt.date(2026, 10, 26), dt.date(2026, 10, 28), dt.date(2026, 11, 2)],
        )
        self.assertEqual(len({v.id for v in vuelos}), 4, 'un id por fecha')
        for v in vuelos:
            self.assertEqual(v.fecha_llegada, v.fecha_operacion)
            self.assertEqual((v.hora_partida, v.hora_llegada), (dt.time(8, 30), dt.time(10, 45)))
            self.assertEqual((v.aeropuerto_origen, v.aeropuerto_destino, v.avion), (self.bhi, self.aep, self.avion))
            self.assertEqual((v.asientos_disponibles_economy, v.asientos_disponibles_primera), (150, 12))
            self.assertEqual((v.precio_economy, v.precio_primera), (Decimal('85000.00'), Decimal('190000.00')))
            self.assertEqual((v.estado, v.creado_por), (Vuelo.Estado.ACTIVO, self.admin))

    def test_numero_siguiente_al_mas_alto(self):
        self.vuelo('FA 2203', fecha=MANANA + dt.timedelta(days=60))
        self.vuelo('FA 1500', fecha=MANANA + dt.timedelta(days=61))
        self.assertEqual(self.crear(self.datos()).json()['numero_vuelo'], 'FA 2204')

    def test_cada_periodo_con_su_avion_y_sus_precios(self):
        jueves = MANANA + dt.timedelta(days=1)
        periodos = [
            self.periodo(hasta=str(MANANA), dias=[2]),
            self.periodo(desde=str(jueves), hasta=str(jueves), dias=[3], avion=str(self.avion2.id), precio_economy='99000.00'),
        ]
        r = self.crear(self.datos(periodos=periodos))
        self.assertEqual(r.json()['cantidad'], 2, r.content)
        segundo = Vuelo.objects.get(fecha_operacion=jueves)
        self.assertEqual(segundo.avion, self.avion2)
        self.assertEqual((segundo.asientos_disponibles_economy, segundo.asientos_disponibles_primera), (96, 8))
        self.assertEqual(segundo.precio_economy, Decimal('99000.00'))
        self.assertEqual(segundo.numero_vuelo, Vuelo.objects.get(fecha_operacion=MANANA).numero_vuelo)

    def test_cruza_medianoche(self):
        r = self.crear(self.datos(hora_partida='23:00', hora_llegada='01:30'))
        self.assertEqual(r.status_code, 201, r.content)
        for v in Vuelo.objects.all():
            self.assertEqual(v.fecha_llegada, v.fecha_operacion + dt.timedelta(days=1))

    def test_validaciones(self):
        self.assertEqual(set(self.rechaza({})), {'origen', 'destino', 'hora_partida', 'hora_llegada', 'periodos'})
        self.assertIn('periodos', self.rechaza(self.datos(periodos=[])))
        self.assertEqual(
            self.rechaza(self.datos(destino='BHI')), {'destino': ['El destino tiene que ser distinto del origen.']}
        )
        self.assertEqual(
            self.rechaza(self.datos(origen='AEP', destino='EZE')),
            {'destino': ['Origen y destino están en la misma ciudad.']},
        )
        self.assertEqual(self.rechaza(self.datos(origen='ZZZ')), {'origen': ['No conocemos el aeropuerto "ZZZ".']})
        self.assertEqual(
            self.rechaza(self.datos(hora_llegada='08:30')),
            {'hora_llegada': ['La llegada no puede ser a la misma hora que la partida.']},
        )

        def periodo_invalido(clave, mensaje=None, **cambios):
            # DRF indexa los errores de una lista por posición: {'periodos': {'0': {...}}}
            errores = self.rechaza(self.datos(periodos=[self.periodo(**cambios)]))['periodos']['0']
            self.assertIn(clave, errores, cambios)
            if mensaje:
                self.assertEqual(errores[clave], [mensaje])

        periodo_invalido('desde', 'La fecha no puede ser en el pasado.', desde=str(HOY - dt.timedelta(days=1)))
        periodo_invalido('hasta', '"Hasta" no puede ser antes de "Desde".', hasta=str(HOY))
        periodo_invalido(
            'hasta', 'El período no puede pasar de un año desde hoy.', hasta=str(HOY + dt.timedelta(days=366))
        )
        periodo_invalido('dias', dias=[])
        periodo_invalido('dias', dias=[7])
        periodo_invalido('dias', 'Ningún día del rango cae en los días elegidos.', hasta=str(MANANA), dias=[0])
        periodo_invalido('precio_economy', 'El precio tiene que ser mayor a cero.', precio_economy='0')
        periodo_invalido('precio_primera', precio_primera='abc')
        periodo_invalido('avion', avion='no-es-un-uuid')
        periodo_invalido('avion', avion=str(uuid.uuid4()))

    def test_fechas_repetidas_entre_periodos(self):
        periodos = [self.periodo(), self.periodo(avion=str(self.avion2.id), dias=[2, 4])]
        errores = self.rechaza(self.datos(periodos=periodos))
        self.assertEqual(
            errores, {'non_field_errors': ['Hay fechas repetidas entre períodos: 2026-10-21, 2026-10-28.']}
        )

    def test_hoy_con_horario_pasado(self):
        hoy = self.periodo(desde=str(HOY), hasta=str(HOY), dias=[1])  # martes; AHORA son las 12:00
        self.assertEqual(
            self.rechaza(self.datos(hora_partida='11:00', hora_llegada='12:30', periodos=[hoy])),
            {'hora_partida': ['Ese horario ya pasó para hoy.']},
        )
        self.assertEqual(self.crear(self.datos(hora_partida='13:00', hora_llegada='14:30', periodos=[hoy])).status_code, 201)

    def test_avion_ocupado(self):
        otro = self.vuelo('FA 1', fecha=MANANA, partida='09:00')  # LV-FAA de 09:00 a 10:00
        self.assertEqual(
            self.rechaza(self.datos(), vuelos_antes=1),
            {'non_field_errors': ['LV-FAA ya está asignado al FA 1 el 2026-10-21 de 09:00 a 10:00.']},
        )
        otro.estado = Vuelo.Estado.CANCELADO
        otro.save()
        self.assertEqual(self.crear(self.datos()).status_code, 201, 'un cancelado no ocupa el avión')

    def test_avion_libre_si_los_horarios_se_tocan_sin_pisarse(self):
        self.vuelo('FA 1', fecha=MANANA, partida='10:45')  # sale justo cuando aterriza el nuevo
        self.assertEqual(self.crear(self.datos()).status_code, 201)

    def test_avion_ocupado_cruzando_medianoche(self):
        self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1), partida='00:30')  # madrugada del jueves
        nocturno = self.datos(hora_partida='23:00', hora_llegada='01:00', periodos=[self.periodo(hasta=str(MANANA), dias=[2])])
        self.assertEqual(
            self.rechaza(nocturno, vuelos_antes=1),
            {'non_field_errors': ['LV-FAA ya está asignado al FA 1 el 2026-10-22 de 00:30 a 01:30.']},
        )

    def test_doble_envio(self):
        self.assertEqual(self.crear(self.datos()).status_code, 201)
        self.assertIn('non_field_errors', self.rechaza(self.datos(), vuelos_antes=4))

    def test_choque_de_numero(self):
        self.vuelo('FA 1', fecha=MANANA, partida='15:00', avion=self.avion2)
        with patch('vuelos.servicios.siguiente_numero', return_value='FA 1'):
            errores = self.rechaza(self.datos(), vuelos_antes=1)
        self.assertEqual(errores, {'non_field_errors': ['No se pudo asignar el número de vuelo. Probá de nuevo.']})


class ListadoTests(AdminDatos):
    def listar(self, **params):
        r = self.client.get('/api/vuelos/', params)
        self.assertEqual(r.status_code, 200, r.content)
        return [v['numero_vuelo'] for v in r.json()['results']]

    def test_solo_el_administrador(self):
        self.solo_admin('get', '/api/vuelos/')
        self.solo_admin('get', '/api/aviones/')

    def test_desde_hoy_ordenado_y_con_avion(self):
        self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1))
        self.vuelo('FA 2', fecha=MANANA, partida='18:00')
        self.vuelo('FA 3', fecha=MANANA, partida='09:00', estado=Vuelo.Estado.CANCELADO)
        self.vuelo('FA 4', fecha=HOY - dt.timedelta(days=1))
        r = self.client.get('/api/vuelos/')
        d = r.json()
        self.assertEqual((d['count'], d['next'], d['previous']), (3, None, None))
        self.assertEqual([v['numero_vuelo'] for v in d['results']], ['FA 3', 'FA 2', 'FA 1'])
        self.assertEqual(set(d['results'][0]), VUELO_CAMPOS | {'avion'})
        self.assertEqual(d['results'][0]['avion']['id'], str(self.avion.id))

    def test_filtros(self):
        a = self.vuelo('FA 10', fecha=MANANA)
        self.vuelo('FA 20', fecha=MANANA, origen=self.cor, destino=self.aep, partida='10:00', avion=self.avion2)
        self.vuelo('FA 30', fecha=MANANA + dt.timedelta(days=5), estado=Vuelo.Estado.CANCELADO)
        viejo = self.vuelo('FA 40', fecha=HOY - dt.timedelta(days=3))
        self.assertEqual(self.listar(q='fa 1'), ['FA 10'])
        self.assertEqual(self.listar(q=str(a.id)), ['FA 10'])
        self.assertEqual(self.listar(q=str(viejo.id)), ['FA 40'], 'por id se llega a un vuelo pasado')
        self.assertEqual(self.listar(origen='cor'), ['FA 20'])
        self.assertEqual(self.listar(destino='AEP', hasta=str(MANANA)), ['FA 20', 'FA 10'], 'por hora de partida')
        self.assertEqual(self.listar(estado='cancelado'), ['FA 30'])
        self.assertEqual(self.listar(desde=str(HOY - dt.timedelta(days=3)), hasta=str(HOY)), ['FA 40'])
        self.assertEqual(self.listar(q='', origen='', estado=''), ['FA 20', 'FA 10', 'FA 30'], 'vacío = no enviado')

    def test_filtros_invalidos(self):
        r = self.client.get('/api/vuelos/', {'desde': 'ayer'})
        self.assertEqual((r.status_code, r.json()), (400, {'desde': ['Indicá una fecha válida (AAAA-MM-DD).']}))
        self.assertEqual(self.client.get('/api/vuelos/', {'estado': 'demorado'}).status_code, 400)

    def test_paginas_de_50(self):
        for n in range(51):
            self.vuelo(f'FA {n}', fecha=MANANA + dt.timedelta(days=n))
        primera = self.client.get('/api/vuelos/').json()
        self.assertEqual((primera['count'], len(primera['results'])), (51, 50))
        self.assertIsNotNone(primera['next'])
        self.assertEqual(len(self.client.get('/api/vuelos/', {'page': 2}).json()['results']), 1)
        self.assertEqual(self.client.get('/api/vuelos/', {'page': 9}).status_code, 404)

    def test_aviones(self):
        r = self.client.get('/api/aviones/')
        self.assertEqual([a['matricula'] for a in r.json()], ['LV-FAA', 'LV-FAB'])
        self.assertEqual(set(r.json()[0]), {'id', 'matricula', 'modelo', 'capacidad_economy', 'capacidad_primera'})


class EdicionTests(AdminDatos):
    def editar(self, vuelo, **cambios):
        return self.client.patch(f'/api/vuelos/{vuelo.id}/', cambios, format='json')

    def rechaza(self, vuelo, **cambios):
        r = self.editar(vuelo, **cambios)
        self.assertEqual(r.status_code, 400, r.content)
        return r.json()

    def test_solo_el_administrador_edita_y_el_detalle_sigue_publico(self):
        v = self.vuelo()
        self.solo_admin('patch', f'/api/vuelos/{v.id}/')
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f'/api/vuelos/{v.id}/').status_code, 200)

    def test_edita_solo_esa_instancia(self):
        v = self.vuelo('FA 1', fecha=MANANA)
        otra = self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1))
        r = self.editar(
            v, hora_partida='16:00', hora_llegada='17:30', precio_economy='90000.00', destino='COR',
            fecha_operacion=str(MANANA + dt.timedelta(days=7)),
        )
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(set(d), VUELO_CAMPOS | {'avion'})
        self.assertEqual((d['id'], d['numero_vuelo']), (str(v.id), 'FA 1'))
        self.assertEqual((d['hora_partida'], d['hora_llegada'], d['precio_economy']), ('16:00:00', '17:30:00', '90000.00'))
        self.assertEqual(d['destino']['codigo_iata'], 'COR')
        self.assertEqual(d['fecha_operacion'], d['fecha_llegada'])
        v.refresh_from_db()
        self.assertEqual(v.fecha_operacion, MANANA + dt.timedelta(days=7))
        otra.refresh_from_db()
        self.assertEqual((otra.hora_partida, otra.precio_economy), (dt.time(15), Decimal('100000.00')))
        self.assertEqual(otra.aeropuerto_destino, self.aep)

    def test_cruza_medianoche(self):
        v = self.vuelo()
        self.assertEqual(self.editar(v, hora_partida='23:30', hora_llegada='00:40').status_code, 200)
        v.refresh_from_db()
        self.assertEqual(v.fecha_llegada, v.fecha_operacion + dt.timedelta(days=1))

    def test_cambio_de_avion_recalcula_asientos(self):
        v = self.vuelo(asientos_disponibles_economy=140, asientos_disponibles_primera=10)  # vendidos: 10 y 2
        self.assertEqual(self.editar(v, avion=str(self.avion2.id)).status_code, 200)
        v.refresh_from_db()
        self.assertEqual((v.avion, v.asientos_disponibles_economy, v.asientos_disponibles_primera), (self.avion2, 86, 6))

    def test_cambio_de_avion_sin_lugar_para_lo_vendido(self):
        v = self.vuelo('FA 2')  # disponibles 30 y 5 sobre 150 y 12: vendidos 120 y 7; el otro avión tiene 96 y 8
        self.assertEqual(
            self.rechaza(v, avion=str(self.avion2.id)),
            {'avion': ['Ese avión no tiene lugar para los pasajes ya vendidos.']},
        )

    def test_cuerpo_vacio_y_campos_no_editables(self):
        v = self.vuelo()
        self.assertEqual(self.editar(v).status_code, 200)
        r = self.editar(v, numero_vuelo='FA 9', estado='cancelado', asientos_disponibles_economy=1, fecha_llegada='2030-01-01')
        self.assertEqual(r.status_code, 200)
        v.refresh_from_db()
        self.assertEqual((v.numero_vuelo, v.estado, v.asientos_disponibles_economy), ('FA 1000', 'activo', 30))
        self.assertEqual(v.fecha_llegada, v.fecha_operacion)

    def test_validaciones(self):
        v = self.vuelo('FA 1', fecha=MANANA)
        self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1))
        self.assertEqual(self.rechaza(v, destino='BHI'), {'destino': ['El destino tiene que ser distinto del origen.']})
        self.assertEqual(
            self.rechaza(v, hora_llegada='15:00'),
            {'hora_llegada': ['La llegada no puede ser a la misma hora que la partida.']},
        )
        self.assertEqual(
            self.rechaza(v, fecha_operacion=str(HOY), hora_partida='11:00'),
            {'fecha_operacion': ['La partida tiene que ser en el futuro.']},
        )
        self.assertEqual(
            self.rechaza(v, fecha_operacion=str(HOY + dt.timedelta(days=366))),
            {'fecha_operacion': ['La fecha no puede pasar de un año desde hoy.']},
        )
        self.assertEqual(
            self.rechaza(v, fecha_operacion=str(MANANA + dt.timedelta(days=1))),
            {'fecha_operacion': ['El FA 1 ya tiene un vuelo ese día.']},
        )
        self.assertIn('precio_economy', self.rechaza(v, precio_economy='0'))
        self.assertIn('avion', self.rechaza(v, avion='no-es-un-uuid'))
        self.assertIn('origen', self.rechaza(v, origen='ZZZ'))

    def test_avion_ocupado_por_otro_vuelo(self):
        v = self.vuelo('FA 1', fecha=MANANA, partida='15:00')
        self.vuelo('FA 2', fecha=MANANA, partida='18:00')
        self.assertEqual(
            self.rechaza(v, hora_partida='17:30', hora_llegada='18:30'),
            {'non_field_errors': ['LV-FAA ya está asignado al FA 2 el 2026-10-21 de 18:00 a 19:00.']},
        )
        self.assertEqual(self.editar(v, hora_partida='15:30', hora_llegada='16:30').status_code, 200, 'no choca consigo mismo')

    def test_un_choque_previo_no_impide_editar_otros_datos(self):
        # Los vuelos de ejemplo no validaron avión libre: pueden estar pisados desde antes.
        v = self.vuelo('FA 1', fecha=MANANA, partida='15:00')
        self.vuelo('FA 2', fecha=MANANA, partida='15:30')
        self.assertEqual(self.editar(v).status_code, 200)
        sin_cambios = dict(fecha_operacion=str(MANANA), hora_partida='15:00', hora_llegada='16:00', avion=str(self.avion.id))
        self.assertEqual(self.editar(v, precio_economy='90000.00', **sin_cambios).status_code, 200, 'el formulario manda todo')
        self.assertIn('non_field_errors', self.rechaza(v, hora_llegada='16:10'), 'si cambia el horario, se valida')

    def test_no_edita_cancelados_ni_los_que_ya_salieron(self):
        cancelado = self.vuelo('FA 1', estado=Vuelo.Estado.CANCELADO)
        salio = self.vuelo('FA 2', fecha=HOY, partida='11:00')
        self.assertEqual(self.rechaza(cancelado, precio_economy='1.00'), {'non_field_errors': ['El vuelo ya está cancelado.']})
        self.assertEqual(self.rechaza(salio, precio_economy='1.00'), {'non_field_errors': ['El vuelo ya salió.']})

    def test_404(self):
        for id_ in (uuid.uuid4(), 'no-es-un-uuid'):
            self.assertEqual(self.client.patch(f'/api/vuelos/{id_}/', {}, format='json').status_code, 404, id_)


class CancelacionTests(AdminDatos):
    def cancelar(self, id_):
        return self.client.post(f'/api/vuelos/{id_}/cancelar/')

    def test_solo_el_administrador(self):
        self.solo_admin('post', f'/api/vuelos/{self.vuelo().id}/cancelar/')

    def test_cancela_solo_esa_instancia_y_conserva_la_fila(self):
        v = self.vuelo('FA 1', fecha=MANANA)
        otra = self.vuelo('FA 1', fecha=MANANA + dt.timedelta(days=1))
        r = self.cancelar(v.id)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((r.json()['id'], r.json()['estado']), (str(v.id), 'cancelado'))
        v.refresh_from_db()
        otra.refresh_from_db()
        self.assertEqual((v.estado, otra.estado), ('cancelado', 'activo'))
        self.assertEqual(Vuelo.objects.count(), 2, 'no se borra nada')
        self.assertEqual((v.precio_economy, v.asientos_disponibles_economy), (Decimal('100000.00'), 30))
        buscar = lambda fecha: self.client.get('/api/vuelos/buscar/', {'origen': 'BHI', 'desde': str(fecha)}).json()
        self.assertEqual(buscar(MANANA), [], 'el cancelado no se ofrece')
        self.assertEqual(len(buscar(MANANA + dt.timedelta(days=1))), 1)
        self.assertEqual(self.client.get(f'/api/vuelos/{v.id}/').json()['estado'], 'cancelado')

    def test_no_cancela_cancelados_ni_los_que_ya_salieron(self):
        cancelado = self.vuelo('FA 1', estado=Vuelo.Estado.CANCELADO)
        salio = self.vuelo('FA 2', fecha=HOY, partida='11:00')
        r = self.cancelar(cancelado.id)
        self.assertEqual((r.status_code, r.json()), (400, {'non_field_errors': ['El vuelo ya está cancelado.']}))
        r = self.cancelar(salio.id)
        self.assertEqual((r.status_code, r.json()), (400, {'non_field_errors': ['El vuelo ya salió.']}))
        salio.refresh_from_db()
        self.assertEqual(salio.estado, 'activo')

    def test_404(self):
        for id_ in (uuid.uuid4(), 'no-es-un-uuid'):
            self.assertEqual(self.cancelar(id_).status_code, 404, id_)



class MostradorEstadoVueloTests(AdminDatos):
    """US14: consulta operativa del estado de un vuelo desde mostrador."""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.empleado)
        factura = patch('pagos.factura.enviar_factura_confirmada')
        factura.start()
        self.addCleanup(factura.stop)

    def buscar_mostrador(self, **params):
        r = self.client.get('/api/mostrador/vuelos/', params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()['results']

    def consultar_estado(self, id_):
        return self.client.get(f'/api/mostrador/vuelos/{id_}/')

    def confirmar_venta(self, vuelo, clase='economy', cantidad=1):
        from pagos import servicios as pagos
        from pagos.models import Pago

        reserva = Reserva.objects.create(
            pasajero=self.pasajero, contacto_email='pepe@mail.com', vuelo=vuelo, cantidad_pasajes=cantidad
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=f'{reserva.id.hex[:8]}-{i:02d}', nombre_pasajero='Pepe',
                apellido_pasajero='Pérez', dni_pasajero='12345678', clase=clase, precio=Decimal('100000.00'),
            )
        pago = Pago.objects.create(reserva_id=reserva.id, monto=Decimal('100000.00') * cantidad, metodo_pago=Pago.Metodo.TARJETA)
        pagos.confirmar_compra(pago, 'Pago aprobado.')

    def test_empleado_busca_y_selecciona_vuelo(self):
        v1 = self.vuelo('FA 1010', fecha=MANANA, origen=self.bhi, destino=self.aep)
        v2 = self.vuelo('FA 2020', fecha=MANANA, origen=self.cor, destino=self.aep, estado=Vuelo.Estado.CANCELADO)
        pasado = self.vuelo('FA 3030', fecha=HOY - dt.timedelta(days=2))

        self.assertEqual([v['id'] for v in self.buscar_mostrador()], [str(v1.id), str(v2.id)])
        self.assertEqual([v['id'] for v in self.buscar_mostrador(q='1010')], [str(v1.id)])
        self.assertEqual([v['id'] for v in self.buscar_mostrador(q=str(pasado.id))], [str(pasado.id)])
        self.assertEqual([v['id'] for v in self.buscar_mostrador(origen='cor')], [str(v2.id)])
        self.assertEqual([v['id'] for v in self.buscar_mostrador(estado='cancelado')], [str(v2.id)])

    def test_consulta_identificador_ruta_horarios_estado_ocupacion_y_disponibilidad_por_clase(self):
        v = self.vuelo(
            'FA 1010', fecha=MANANA, origen=self.bhi, destino=self.aep, partida='15:00',
            asientos_disponibles_economy=150, asientos_disponibles_primera=12,
        )
        self.confirmar_venta(v, 'economy', 3)
        self.confirmar_venta(v, 'primera', 1)

        r = self.consultar_estado(v.id)
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        vuelo = d['vuelo']
        self.assertEqual(vuelo['id'], str(v.id))
        self.assertEqual(vuelo['numero_vuelo'], 'FA 1010')
        self.assertEqual((vuelo['origen']['codigo_iata'], vuelo['destino']['codigo_iata']), ('BHI', 'AEP'))
        self.assertEqual((vuelo['fecha_operacion'], vuelo['fecha_llegada']), (str(MANANA), str(MANANA)))
        self.assertEqual((vuelo['hora_partida'], vuelo['hora_llegada']), ('15:00:00', '16:00:00'))
        self.assertEqual(vuelo['estado'], 'activo')
        self.assertEqual((vuelo['asientos_disponibles_economy'], vuelo['asientos_disponibles_primera']), (147, 11))
        self.assertEqual(d['clases'], [
            {'clase': 'economy', 'capacidad': 150, 'vendidos': 3, 'disponibles': 147},
            {'clase': 'primera', 'capacidad': 12, 'vendidos': 1, 'disponibles': 11},
        ])
        self.assertEqual(d['total'], {'capacidad': 162, 'vendidos': 4, 'disponibles': 158})

    def test_informacion_actualizada_ante_ventas_y_cambios_de_estado(self):
        v = self.vuelo(
            'FA 1010', fecha=MANANA, asientos_disponibles_economy=150, asientos_disponibles_primera=12
        )
        inicial = self.consultar_estado(v.id).json()
        self.assertEqual(inicial['total'], {'capacidad': 162, 'vendidos': 0, 'disponibles': 162})

        self.confirmar_venta(v, 'economy', 2)
        tras_venta = self.consultar_estado(v.id).json()
        self.assertEqual(tras_venta['total'], {'capacidad': 162, 'vendidos': 2, 'disponibles': 160})
        self.assertEqual(tras_venta['vuelo']['asientos_disponibles_economy'], 148)

        self.client.force_authenticate(self.admin)
        self.client.post(f'/api/vuelos/{v.id}/cancelar/')
        self.client.force_authenticate(self.empleado)
        tras_cancelar = self.consultar_estado(v.id).json()
        self.assertEqual(tras_cancelar['vuelo']['estado'], 'cancelado')

    def test_empleado_no_puede_crear_modificar_ni_cancelar_vuelos(self):
        v = self.vuelo('FA 1010', fecha=MANANA)
        self.assertEqual(self.client.post('/api/vuelos/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/vuelos/{v.id}/', {'precio_economy': '1.00'}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'/api/vuelos/{v.id}/cancelar/').status_code, 403)
        self.assertEqual(self.client.post('/api/mostrador/vuelos/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(f'/api/mostrador/vuelos/{v.id}/', {}, format='json').status_code, 405)
        v.refresh_from_db()
        self.assertEqual((v.estado, v.precio_economy), (Vuelo.Estado.ACTIVO, Decimal('100000.00')))

    def test_pasajero_y_anonimo_no_acceden_a_mostrador(self):
        v = self.vuelo('FA 1010', fecha=MANANA)
        for url in ('/api/mostrador/vuelos/', f'/api/mostrador/vuelos/{v.id}/'):
            self.client.force_authenticate(None)
            self.assertEqual(self.client.get(url).status_code, 401, url)
            self.client.force_authenticate(self.pasajero)
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_404_en_instancia_inexistente_o_id_invalido(self):
        for id_ in (uuid.uuid4(), 'no-es-un-uuid'):
            r = self.consultar_estado(id_)
            self.assertEqual(r.status_code, 404, id_)
            self.assertIn('detail', r.json())


class NotificacionCambioHorarioTests(AdminDatos):
    """US15: Notificar modificaciones de horario a pasajeros con compra confirmada."""

    def reserva(self, vuelo, pasajero=None, email=None, estado=Reserva.Estado.PAGADA, cantidad=1):
        pasajero = pasajero or self.pasajero
        reserva = Reserva.objects.create(
            pasajero=pasajero,
            contacto_email=email if email is not None else pasajero.email,
            vuelo=vuelo,
            cantidad_pasajes=cantidad,
            estado=estado,
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva,
                codigo_pasaje=f'{reserva.id.hex[:8]}-{i:02d}',
                nombre_pasajero=pasajero.nombre,
                apellido_pasajero=pasajero.apellido,
                dni_pasajero='12345678',
                clase=Pasaje.Clase.ECONOMY,
                precio=Decimal('100000.00'),
            )
        return reserva

    def modificar(self, vuelo, **datos):
        with (
            self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'),
            self.captureOnCommitCallbacks(execute=True),
        ):
            return self.client.patch(f'/api/vuelos/{vuelo.id}/', datos, format='json')

    def test_modifica_horario_notifica_pasajeros_con_compra_confirmada(self):
        from django.core import mail

        from .models import Notificacion

        otro = get_user_model().objects.create_user(
            'ana@mail.com', 'x', nombre='Ana', apellido='García', rol='pasajero'
        )
        v = self.vuelo('FA 1010', fecha=MANANA, origen=self.bhi, destino=self.aep, partida='15:00')
        self.reserva(v, pasajero=self.pasajero, email='pepe.contacto@mail.com')
        self.reserva(v, pasajero=otro, email='ana@mail.com')

        r = self.modificar(v, hora_partida='17:30', hora_llegada='18:45')
        self.assertEqual(r.status_code, 200, r.content)

        self.assertEqual(len(mail.outbox), 2)
        destinatarios = {m.to[0]: m for m in mail.outbox}
        self.assertEqual(set(destinatarios), {'pepe.contacto@mail.com', 'ana@mail.com'})

        correo = destinatarios['pepe.contacto@mail.com']
        self.assertIn('FA 1010', correo.subject)
        for dato in (
            'FA 1010',
            str(v.id),
            'BHI',
            'Bahía Blanca',
            'AEP',
            'Buenos Aires',
            '15:00',
            '16:00',
            '17:30',
            '18:45',
            '21/10/2026',
        ):
            self.assertIn(dato, correo.body)
            self.assertIn(dato, correo.alternatives[0][0])

        notificaciones = list(Notificacion.objects.filter(vuelo=v).order_by('usuario__email'))
        self.assertEqual(len(notificaciones), 2)
        self.assertTrue(all(n.enviado and n.tipo == Notificacion.Tipo.CAMBIO_HORARIO for n in notificaciones))
        self.assertIn('15:00', notificaciones[0].mensaje)
        self.assertIn('17:30', notificaciones[0].mensaje)

    def test_no_notifica_otras_instancias_de_la_misma_recurrencia(self):
        from django.core import mail

        from .models import Notificacion

        otro = get_user_model().objects.create_user(
            'otro@mail.com', 'x', nombre='Luis', apellido='L', rol='pasajero'
        )
        v_modificado = self.vuelo('FA 1000', fecha=MANANA, partida='15:00')
        v_otra_fecha = self.vuelo('FA 1000', fecha=MANANA + dt.timedelta(days=2), partida='15:00')
        self.reserva(v_modificado, pasajero=self.pasajero, email='pepe@mail.com')
        self.reserva(v_otra_fecha, pasajero=otro, email='otro@mail.com')

        r = self.modificar(v_modificado, hora_partida='16:30', hora_llegada='17:30')
        self.assertEqual(r.status_code, 200, r.content)

        self.assertEqual([m.to for m in mail.outbox], [['pepe@mail.com']])
        self.assertEqual(
            list(Notificacion.objects.values_list('usuario_id', 'vuelo_id')),
            [(self.pasajero.id, v_modificado.id)],
        )

    def test_no_notifica_compras_no_confirmadas(self):
        from django.core import mail

        from .models import Notificacion

        pendiente = get_user_model().objects.create_user(
            'pendiente@mail.com', 'x', nombre='Pau', apellido='P', rol='pasajero'
        )
        cancelado = get_user_model().objects.create_user(
            'cancelado@mail.com', 'x', nombre='Caro', apellido='C', rol='pasajero'
        )
        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=pendiente, estado=Reserva.Estado.PENDIENTE)
        self.reserva(v, pasajero=cancelado, estado=Reserva.Estado.CANCELADA)

        r = self.modificar(v, hora_partida='18:00', hora_llegada='19:00')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Notificacion.objects.count(), 0)

    def test_no_duplica_notificaciones_en_una_misma_operacion_ni_sin_cambio_horario(self):
        from django.core import mail

        from .models import Notificacion
        from .notificaciones import enviar_notificacion_cambio_horario, snapshot_horario

        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com', cantidad=3)
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com', cantidad=2)

        # Editar solo precio (sin cambiar horario) o enviar el mismo horario no dispara notificaciones.
        r1 = self.modificar(v, precio_economy='120000.00', hora_partida='15:00', hora_llegada='16:00')
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Notificacion.objects.count(), 0)

        # Una operación que modifica el horario envía exactamente 1 notificación por pasajero afectado.
        anterior = snapshot_horario(v)
        r2 = self.modificar(v, hora_partida='16:15', hora_llegada='17:15')
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

        # Un reintento idempotente sobre la notificación ya enviada no reenvía el correo.
        notificacion = Notificacion.objects.get()
        v.refresh_from_db()
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            enviar_notificacion_cambio_horario(
                notificacion.id, 'pepe@mail.com', 'Pepe P', anterior, ['ABC-00']
            )
        self.assertEqual(len(mail.outbox), 1)

    def test_error_en_envio_de_correo_no_revierte_modificacion_del_vuelo(self):
        from smtplib import SMTPException

        from .models import Notificacion

        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com')

        with (
            patch('vuelos.notificaciones.EmailMultiAlternatives.send', side_effect=SMTPException('SMTP caído')),
            self.assertLogs('vuelos.notificaciones', level='ERROR'),
        ):
            r = self.modificar(v, hora_partida='19:00', hora_llegada='20:00')

        self.assertEqual(r.status_code, 200, r.content)
        v.refresh_from_db()
        self.assertEqual((v.hora_partida, v.hora_llegada), (dt.time(19, 0), dt.time(20, 0)))
        notificacion = Notificacion.objects.get(vuelo=v, usuario=self.pasajero)
        self.assertFalse(notificacion.enviado)


class NotificacionCancelacionTests(AdminDatos):
    """US16: Notificar cancelaciones de vuelo a pasajeros con compra confirmada."""

    def reserva(self, vuelo, pasajero=None, email=None, estado=Reserva.Estado.PAGADA, cantidad=1):
        pasajero = pasajero or self.pasajero
        reserva = Reserva.objects.create(
            pasajero=pasajero,
            contacto_email=email if email is not None else pasajero.email,
            vuelo=vuelo,
            cantidad_pasajes=cantidad,
            estado=estado,
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva,
                codigo_pasaje=f'{reserva.id.hex[:8]}-{i:02d}',
                nombre_pasajero=pasajero.nombre,
                apellido_pasajero=pasajero.apellido,
                dni_pasajero='12345678',
                clase=Pasaje.Clase.ECONOMY,
                precio=Decimal('100000.00'),
            )
        return reserva

    def cancelar(self, vuelo):
        with (
            self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'),
            self.captureOnCommitCallbacks(execute=True),
        ):
            return self.client.post(f'/api/vuelos/{vuelo.id}/cancelar/')

    def test_cancela_vuelo_notifica_pasajeros_con_compra_confirmada(self):
        from django.core import mail

        from .models import Notificacion

        otro = get_user_model().objects.create_user(
            'ana@mail.com', 'x', nombre='Ana', apellido='García', rol='pasajero'
        )
        v = self.vuelo('FA 1010', fecha=MANANA, origen=self.bhi, destino=self.aep, partida='15:00')
        r_pepe = self.reserva(v, pasajero=self.pasajero, email='pepe.contacto@mail.com')
        self.reserva(v, pasajero=otro, email='ana@mail.com')

        r = self.cancelar(v)
        self.assertEqual(r.status_code, 200, r.content)
        v.refresh_from_db()
        self.assertEqual(v.estado, Vuelo.Estado.CANCELADO)

        self.assertEqual(len(mail.outbox), 2)
        destinatarios = {m.to[0]: m for m in mail.outbox}
        self.assertEqual(set(destinatarios), {'pepe.contacto@mail.com', 'ana@mail.com'})

        correo = destinatarios['pepe.contacto@mail.com']
        self.assertIn('Cancelación de vuelo', correo.subject)
        self.assertIn('FA 1010', correo.subject)
        for dato in (
            'FA 1010',
            str(v.id),
            'BHI',
            'Bahía Blanca',
            'AEP',
            'Buenos Aires',
            '21/10/2026',
            '15:00',
            '16:00',
            f'{r_pepe.id.hex[:8]}-00',
        ):
            self.assertIn(dato, correo.body)
            self.assertIn(dato, correo.alternatives[0][0])

        notificaciones = list(Notificacion.objects.filter(vuelo=v).order_by('usuario__email'))
        self.assertEqual(len(notificaciones), 2)
        self.assertTrue(all(n.enviado and n.tipo == Notificacion.Tipo.CANCELACION for n in notificaciones))
        self.assertIn('FA 1010', notificaciones[0].mensaje)
        self.assertIn('cancelado', notificaciones[0].mensaje)

    def test_no_notifica_otras_instancias_de_la_misma_recurrencia(self):
        from django.core import mail

        from .models import Notificacion

        otro = get_user_model().objects.create_user(
            'otro@mail.com', 'x', nombre='Luis', apellido='L', rol='pasajero'
        )
        v_cancelado = self.vuelo('FA 1000', fecha=MANANA, partida='15:00')
        v_otra_fecha = self.vuelo('FA 1000', fecha=MANANA + dt.timedelta(days=2), partida='15:00')
        self.reserva(v_cancelado, pasajero=self.pasajero, email='pepe@mail.com')
        self.reserva(v_otra_fecha, pasajero=otro, email='otro@mail.com')

        r = self.cancelar(v_cancelado)
        self.assertEqual(r.status_code, 200, r.content)

        self.assertEqual([m.to for m in mail.outbox], [['pepe@mail.com']])
        self.assertEqual(
            list(Notificacion.objects.values_list('usuario_id', 'vuelo_id')),
            [(self.pasajero.id, v_cancelado.id)],
        )
        v_otra_fecha.refresh_from_db()
        self.assertEqual(v_otra_fecha.estado, Vuelo.Estado.ACTIVO)

    def test_no_notifica_compras_no_confirmadas(self):
        from django.core import mail

        from .models import Notificacion

        pendiente = get_user_model().objects.create_user(
            'pendiente@mail.com', 'x', nombre='Pau', apellido='P', rol='pasajero'
        )
        cancelado = get_user_model().objects.create_user(
            'cancelado@mail.com', 'x', nombre='Caro', apellido='C', rol='pasajero'
        )
        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=pendiente, estado=Reserva.Estado.PENDIENTE)
        self.reserva(v, pasajero=cancelado, estado=Reserva.Estado.CANCELADA)

        r = self.cancelar(v)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Notificacion.objects.count(), 0)

    def test_no_duplica_notificaciones_para_un_mismo_pasajero(self):
        from django.core import mail

        from .models import Notificacion
        from .notificaciones import enviar_notificacion_cancelacion, programar_notificaciones_cancelacion

        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com', cantidad=3)
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com', cantidad=2)

        r1 = self.cancelar(v)
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

        # Intentar cancelar de nuevo devuelve 400 y no genera otra notificación.
        r2 = self.cancelar(v)
        self.assertEqual(r2.status_code, 400)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

        # Incluso si se invoca directamente otra vez, no duplica filas ni reenvía el correo.
        notificacion = Notificacion.objects.get()
        with (
            self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'),
            self.captureOnCommitCallbacks(execute=True),
        ):
            self.assertEqual(programar_notificaciones_cancelacion(v), [])
            enviar_notificacion_cancelacion(notificacion.id, 'pepe@mail.com', 'Pepe P', ['ABC-00'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notificacion.objects.count(), 1)

    def test_error_en_envio_de_correo_no_altera_el_vuelo_cancelado(self):
        from smtplib import SMTPException

        from .models import Notificacion

        v = self.vuelo('FA 1010', fecha=MANANA, partida='15:00')
        self.reserva(v, pasajero=self.pasajero, email='pepe@mail.com')
        antes = (v.numero_vuelo, v.fecha_operacion, v.hora_partida, v.hora_llegada, v.asientos_disponibles_economy)

        with (
            patch('vuelos.notificaciones.EmailMultiAlternatives.send', side_effect=SMTPException('SMTP caído')),
            self.assertLogs('vuelos.notificaciones', level='ERROR'),
        ):
            r = self.cancelar(v)

        self.assertEqual(r.status_code, 200, r.content)
        v.refresh_from_db()
        self.assertEqual(v.estado, Vuelo.Estado.CANCELADO)
        self.assertEqual(
            (v.numero_vuelo, v.fecha_operacion, v.hora_partida, v.hora_llegada, v.asientos_disponibles_economy),
            antes,
        )
        notificacion = Notificacion.objects.get(vuelo=v, usuario=self.pasajero)
        self.assertFalse(notificacion.enviado)
        self.assertEqual(notificacion.tipo, Notificacion.Tipo.CANCELACION)
