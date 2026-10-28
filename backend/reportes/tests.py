import datetime as dt
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from pagos import servicios as pagos
from pagos.models import Pago
from reservas.models import Pasaje, Reserva
from vuelos.models import Aeropuerto, Avion, Vuelo

Usuario = get_user_model()


class Datos(APITestCase):
    """Avión 150/12 y vuelos AEP → COR en los próximos días; el admin consulta."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_superuser('admin@mail.com', 'x', nombre='Ada', apellido='Admin')
        cls.pasajero = Usuario.objects.create_user('ana@mail.com', 'x', nombre='Ana', apellido='Pérez')
        cls.empleado = Usuario.objects.create_user(
            'eva@mail.com', 'x', nombre='Eva', apellido='Empleada', rol=Usuario.Rol.EMPLEADO_MOSTRADOR
        )
        cls.aep = Aeropuerto.objects.create(codigo_iata='AEP', nombre='Aeroparque', ciudad='Buenos Aires', pais='Argentina')
        cls.cor = Aeropuerto.objects.create(codigo_iata='COR', nombre='Pajas Blancas', ciudad='Córdoba', pais='Argentina')
        cls.avion = Avion.objects.create(matricula='LV-FAA', modelo='Airbus A320', capacidad_economy=150, capacidad_primera=12)
        cls.vuelo = cls.crear_vuelo('FA 5000', dias=5)

    @classmethod
    def crear_vuelo(cls, numero, dias, **cambios):
        fecha = timezone.localdate() + dt.timedelta(days=dias)
        datos = dict(
            numero_vuelo=numero, avion=cls.avion, aeropuerto_origen=cls.aep, aeropuerto_destino=cls.cor,
            fecha_operacion=fecha, fecha_llegada=fecha, hora_partida=dt.time(15, 0), hora_llegada=dt.time(16, 30),
            precio_economy=Decimal('100000.00'), precio_primera=Decimal('250000.00'),
            asientos_disponibles_economy=150, asientos_disponibles_primera=12, creado_por=cls.admin,
        )
        datos.update(cambios)
        return Vuelo.objects.create(**datos)

    def setUp(self):
        self.client.force_authenticate(self.admin)
        factura = patch('pagos.factura.enviar_factura_confirmada')
        factura.start()
        self.addCleanup(factura.stop)

    def reserva(self, vuelo, clase='economy', cantidad=1):
        reserva = Reserva.objects.create(
            pasajero=self.pasajero, contacto_email='ana@mail.com', vuelo=vuelo, cantidad_pasajes=cantidad
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=f'{reserva.id.hex[:8]}-{i}', nombre_pasajero='Ana',
                apellido_pasajero='Pérez', dni_pasajero='12345678', clase=clase, precio=Decimal('1.00'),
            )
        return reserva

    def confirmar(self, reserva):
        """Compra confirmada por el camino real (US08): descuenta asientos y marca la reserva pagada."""
        pago = Pago.objects.create(reserva_id=reserva.id, monto=Decimal('1.00'), metodo_pago=Pago.Metodo.TARJETA)
        pago = pagos.confirmar_compra(pago, 'Pago aprobado.')
        self.assertEqual(pago.estado, 'aprobado')
        return reserva

    def ocupacion(self, vuelo):
        return self.client.get(f'/api/reportes/ocupacion/{vuelo.id}/')

    def por_clase(self, datos):
        return {c['clase']: (c['capacidad'], c['vendidos'], c['disponibles']) for c in datos['clases']}


class OcupacionVueloTests(Datos):
    def test_vuelo_sin_ventas(self):
        r = self.ocupacion(self.vuelo)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['vuelo']['id'], str(self.vuelo.id))
        self.assertEqual([c['clase'] for c in r.data['clases']], ['economy', 'primera'])
        self.assertEqual(self.por_clase(r.data), {'economy': (150, 0, 150), 'primera': (12, 0, 12)})
        self.assertEqual(r.data['total'], {'capacidad': 162, 'vendidos': 0, 'disponibles': 162})

    def test_solo_cuentan_compras_confirmadas(self):
        self.confirmar(self.reserva(self.vuelo, 'economy', 2))
        self.confirmar(self.reserva(self.vuelo, 'primera', 1))
        self.reserva(self.vuelo, 'economy', 3)  # pendiente
        rechazada = self.reserva(self.vuelo, 'economy', 1)
        Pago.objects.create(
            reserva_id=rechazada.id, monto=Decimal('1.00'), metodo_pago=Pago.Metodo.TARJETA, estado=Pago.Estado.RECHAZADO
        )

        r = self.ocupacion(self.vuelo)
        self.assertEqual(self.por_clase(r.data), {'economy': (150, 2, 148), 'primera': (12, 1, 11)})
        self.assertEqual(r.data['total'], {'capacidad': 162, 'vendidos': 3, 'disponibles': 159})

    def test_suma_consistente_tras_compras_reales(self):
        for clase, cantidad in (('economy', 9), ('primera', 2), ('economy', 4), ('primera', 1)):
            self.confirmar(self.reserva(self.vuelo, clase, cantidad))
        r = self.ocupacion(self.vuelo)
        for capacidad, vendidos, disponibles in self.por_clase(r.data).values():
            self.assertEqual(vendidos + disponibles, capacidad)
        self.assertEqual(self.por_clase(r.data), {'economy': (150, 13, 137), 'primera': (12, 3, 9)})

    def test_no_mezcla_otra_instancia_del_mismo_numero(self):
        otro_dia = self.crear_vuelo('FA 5000', dias=6)
        self.confirmar(self.reserva(otro_dia, 'economy', 4))
        self.assertEqual(self.por_clase(self.ocupacion(self.vuelo).data)['economy'], (150, 0, 150))
        self.assertEqual(self.por_clase(self.ocupacion(otro_dia).data)['economy'], (150, 4, 146))

    def test_vuelo_cancelado_se_consulta(self):
        cancelado = self.crear_vuelo('FA 5001', dias=7, estado=Vuelo.Estado.CANCELADO)
        r = self.ocupacion(cancelado)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['vuelo']['estado'], 'cancelado')

    def test_permisos(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.ocupacion(self.vuelo).status_code, 401)
        for usuario in (self.pasajero, self.empleado):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.ocupacion(self.vuelo).status_code, 403, usuario.rol)

    def test_404(self):
        self.assertEqual(self.client.get('/api/reportes/ocupacion/00000000-0000-0000-0000-000000000000/').status_code, 404)
        r = self.client.get('/api/reportes/ocupacion/abc/')
        self.assertEqual(r.status_code, 404)
        self.assertIn('detail', r.data)


class ReporteTests(Datos):
    """US13: GET /api/reportes/ocupacion/ con filtros por vuelo, fecha y clase."""

    def get(self, **params):
        return self.client.get('/api/reportes/ocupacion/', params)

    def fecha(self, dias):
        return (timezone.localdate() + dt.timedelta(days=dias)).isoformat()

    def test_sin_criterios_400(self):
        for params in ({}, {'vuelo': '', 'desde': ''}, {'clase': 'primera'}):
            r = self.get(**params)
            self.assertEqual(r.status_code, 400, params)
            self.assertEqual(r.data['non_field_errors'], ['Elegí un vuelo o un rango de fechas.'])

    def test_hasta_antes_de_desde_400(self):
        r = self.get(desde=self.fecha(5), hasta=self.fecha(4))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['hasta'], ['La fecha hasta no puede ser anterior a desde.'])

    def test_fecha_y_clase_invalidas_400(self):
        r = self.get(desde='2026-13-01')
        self.assertEqual(r.status_code, 400)
        self.assertIn('desde', r.data)
        r = self.get(desde=self.fecha(1), clase='business')
        self.assertEqual(r.data['clase'], ['La clase debe ser economy o primera.'])

    def test_por_numero_trae_todas_sus_instancias(self):
        self.crear_vuelo('FA 5000', dias=6)
        self.crear_vuelo('FA 5000', dias=7)
        self.crear_vuelo('FA 5001', dias=6)
        r = self.get(vuelo='5000')
        self.assertEqual(r.data['count'], 3)
        self.assertEqual({f['vuelo']['numero_vuelo'] for f in r.data['results']}, {'FA 5000'})

    def test_por_id_trae_una(self):
        self.crear_vuelo('FA 5000', dias=6)
        r = self.get(vuelo=str(self.vuelo.id))
        self.assertEqual([f['vuelo']['id'] for f in r.data['results']], [str(self.vuelo.id)])

    def test_por_rango_de_fechas(self):
        for dias in (3, 4, 6, 8):
            self.crear_vuelo(f'FA 6{dias:03d}', dias=dias)
        r = self.get(desde=self.fecha(4), hasta=self.fecha(6))
        self.assertEqual([f['vuelo']['fecha_operacion'] for f in r.data['results']], [self.fecha(4), self.fecha(5), self.fecha(6)])
        r = self.get(hasta=self.fecha(4))  # solo "hasta" también es un criterio
        self.assertEqual([f['vuelo']['fecha_operacion'] for f in r.data['results']], [self.fecha(3), self.fecha(4)])

    def test_clase_filtra_columnas(self):
        self.confirmar(self.reserva(self.vuelo, 'primera', 2))
        r = self.get(vuelo='FA 5000', clase='primera')
        fila = r.data['results'][0]
        self.assertEqual(fila['clases'], [{'clase': 'primera', 'capacidad': 12, 'vendidos': 2, 'disponibles': 10}])
        self.assertEqual(fila['total'], {'capacidad': 12, 'vendidos': 2, 'disponibles': 10})
        self.assertEqual([c['clase'] for c in r.data['totales']['clases']], ['primera'])
        self.assertEqual(r.data['totales']['total'], {'capacidad': 12, 'vendidos': 2, 'disponibles': 10})

    def test_vuelo_sin_ventas_aparece_en_cero(self):
        r = self.get(vuelo='FA 5000')
        self.assertEqual(r.data['results'][0]['total'], {'capacidad': 162, 'vendidos': 0, 'disponibles': 162})

    def test_pendientes_y_rechazados_no_cuentan(self):
        self.confirmar(self.reserva(self.vuelo, 'economy', 2))
        self.reserva(self.vuelo, 'economy', 3)
        rechazada = self.reserva(self.vuelo, 'economy', 1)
        Pago.objects.create(
            reserva_id=rechazada.id, monto=Decimal('1.00'), metodo_pago=Pago.Metodo.TARJETA, estado=Pago.Estado.RECHAZADO
        )
        r = self.get(vuelo='FA 5000')
        self.assertEqual(r.data['results'][0]['total']['vendidos'], 2)
        self.assertEqual(r.data['totales']['total']['vendidos'], 2)

    def test_coincide_con_la_consulta_por_vuelo(self):
        otro = self.crear_vuelo('FA 5000', dias=6)
        self.confirmar(self.reserva(self.vuelo, 'economy', 3))
        self.confirmar(self.reserva(otro, 'primera', 1))
        for fila in self.get(vuelo='FA 5000').data['results']:
            detalle = self.client.get(f"/api/reportes/ocupacion/{fila['vuelo']['id']}/").data
            self.assertEqual((fila['clases'], fila['total']), (detalle['clases'], detalle['total']))

    def test_totales_suman_todas_las_paginas(self):
        vuelos = [self.crear_vuelo('FA 6000', dias=10 + n) for n in range(55)]
        self.confirmar(self.reserva(vuelos[0], 'economy', 1))
        self.confirmar(self.reserva(vuelos[-1], 'economy', 1))
        r = self.get(vuelo='FA 6000')
        self.assertEqual((r.data['count'], len(r.data['results'])), (55, 50))
        self.assertEqual(r.data['totales']['total'], {'capacidad': 55 * 162, 'vendidos': 2, 'disponibles': 55 * 162 - 2})
        self.assertEqual(len(self.get(vuelo='FA 6000', page=2).data['results']), 5)

    def test_sin_resultados(self):
        r = self.get(desde=self.fecha(100), hasta=self.fecha(101))
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.data['count'], r.data['results']), (0, []))
        self.assertEqual(r.data['totales']['total'], {'capacidad': 0, 'vendidos': 0, 'disponibles': 0})

    def test_incluye_cancelados_con_su_estado(self):
        self.crear_vuelo('FA 5000', dias=6, estado=Vuelo.Estado.CANCELADO)
        estados = [f['vuelo']['estado'] for f in self.get(vuelo='FA 5000').data['results']]
        self.assertEqual(estados, ['activo', 'cancelado'])

    def test_permisos(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.get(vuelo='FA 5000').status_code, 401)
        for usuario in (self.pasajero, self.empleado):
            self.client.force_authenticate(usuario)
            self.assertEqual(self.get(vuelo='FA 5000').status_code, 403, usuario.rol)
