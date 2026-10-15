import datetime as dt
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from vuelos.models import Aeropuerto, Avion, Vuelo

from . import mercadopago, reservas_mock, servicios, tarjeta
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
        pago = Pago.objects.get(id=r.data['id'])
        self.assertEqual((pago.reserva_id, pago.metodo_pago), (reserva.id, 'tarjeta'))
        self.assertIsNotNone(pago.procesado_en)

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

    def test_un_segundo_aprobado_queda_rechazado_y_no_da_500(self):
        reserva = self.reserva()
        self.pago(reserva)
        segundo = self.pago(reserva, estado=Pago.Estado.PENDIENTE, metodo=Pago.Metodo.MERCADOPAGO)
        servicios.guardar_resultado(segundo, Pago.Estado.APROBADO, 'Pago aprobado.')
        segundo.refresh_from_db()
        self.assertEqual(segundo.estado, 'rechazado')
        self.assertEqual(segundo.detalle, servicios.YA_PAGADA)


@patch('pagos.mercadopago.cancelar_orden')
@patch('pagos.mercadopago.consultar_orden')
@patch('pagos.mercadopago.crear_orden', return_value=('ORDTST1', 'https://mp.test/checkout'))
class PagoMercadoPagoTests(Datos):
    def pagar(self, reserva):
        return self.client.post('/api/pagos/mercadopago/', {'reserva_id': str(reserva.id)}, format='json')

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
        consultar.return_value = ('processed', 'accredited')
        r = self.client.get(f'/api/pagos/{pago_id}/')
        consultar.assert_called_with('ORDTST1')
        self.assertEqual((r.data['estado'], r.data['detalle']), ('aprobado', 'Pago aprobado.'))

    def test_rechazo_de_mp_con_motivo(self, crear, consultar, cancelar):
        pago_id = self.pagar(self.reserva()).data['pago']['id']
        consultar.return_value = ('failed', 'card_insufficient_amount')
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
        consultar.return_value = ('created', 'created')
        r = self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK}, format='json')
        self.assertEqual(r.data['estado'], 'aprobado')
        cancelar.assert_called_once_with('ORDTST1')
        abandonado = Pago.objects.get(metodo_pago='mercadopago')
        self.assertEqual((abandonado.estado, abandonado.detalle), ('rechazado', 'Reemplazado por un nuevo intento de pago.'))

    def test_con_un_pago_de_mp_en_proceso_409(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pagar(reserva)
        consultar.return_value = ('processing', 'in_process')
        r = self.client.post('/api/pagos/tarjeta/', {'reserva_id': str(reserva.id), **TARJETA_OK}, format='json')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['detail'], servicios.EN_PROCESO)
        cancelar.assert_not_called()

    def test_mp_aprobado_mientras_tanto_entonces_ya_pagada(self, crear, consultar, cancelar):
        reserva = self.reserva()
        self.pagar(reserva)
        consultar.return_value = ('processed', 'accredited')
        r = self.pagar(reserva)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['detail'], 'La reserva ya está pagada.')


class ClienteMercadoPagoTests(Datos):
    def test_resultado_de_cada_estado_de_la_orden(self):
        self.assertEqual(mercadopago.resultado_de('processed', 'accredited'), ('aprobado', 'Pago aprobado.'))
        self.assertEqual(mercadopago.resultado_de('failed', 'rejected_by_issuer'), ('rechazado', 'Tarjeta rechazada por el emisor.'))
        self.assertEqual(mercadopago.resultado_de('failed', 'otro'), ('rechazado', 'Mercado Pago rechazó el pago.'))
        self.assertEqual(mercadopago.resultado_de('canceled', 'canceled')[0], 'rechazado')
        self.assertEqual(mercadopago.resultado_de('processed', 'refunded')[0], 'rechazado')
        for status in ('created', 'processing', 'action_required'):
            self.assertEqual(mercadopago.resultado_de(status, None)[0], 'pendiente')

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
