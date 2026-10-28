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
