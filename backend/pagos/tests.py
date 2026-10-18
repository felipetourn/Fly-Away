import datetime as dt
import http.client
import smtplib
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from anymail.exceptions import AnymailAPIError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from reservas.models import Pasaje, Reserva
from reservas.servicios import crear_reserva
from vuelos.models import Aeropuerto, Avion, Vuelo

from . import mercadopago, reservas_mock, servicios, tarjeta
from .models import Pago

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
        self.enterContext(self.settings(MP_ACCESS_TOKEN=''))
        self.client.force_authenticate(self.pasajero)

    def reserva(self, clase='economy', cantidad=1, vuelo=None, pasajero=None):
        vuelo = vuelo or self.vuelos[0]
        reserva = Reserva.objects.create(
            pasajero=pasajero or self.pasajero, contacto_email='ana@mail.com', vuelo=vuelo, cantidad_pasajes=cantidad
        )
        for i in range(cantidad):
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=f'{reserva.id.hex[:8]}-{i}', nombre_pasajero='Ana',
                apellido_pasajero='Pérez', dni_pasajero='12345678', clase=clase, precio=getattr(vuelo, f'precio_{clase}'),
            )
        return reserva

    def pago(self, reserva, estado=Pago.Estado.APROBADO, metodo=Pago.Metodo.TARJETA, **campos):
        return Pago.objects.create(reserva_id=reserva.id, monto=Decimal('100000.00'), estado=estado, metodo_pago=metodo, **campos)


class ModeloTests(Datos):
    def test_tabla_con_el_nombre_del_dbml(self):
        self.assertEqual(Pago._meta.db_table, 'pagos')

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


class ReservasTests(Datos):
    def test_reservas_de_devuelve_solo_las_propias_sin_inventar_ninguna(self):
        self.assertEqual(reservas_mock.reservas_de(self.pasajero), [])
        propia = self.reserva()
        self.reserva(pasajero=self.otro)
        self.assertEqual(reservas_mock.reservas_de(self.pasajero), [propia])

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


class EstadoReservaTests(Datos):
    def test_una_reserva_nueva_esta_pendiente_y_se_puede_marcar_pagada(self):
        reserva = self.reserva()
        self.assertEqual(reserva.estado, 'pendiente')
        reservas_mock.marcar_pagada(reserva)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pagada')

    def test_reserva_de_pago(self):
        reserva = self.reserva()
        self.assertEqual(reservas_mock.reserva_de_pago(self.pago(reserva)), reserva)


class TarjetaTests(Datos):
    def errores(self, numero='4242424242424242', titular='Ana Pérez', vencimiento='12/30', cvv='123'):
        return tarjeta.errores_de_tarjeta(tarjeta.limpiar_numero(numero), titular, vencimiento, cvv, HOY)

    def test_tarjetas_validas_de_las_tres_marcas(self):
        self.assertEqual(self.errores(), {})
        self.assertEqual(self.errores(numero='5031755734530604'), {})
        self.assertEqual(self.errores(numero='378282246310005', cvv='1234'), {})

    def test_acepta_espacios_y_guiones(self):
        self.assertEqual(self.errores(numero='4242 4242-4242 4242'), {})

    def test_numero_invalido(self):
        self.assertIn('numero', self.errores(numero='4242'))
        self.assertIn('numero', self.errores(numero='4242424242424241'))  # Luhn
        self.assertIn('numero', self.errores(numero='6011111111111117'))  # Discover: no soportada

    def test_titular_vencimiento_y_cvv(self):
        self.assertIn('titular', self.errores(titular='  '))
        self.assertIn('vencimiento', self.errores(vencimiento='13/30'))
        self.assertIn('vencimiento', self.errores(vencimiento='1230'))
        self.assertIn('vencimiento', self.errores(vencimiento='09/26'))  # HOY es octubre de 2026
        self.assertEqual(self.errores(vencimiento='10/26'), {})  # vence a fin de mes
        self.assertIn('cvv', self.errores(cvv='12'))
        self.assertIn('cvv', self.errores(numero='378282246310005', cvv='123'))  # Amex pide 4

    def test_resultado_segun_la_tarjeta_de_prueba(self):
        self.assertEqual(tarjeta.procesar('4242424242424242')[:2], (True, 'Pago aprobado.'))
        self.assertEqual(tarjeta.procesar('4000000000000002')[:2], (False, 'Tarjeta rechazada por el emisor.'))
        self.assertEqual(tarjeta.procesar('4000000000009995')[:2], (False, 'Fondos insuficientes.'))
        self.assertFalse(tarjeta.procesar('4000000000000119')[0])
        self.assertTrue(tarjeta.procesar('4242424242424242')[2].startswith('SIM-'))

    def test_cada_caso_tiene_su_mastercard(self):
        for visa, mastercard in (
            ('4242424242424242', '5555555555554444'),
            ('4000000000000002', '5200000000000007'),
            ('4000000000009995', '5200000000009990'),
            ('4000000000000119', '5200000000000114'),
        ):
            self.assertEqual(self.errores(numero=mastercard), {})
            self.assertEqual(tarjeta.procesar(mastercard)[:2], tarjeta.procesar(visa)[:2])


TARJETA_OK = {'numero': '4242 4242 4242 4242', 'titular': 'Ana Pérez', 'vencimiento': '12/30', 'cvv': '123'}


class PagoTarjetaTests(Datos):
    def pagar(self, reserva, **cambios):
        return self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK, **cambios}, format='json')

    def test_aprobado(self):
        reserva = self.reserva(clase='primera', cantidad=2)
        r = self.pagar(reserva)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['estado'], 'aprobado')
        self.assertEqual(r.data['monto'], '500000.00')
        self.assertEqual(r.data['ultimos_4'], '4242')
        self.assertEqual(r.data['vuelo']['numero_vuelo'], 'FA 1000')
        self.assertEqual(r.data['cantidad_pasajes'], 2)
        pago = Pago.objects.get(id=r.data['id'])
        self.assertEqual((pago.reserva_id, pago.metodo_pago), (reserva.id, 'tarjeta'))
        self.assertIsNotNone(pago.procesado_en)

    def test_guarda_la_marca(self):
        self.assertEqual(self.pagar(self.reserva()).data['marca'], 'visa')
        self.assertEqual(self.pagar(self.reserva(vuelo=self.vuelos[1]), numero='5031 7557 3453 0604').data['marca'], 'mastercard')

    def test_rechazado_queda_registrado_con_el_motivo(self):
        r = self.pagar(self.reserva(), numero='4000 0000 0000 9995')
        self.assertEqual(r.status_code, 201)
        self.assertEqual((r.data['estado'], r.data['detalle']), ('rechazado', 'Fondos insuficientes.'))

    def test_no_guarda_el_numero_completo_ni_el_cvv(self):
        self.pagar(self.reserva(), cvv='987')
        pago = Pago.objects.get()
        valores = ' '.join(str(getattr(pago, campo.attname)) for campo in Pago._meta.fields)
        self.assertNotIn('4242424242424242', valores)
        self.assertNotIn('987', valores)

    def test_datos_invalidos_400_por_campo(self):
        r = self.pagar(self.reserva(), numero='1234', cvv='', vencimiento='01/20')
        self.assertEqual(r.status_code, 400)
        self.assertIn('numero', r.data)
        self.assertIn('vencimiento', r.data)
        self.assertIn('cvv', r.data)
        self.assertFalse(Pago.objects.exists())

    def test_doble_envio_el_segundo_es_409(self):
        reserva = self.reserva()
        self.assertEqual(self.pagar(reserva).status_code, 201)
        r = self.pagar(reserva)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['detail'], 'La reserva ya está pagada.')
        self.assertEqual(Pago.objects.filter(estado='aprobado').count(), 1)

    def test_reintento_despues_de_un_rechazo(self):
        reserva = self.reserva()
        self.pagar(reserva, numero='4000000000000002')
        self.assertEqual(self.pagar(reserva).data['estado'], 'aprobado')

    def test_reserva_ajena_o_inexistente_404(self):
        self.assertEqual(self.pagar(self.reserva(pasajero=self.otro)).status_code, 404)
        r = self.client.post('/api/pagos/tarjeta/', {'reserva_id': '00000000-0000-0000-0000-000000000000', **TARJETA_OK}, format='json')
        self.assertEqual(r.status_code, 404)

    def test_vuelo_cancelado_salido_o_sin_lugar_400(self):
        cancelado = self.crear_vuelo('FA 3000', HOY + dt.timedelta(days=5), estado=Vuelo.Estado.CANCELADO)
        salido = self.crear_vuelo('FA 3001', HOY, hora_partida=dt.time(9, 0), hora_llegada=dt.time(10, 0))
        lleno = self.crear_vuelo('FA 3002', HOY + dt.timedelta(days=6), asientos_disponibles_economy=1)
        for vuelo, cantidad in ((cancelado, 1), (salido, 1), (lleno, 2)):
            r = self.pagar(self.reserva(vuelo=vuelo, cantidad=cantidad))
            self.assertEqual(r.status_code, 400, vuelo.numero_vuelo)
            self.assertIn('non_field_errors', r.data)
        self.assertFalse(Pago.objects.exists())

    def test_solo_pasajeros(self):
        reserva = self.reserva()
        self.client.force_authenticate(None)
        self.assertEqual(self.pagar(reserva).status_code, 401)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.pagar(reserva).status_code, 403)


class ConsultaPagosTests(Datos):
    def test_lista_solo_los_pagos_propios(self):
        propio = self.pago(self.reserva())
        self.pago(self.reserva(pasajero=self.otro))
        r = self.client.get('/api/pagos/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([p['id'] for p in r.data], [str(propio.id)])

    def test_detalle_propio_y_404_para_ajeno_o_id_malformado(self):
        propio = self.pago(self.reserva())
        ajeno = self.pago(self.reserva(pasajero=self.otro))
        self.assertEqual(self.client.get(f'/api/pagos/{propio.id}/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/pagos/{ajeno.id}/').status_code, 404)
        r = self.client.get('/api/pagos/abc/')
        self.assertEqual(r.status_code, 404)
        self.assertIn('detail', r.data)

    def test_un_segundo_aprobado_queda_rechazado_sin_descontar_ni_dar_500(self):
        reserva = self.reserva(cantidad=2)
        self.pago(reserva)  # aprobado cargado directo: la reserva sigue pendiente, así salta el constraint
        segundo = self.pago(reserva, estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        segundo = servicios.confirmar_compra(segundo, 'Pago aprobado.')
        segundo.refresh_from_db()
        reserva.refresh_from_db()
        self.vuelos[0].refresh_from_db()
        self.assertEqual((segundo.estado, segundo.detalle), ('rechazado', servicios.YA_PAGADA))
        self.assertEqual(reserva.estado, 'pendiente')
        self.assertEqual(self.vuelos[0].asientos_disponibles_economy, 30)


class ConfirmacionTests(Datos):
    def pagar(self, reserva, numero='4242424242424242'):
        datos = {'reserva_id': str(reserva.id), 'numero': numero, 'titular': 'Ana', 'vencimiento': '12/30', 'cvv': '123'}
        return self.client.post('/api/pagos/tarjeta/', datos, format='json')

    def asientos(self, vuelo):
        vuelo.refresh_from_db()
        return vuelo.asientos_disponibles_economy, vuelo.asientos_disponibles_primera

    def test_aprobado_descuenta_los_asientos_de_su_clase_y_confirma(self):
        reserva = self.reserva(clase='primera', cantidad=2)
        self.assertEqual(self.pagar(reserva).data['estado'], 'aprobado')
        self.assertEqual(self.asientos(self.vuelos[0]), (30, 10))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pagada')

    def test_rechazado_no_toca_asientos_ni_reserva(self):
        reserva = self.reserva(cantidad=3)
        self.assertEqual(self.pagar(reserva, numero='4000000000009995').data['estado'], 'rechazado')
        self.assertEqual(self.asientos(self.vuelos[0]), (30, 12))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pendiente')

    def test_confirmar_dos_veces_descuenta_una(self):
        reserva = self.reserva(cantidad=2)
        pago = self.pago(reserva, estado=Pago.Estado.PENDIENTE)
        servicios.confirmar_compra(pago, 'Pago aprobado.')
        servicios.confirmar_compra(pago, 'Pago aprobado.')
        self.assertEqual(self.asientos(self.vuelos[0]), (28, 12))

    def test_reserva_ya_pagada_no_vuelve_a_descontar(self):
        reserva = self.reserva(cantidad=2)
        reservas_mock.marcar_pagada(reserva)
        pago = servicios.confirmar_compra(self.pago(reserva, estado=Pago.Estado.PENDIENTE), 'Pago aprobado.')
        self.assertEqual((pago.estado, pago.detalle), ('rechazado', servicios.YA_PAGADA))
        self.assertEqual(self.asientos(self.vuelos[0]), (30, 12))

    def test_una_reserva_pagada_no_se_puede_volver_a_pagar(self):
        reserva = self.reserva()
        reservas_mock.marcar_pagada(reserva)
        self.assertEqual(self.pagar(reserva).status_code, 409)


class FacturacionTests(Datos):
    def pagar(self, reserva_id, numero='4242424242424242'):
        return self.client.post(
            '/api/pagos/tarjeta/',
            {
                'reserva_id': str(reserva_id),
                'numero': numero,
                'titular': 'Ana',
                'vencimiento': '12/30',
                'cvv': '123',
            },
            format='json',
        )

    def test_compra_aprobada_asocia_y_envia_factura_pdf_al_correo_de_la_reserva(self):
        reserva = crear_reserva(
            usuario=self.pasajero,
            vuelo_id=self.vuelos[0].id,
            clase='economy',
            cantidad_pasajes=1,
            pasajeros=[{
                'nombre_pasajero': 'Ana',
                'apellido_pasajero': 'Pérez',
                'dni_pasajero': '12345678',
            }],
            contacto_email='facturacion@mail.com',
        )

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.pagar(reserva.id)

        self.assertEqual((respuesta.status_code, respuesta.data['estado']), (201, 'aprobado'))
        pago = Pago.objects.get(id=respuesta.data['id'])
        self.assertTrue(pago.numero_factura.startswith('FA-2026-'))
        self.assertEqual(mail.outbox[-1].to, ['facturacion@mail.com'])
        self.assertIn(pago.numero_factura, mail.outbox[-1].subject)
        self.assertEqual(len(mail.outbox[-1].attachments), 1)
        nombre, contenido, tipo = mail.outbox[-1].attachments[0]
        self.assertEqual((nombre, tipo), (f'factura-{pago.numero_factura}.pdf', 'application/pdf'))
        self.assertTrue(contenido.startswith(b'%PDF'))
        self.assertIn('12345678', mail.outbox[-1].alternatives[0][0])

    def test_pago_rechazado_no_genera_factura_ni_envia_correo(self):
        reserva = self.reserva()

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.pagar(reserva.id, numero='4000000000000002')

        self.assertEqual(respuesta.data['estado'], 'rechazado')
        pago = Pago.objects.get(id=respuesta.data['id'])
        self.assertIsNone(pago.numero_factura)
        self.assertEqual(mail.outbox, [])

    def test_error_al_armar_la_factura_no_tumba_la_compra(self):
        reserva = self.reserva()
        with patch('pagos.factura.render_to_string', side_effect=RuntimeError('template roto')):
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.pagar(reserva.id)

        self.assertEqual((respuesta.status_code, respuesta.data['estado']), (201, 'aprobado'))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pagada')

    def test_error_de_la_api_de_correo_no_tumba_la_compra(self):
        reserva = self.reserva()
        with patch('pagos.factura.EmailMultiAlternatives.send', side_effect=AnymailAPIError('Brevo respondió 401')):
            with self.assertLogs('pagos.factura', level='ERROR'):
                with self.captureOnCommitCallbacks(execute=True):
                    respuesta = self.pagar(reserva.id)

        self.assertEqual((respuesta.status_code, respuesta.data['estado']), (201, 'aprobado'))

    def test_error_de_correo_no_revierte_ni_duplica_la_compra(self):
        reserva = self.reserva(cantidad=2)

        with patch('pagos.factura.EmailMultiAlternatives.send', side_effect=smtplib.SMTPException('Sin conexión')):
            with self.assertLogs('pagos.factura', level='ERROR'):
                with self.captureOnCommitCallbacks(execute=True):
                    respuesta = self.pagar(reserva.id)

        self.assertEqual((respuesta.status_code, respuesta.data['estado']), (201, 'aprobado'))
        pago = Pago.objects.get(id=respuesta.data['id'])
        self.assertTrue(pago.numero_factura)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, 'pagada')
        self.assertEqual(Pago.objects.filter(reserva_id=reserva.id, estado=Pago.Estado.APROBADO).count(), 1)
        self.vuelos[0].refresh_from_db()
        self.assertEqual(self.vuelos[0].asientos_disponibles_economy, 28)
        self.assertEqual(self.pagar(reserva.id).status_code, 409)
        self.assertEqual(Pago.objects.filter(reserva_id=reserva.id, estado=Pago.Estado.APROBADO).count(), 1)

    def test_confirmar_compra_idempotente_no_reenvia_factura(self):
        reserva = self.reserva()
        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.pagar(reserva.id)

            pago = Pago.objects.get(id=respuesta.data['id'])
            with self.captureOnCommitCallbacks(execute=True):
                servicios.confirmar_compra(pago, 'Pago aprobado.')

        self.assertEqual(len(mail.outbox), 1)


@patch('pagos.mercadopago.cuenta_del_comprador', new=lambda pago_id: None)
@patch('pagos.mercadopago.cancelar_orden')
@patch('pagos.mercadopago.consultar_orden')
@patch('pagos.mercadopago.crear_orden', return_value=('ORDTST1', 'https://mp.test/checkout'))
class PagoMercadoPagoTests(Datos):
    APROBADA = {
        'status': 'processed',
        'status_detail': 'accredited',
        'transactions': {'payments': [{'payment_method': {'id': 'master'}}]},
    }

    def pagar(self, reserva):
        return self.client.post('/api/pagos/mercadopago/', {'reserva_id': str(reserva.id)}, format='json')

    def test_aprobado_al_volver_descuenta_y_confirma(self, crear, consultar, cancelar):
        reserva = self.reserva(clase='primera', cantidad=2)
        pago_id = self.pagar(reserva).data['pago']['id']
        consultar.return_value = self.APROBADA
        self.assertEqual(self.client.get(f'/api/pagos/{pago_id}/').data['estado'], 'aprobado')
        self.client.get(f'/api/pagos/{pago_id}/')  # volver a abrirlo no descuenta otra vez
        self.vuelos[0].refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual((self.vuelos[0].asientos_disponibles_primera, reserva.estado), (10, 'pagada'))

    def test_aprobacion_de_mp_tambien_envia_factura(self, crear, consultar, cancelar):
        reserva = self.reserva()
        pago_id = self.pagar(reserva).data['pago']['id']
        consultar.return_value = self.APROBADA

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            with self.captureOnCommitCallbacks(execute=True):
                respuesta = self.client.get(f'/api/pagos/{pago_id}/')

        self.assertEqual(respuesta.data['estado'], 'aprobado')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.pasajero.email])
        pago = Pago.objects.get(id=pago_id)
        self.assertIn(pago.numero_factura, mail.outbox[0].subject)

    def test_rechazado_de_mp_no_toca_asientos(self, crear, consultar, cancelar):
        reserva = self.reserva(cantidad=2)
        pago_id = self.pagar(reserva).data['pago']['id']
        consultar.return_value = {'status': 'failed', 'status_detail': 'rejected_by_issuer'}
        self.client.get(f'/api/pagos/{pago_id}/')
        self.vuelos[0].refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual((self.vuelos[0].asientos_disponibles_economy, reserva.estado), (30, 'pendiente'))

    def test_sin_asientos_al_aprobarse_corresponde_devolucion(self, crear, consultar, cancelar):
        reserva = self.reserva(cantidad=2)
        pago_id = self.pagar(reserva).data['pago']['id']
        Vuelo.objects.filter(id=self.vuelos[0].id).update(asientos_disponibles_economy=1)  # otro compró mientras tanto
        consultar.return_value = self.APROBADA
        r = self.client.get(f'/api/pagos/{pago_id}/')
        self.assertEqual((r.data['estado'], r.data['detalle'], r.data['marca']), ('rechazado', servicios.SIN_ASIENTOS, 'mastercard'))
        self.vuelos[0].refresh_from_db()
        self.assertEqual(self.vuelos[0].asientos_disponibles_economy, 1)

    def test_vuelo_cancelado_mientras_pagaba(self, crear, consultar, cancelar):
        reserva = self.reserva()
        pago_id = self.pagar(reserva).data['pago']['id']
        Vuelo.objects.filter(id=self.vuelos[0].id).update(estado=Vuelo.Estado.CANCELADO)
        consultar.return_value = self.APROBADA
        r = self.client.get(f'/api/pagos/{pago_id}/')
        self.assertEqual((r.data['estado'], r.data['detalle']), ('rechazado', servicios.VUELO_NO_DISPONIBLE))

    def test_crea_la_orden_con_el_monto_del_backend(self, crear, consultar, cancelar):
        reserva = self.reserva(clase='primera', cantidad=2)
        r = self.pagar(reserva)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['checkout_url'], 'https://mp.test/checkout')
        self.assertEqual(r.data['pago']['estado'], 'pendiente')
        pago = Pago.objects.get()
        self.assertEqual((pago.transaccion_externa_id, pago.monto), ('ORDTST1', Decimal('500000.00')))
        enviado, items = crear.call_args.args
        self.assertEqual(enviado.id, pago.id)
        self.assertEqual(items, [('Vuelo FA 1000 AEP → COR, primera', 2, Decimal('250000.00'))])

    def test_si_mp_falla_el_pago_queda_rechazado_y_502(self, crear, consultar, cancelar):
        crear.side_effect = mercadopago.ErrorMercadoPago('timeout')
        r = self.pagar(self.reserva())
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.data['detail'], 'No pudimos conectar con Mercado Pago.')
        self.assertEqual(Pago.objects.get().estado, 'rechazado')

    def test_al_volver_se_consulta_la_orden(self, crear, consultar, cancelar):
        pago_id = self.pagar(self.reserva()).data['pago']['id']
        consultar.return_value = {'status': 'processed', 'status_detail': 'accredited'}
        r = self.client.get(f'/api/pagos/{pago_id}/')
        consultar.assert_called_with('ORDTST1')
        self.assertEqual((r.data['estado'], r.data['detalle']), ('aprobado', 'Pago aprobado.'))

    def test_al_volver_guarda_marca_y_cuenta_del_comprador(self, crear, consultar, cancelar):
        pago_id = self.pagar(self.reserva()).data['pago']['id']
        consultar.return_value = {
            'status': 'processed',
            'status_detail': 'accredited',
            'transactions': {'payments': [{'payment_method': {'id': 'master', 'type': 'credit_card'}}]},
        }
        with patch('pagos.mercadopago.cuenta_del_comprador', return_value='test_user_123@testuser.com') as cuenta:
            r = self.client.get(f'/api/pagos/{pago_id}/')
        cuenta.assert_called_once_with(pago_id)
        self.assertEqual((r.data['marca'], r.data['cuenta_mp']), ('mastercard', 'test_user_123@testuser.com'))

    def test_rechazo_de_mp_con_motivo(self, crear, consultar, cancelar):
        pago_id = self.pagar(self.reserva()).data['pago']['id']
        consultar.return_value = {'status': 'failed', 'status_detail': 'card_insufficient_amount'}
        r = self.client.get(f'/api/pagos/{pago_id}/')
        self.assertEqual((r.data['estado'], r.data['detalle']), ('rechazado', 'Fondos insuficientes.'))

    def test_sin_conexion_al_volver_sigue_pendiente(self, crear, consultar, cancelar):
        pago_id = self.pagar(self.reserva()).data['pago']['id']
        consultar.side_effect = mercadopago.ErrorMercadoPago('timeout')
        r = self.client.get(f'/api/pagos/{pago_id}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['estado'], 'pendiente')

    def test_volvio_sin_pagar_y_paga_con_tarjeta(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pagar(reserva)
        consultar.return_value = {'status': 'created', 'status_detail': 'created'}
        r = self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK}, format='json')
        self.assertEqual(r.data['estado'], 'aprobado')
        cancelar.assert_called_once_with('ORDTST1')
        abandonado = Pago.objects.get(metodo_pago='mercadopago')
        self.assertEqual((abandonado.estado, abandonado.detalle), ('rechazado', 'Reemplazado por un nuevo intento de pago.'))

    def test_con_un_pago_de_mp_en_proceso_409(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pagar(reserva)
        consultar.return_value = {'status': 'processing', 'status_detail': 'in_process'}
        r = self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['detail'], servicios.EN_PROCESO)
        cancelar.assert_not_called()

    def test_mp_aprobado_mientras_tanto_entonces_ya_pagada(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pagar(reserva)
        consultar.return_value = {'status': 'processed', 'status_detail': 'accredited'}
        r = self.pagar(reserva)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['detail'], 'La reserva ya está pagada.')


    def pagar_con_tarjeta(self, reserva):
        return self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK}, format='json')

    def test_orden_vencida_no_bloquea(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.client.post('/api/pagos/mercadopago/', {'reserva_id': str(reserva.id)}, format='json')
        consultar.return_value = {'status': 'expired', 'status_detail': 'expired'}
        self.assertEqual(self.pagar_con_tarjeta(reserva).data['estado'], 'aprobado')
        vencido = Pago.objects.get(metodo_pago='mercadopago')
        self.assertEqual((vencido.estado, vencido.detalle), ('rechazado', 'El pago no se completó a tiempo.'))

    def test_si_crear_orden_explota_el_pago_queda_rechazado(self, crear, consultar, cancelar):
        crear.side_effect = RuntimeError('inesperado')
        reserva = self.reserva()
        with self.assertRaises(RuntimeError):
            self.client.post('/api/pagos/mercadopago/', {'reserva_id': str(reserva.id)}, format='json')
        self.assertEqual(Pago.objects.get().estado, 'rechazado')
        self.assertEqual(self.pagar_con_tarjeta(reserva).data['estado'], 'aprobado')

    def test_pendiente_sin_orden_viejo_no_bloquea(self, crear, consultar, cancelar):
        reserva = self.reserva()
        huerfano = self.pago(reserva, estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        Pago.objects.filter(id=huerfano.id).update(creado_en=AHORA - dt.timedelta(minutes=10))
        self.assertEqual(self.pagar_con_tarjeta(reserva).data['estado'], 'aprobado')
        consultar.assert_not_called()
        self.assertEqual(Pago.objects.get(id=huerfano.id).estado, 'rechazado')

    def test_pendiente_sin_orden_reciente_es_409(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pago(reserva, estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        self.assertEqual(self.pagar_con_tarjeta(reserva).status_code, 409)
        consultar.assert_not_called()


class ClienteMercadoPagoTests(Datos):
    def test_resultado_de_cada_estado_de_la_orden(self):
        self.assertEqual(mercadopago.resultado_de('processed', 'accredited'), ('aprobado', 'Pago aprobado.'))
        self.assertEqual(mercadopago.resultado_de('failed', 'rejected_by_issuer'), ('rechazado', 'Tarjeta rechazada por el emisor.'))
        self.assertEqual(mercadopago.resultado_de('failed', 'otro'), ('rechazado', 'Mercado Pago rechazó el pago.'))
        self.assertEqual(mercadopago.resultado_de('canceled', 'canceled')[0], 'rechazado')
        self.assertEqual(mercadopago.resultado_de('processed', 'refunded')[0], 'rechazado')
        for status in ('created', 'processing', 'action_required'):
            self.assertEqual(mercadopago.resultado_de(status, None)[0], 'pendiente')

    def test_marca_de_la_orden(self):
        self.assertEqual(mercadopago.marca_de_orden({'transactions': {'payments': [{'payment_method': {'id': 'master'}}]}}), 'mastercard')
        self.assertIsNone(mercadopago.marca_de_orden({'transactions': {'payments': [{'payment_method': {'id': 'account_money'}}]}}))
        self.assertIsNone(mercadopago.marca_de_orden({}))

    def test_cuenta_del_comprador_sale_de_la_busqueda_de_pagos(self):
        respuesta = {'results': [{'payer': {'email': 'test_user_1@testuser.com'}}]}
        with patch('pagos.mercadopago._llamar', return_value=respuesta) as llamar:
            self.assertEqual(mercadopago.cuenta_del_comprador('abc'), 'test_user_1@testuser.com')
        self.assertTrue(llamar.call_args.args[1].endswith('/v1/payments/search?external_reference=abc'))
        with patch('pagos.mercadopago._llamar', return_value={'results': []}):
            self.assertIsNone(mercadopago.cuenta_del_comprador('abc'))
        with patch('pagos.mercadopago._llamar', side_effect=mercadopago.ErrorMercadoPago('x')):
            self.assertIsNone(mercadopago.cuenta_del_comprador('abc'))

    @patch('pagos.mercadopago._llamar', return_value={'id': 'ORDTST1', 'checkout_url': 'https://mp.test/c'})
    def test_crear_orden_arma_el_pedido(self, llamar):
        pago = self.pago(self.reserva(), estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        resultado = mercadopago.crear_orden(pago, [('Vuelo FA 1000 AEP → COR, economy', 1, Decimal('100000.00'))])
        self.assertEqual(resultado, ('ORDTST1', 'https://mp.test/c'))
        metodo, url, cuerpo = llamar.call_args.args
        self.assertEqual((metodo, url), ('POST', 'https://api.mercadopago.com/v1/orders'))
        self.assertEqual(llamar.call_args.kwargs['idempotencia'], str(pago.id))
        self.assertEqual(cuerpo['total_amount'], '100000.00')
        self.assertEqual(cuerpo['external_reference'], str(pago.id))
        self.assertEqual(cuerpo['config']['online']['success_url'], f'{settings.FRONTEND_URL}/pagos/{pago.id}')

    @patch('pagos.mercadopago._llamar', return_value={'status': 'created'})
    def test_respuesta_sin_checkout_url_es_error(self, llamar):
        pago = self.pago(self.reserva(), estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        with self.assertRaises(mercadopago.ErrorMercadoPago):
            mercadopago.crear_orden(pago, [])

    def test_sin_token_es_error(self):
        with self.settings(MP_ACCESS_TOKEN=''), self.assertRaises(mercadopago.ErrorMercadoPago):
            mercadopago.consultar_orden('ORDTST1')

    def test_corte_a_mitad_de_respuesta_es_error_de_mp(self):
        for error in (http.client.RemoteDisconnected('cerró'), ConnectionResetError(), http.client.IncompleteRead(b'')):
            with self.subTest(error=type(error).__name__), self.settings(MP_ACCESS_TOKEN='x'), \
                    patch('urllib.request.urlopen', side_effect=error), self.assertRaises(mercadopago.ErrorMercadoPago):
                mercadopago.consultar_orden('ORDTST1')

    def test_get_del_pago_con_corte_de_conexion_sigue_pendiente(self):
        reserva = self.reserva()
        pago = self.pago(reserva, estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO, transaccion_externa_id='ORDTST1')
        with self.settings(MP_ACCESS_TOKEN='x'), patch('urllib.request.urlopen', side_effect=http.client.RemoteDisconnected('cerró')):
            r = self.client.get(f'/api/pagos/{pago.id}/')
        self.assertEqual((r.status_code, r.data['estado']), (200, 'pendiente'))
