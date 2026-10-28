"""US11: compras realmente simultáneas, con un hilo (y una conexión) por operación.

Solo corren en Postgres: SQLite no bloquea filas, así que ahí no prueban nada y se saltean.
    DATABASE_URL=postgres://usuario@localhost:5432/postgres .venv/bin/python manage.py test pagos.tests_concurrencia
"""
import datetime as dt
import threading
import time
from decimal import Decimal
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from reservas.models import Pasaje, Reserva
from vuelos.models import Aeropuerto, Avion, Vuelo

from . import reservas_mock, servicios
from .models import Pago

Usuario = get_user_model()
APROBADA = '4242424242424242'


def a_la_vez(*funciones):
    """Corre cada función en su hilo, todas largando juntas. Devuelve el resultado o la excepción de cada una."""
    largada = threading.Barrier(len(funciones), timeout=10)
    resultados = [None] * len(funciones)

    def correr(i, funcion):
        try:
            largada.wait()
            resultados[i] = funcion()
        except Exception as error:  # se compara en el test
            resultados[i] = error
        finally:
            connection.close()  # cada hilo abre su conexión; si queda abierta, no se puede borrar la base de test

    hilos = [threading.Thread(target=correr, args=(i, f)) for i, f in enumerate(funciones)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
        assert not hilo.is_alive(), 'un hilo quedó colgado'
    return resultados


def demorar_seccion_critica():
    """Demora la lectura de los pasajes, que ocurre con el vuelo bloqueado: así las operaciones chocan siempre."""
    original = reservas_mock.pasajes_de

    def lento(reserva):
        time.sleep(0.2)
        return original(reserva)

    return patch('pagos.reservas_mock.pasajes_de', side_effect=lento)


@skipUnless(connection.vendor == 'postgresql', 'Necesita Postgres: SQLite no bloquea filas.')
class CompraConcurrenteTests(TransactionTestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser('admin@mail.com', 'x', nombre='Ada', apellido='Admin')
        aep = Aeropuerto.objects.create(codigo_iata='AEP', nombre='Aeroparque', ciudad='Buenos Aires', pais='Argentina')
        cor = Aeropuerto.objects.create(codigo_iata='COR', nombre='Pajas Blancas', ciudad='Córdoba', pais='Argentina')
        avion = Avion.objects.create(matricula='LV-FAA', modelo='Chico', capacidad_economy=10, capacidad_primera=2)
        fecha = timezone.localdate() + dt.timedelta(days=10)  # fecha real: el reloj no se parchea entre hilos
        self.vuelo = Vuelo.objects.create(
            numero_vuelo='FA 7000', avion=avion, aeropuerto_origen=aep, aeropuerto_destino=cor,
            fecha_operacion=fecha, fecha_llegada=fecha, hora_partida=dt.time(15, 0), hora_llegada=dt.time(16, 30),
            precio_economy=Decimal('100000.00'), precio_primera=Decimal('250000.00'),
            asientos_disponibles_economy=10, asientos_disponibles_primera=2, creado_por=self.admin,
        )
        factura = patch('pagos.factura.enviar_factura_confirmada')
        self.enviar_factura = factura.start()
        self.addCleanup(factura.stop)

    def reserva(self, n, cantidad=1):
        pasajero = Usuario.objects.create_user(f'pasajero{n}@mail.com', 'x', nombre='Pasajero', apellido=str(n))
        reserva = Reserva.objects.create(
            pasajero=pasajero, contacto_email=pasajero.email, vuelo=self.vuelo, cantidad_pasajes=cantidad
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=f'{reserva.id.hex[:8]}-{i}', nombre_pasajero='Pasajero',
                apellido_pasajero=str(n), dni_pasajero='12345678', clase='economy', precio=self.vuelo.precio_economy,
            )
        return reserva

    def pago_pendiente(self, reserva):
        return Pago.objects.create(
            reserva_id=reserva.id, monto=Decimal('100000.00'), metodo_pago=Pago.Metodo.MERCADOPAGO,
            estado=Pago.Estado.PENDIENTE,
        )

    def disponibles(self):
        self.vuelo.refresh_from_db()
        return self.vuelo.asientos_disponibles_economy

    def vendidos(self):
        return Pasaje.objects.filter(reserva__vuelo=self.vuelo, reserva__estado='pagada', clase='economy').count()

    def mensaje(self, error):
        self.assertIsInstance(error, ValidationError)
        return error.detail['non_field_errors'][0]

    def test_ultimo_lugar_dos_tarjetas_a_la_vez(self):
        Vuelo.objects.filter(id=self.vuelo.id).update(asientos_disponibles_economy=1)
        reservas = [self.reserva(1), self.reserva(2)]
        with demorar_seccion_critica():
            resultados = a_la_vez(*(lambda r=r: servicios.pagar_con_tarjeta(r, APROBADA) for r in reservas))

        aprobados = [r for r in resultados if isinstance(r, Pago)]
        errores = [r for r in resultados if not isinstance(r, Pago)]
        self.assertEqual([p.estado for p in aprobados], ['aprobado'])
        self.assertEqual([self.mensaje(e) for e in errores], [servicios.SIN_LUGAR_AL_PAGAR])
        self.assertEqual(self.disponibles(), 0)
        self.assertEqual(Reserva.objects.filter(estado='pagada').count(), 1)

    def test_ultimo_lugar_dos_aprobaciones_de_mp_a_la_vez(self):
        Vuelo.objects.filter(id=self.vuelo.id).update(asientos_disponibles_economy=1)
        pagos = [self.pago_pendiente(self.reserva(1)), self.pago_pendiente(self.reserva(2))]
        with demorar_seccion_critica():
            resultados = a_la_vez(*(lambda p=p: servicios.confirmar_compra(p, 'Pago aprobado.') for p in pagos))

        self.assertEqual(sorted(p.estado for p in resultados), ['aprobado', 'rechazado'])
        rechazado = next(p for p in resultados if p.estado == 'rechazado')
        self.assertEqual(rechazado.detalle, servicios.SIN_ASIENTOS)
        self.assertEqual(self.disponibles(), 0)

    def test_mismo_pago_confirmado_dos_veces_a_la_vez(self):
        pago = self.pago_pendiente(self.reserva(1, cantidad=2))
        with demorar_seccion_critica():
            a_la_vez(
                lambda: servicios.confirmar_compra(Pago.objects.get(id=pago.id), 'Pago aprobado.'),
                lambda: servicios.confirmar_compra(Pago.objects.get(id=pago.id), 'Pago aprobado.'),
            )

        pago.refresh_from_db()
        self.assertEqual(pago.estado, 'aprobado')
        self.assertTrue(pago.numero_factura)
        self.assertEqual(self.disponibles(), 8)
        self.assertEqual(Pago.objects.filter(estado='aprobado').count(), 1)
        self.assertEqual(self.enviar_factura.call_count, 1)

    def test_muchos_compradores_nunca_sobrevenden(self):
        reservas = [self.reserva(n, cantidad=n % 3 + 1) for n in range(20)]  # piden 39 lugares; hay 10
        resultados = a_la_vez(*(lambda r=r: servicios.pagar_con_tarjeta(r, APROBADA) for r in reservas))

        aprobados = [r for r in resultados if isinstance(r, Pago)]
        errores = [r for r in resultados if not isinstance(r, Pago)]
        self.assertTrue(all(p.estado == 'aprobado' for p in aprobados))
        self.assertEqual({self.mensaje(e) for e in errores}, {servicios.SIN_LUGAR_AL_PAGAR})
        self.assertLessEqual(self.vendidos(), 10)
        self.assertEqual(self.vendidos() + self.disponibles(), 10)
        self.assertEqual(Reserva.objects.filter(estado='pagada').count(), len(aprobados))
