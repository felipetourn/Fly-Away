import datetime as dt
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APITestCase

from vuelos.models import Aeropuerto, Avion, Vuelo

from .models import Pasaje, Reserva

BA = ZoneInfo('America/Argentina/Buenos_Aires')
AHORA = dt.datetime(2026, 10, 20, 12, 0, tzinfo=BA)
HOY = AHORA.date()
Usuario = get_user_model()


def pasajeros(cantidad):
    return [
        {'nombre_pasajero': f'Viajero {"ABCDEFGHIJKL"[n]}', 'apellido_pasajero': 'Pérez', 'dni_pasajero': f'3000000{n}'}
        for n in range(cantidad)
    ]


class ReservasBaseTestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pasajero = Usuario.objects.create_user('juan@mail.com', 'pass1234', nombre='Juan', apellido='Pérez')
        cls.otro_pasajero = Usuario.objects.create_user('maria@mail.com', 'pass1234', nombre='María', apellido='Gómez')
        cls.admin = Usuario.objects.create_superuser('admin@mail.com', 'pass1234', nombre='Ada', apellido='Admin')

        cls.aep = Aeropuerto.objects.create(codigo_iata='AEP', nombre='Aeroparque', ciudad='Buenos Aires', pais='Argentina')
        cls.cor = Aeropuerto.objects.create(codigo_iata='COR', nombre='Pajas Blancas', ciudad='Córdoba', pais='Argentina')
        cls.avion = Avion.objects.create(matricula='LV-FAA', modelo='Airbus A320', capacidad_economy=150, capacidad_primera=12)

        cls.vuelo = Vuelo.objects.create(
            numero_vuelo='FA 1001',
            avion=cls.avion,
            aeropuerto_origen=cls.aep,
            aeropuerto_destino=cls.cor,
            fecha_operacion=HOY + dt.timedelta(days=2),
            fecha_llegada=HOY + dt.timedelta(days=2),
            hora_partida=dt.time(10, 0),
            hora_llegada=dt.time(11, 30),
            precio_economy=Decimal('100000.00'),
            precio_primera=Decimal('250000.00'),
            asientos_disponibles_economy=10,
            asientos_disponibles_primera=4,
            creado_por=cls.admin,
        )
        cls.vuelo_vuelta = Vuelo.objects.create(
            numero_vuelo='FA 1002',
            avion=cls.avion,
            aeropuerto_origen=cls.cor,
            aeropuerto_destino=cls.aep,
            fecha_operacion=HOY + dt.timedelta(days=5),
            fecha_llegada=HOY + dt.timedelta(days=5),
            hora_partida=dt.time(14, 0),
            hora_llegada=dt.time(15, 30),
            precio_economy=Decimal('120000.00'),
            precio_primera=Decimal('270000.00'),
            asientos_disponibles_economy=10,
            asientos_disponibles_primera=4,
            creado_por=cls.admin,
        )

    def setUp(self):
        reloj = patch('django.utils.timezone.now', return_value=AHORA)
        reloj.start()
        self.addCleanup(reloj.stop)
        self.client.force_authenticate(self.pasajero)


class ModeloReservasTests(ReservasBaseTestCase):
    def test_nombres_de_tablas_segun_dbml(self):
        self.assertEqual(Reserva._meta.db_table, 'reservas')
        self.assertEqual(Pasaje._meta.db_table, 'pasajes')

    def test_cantidad_pasajes_constraint_entre_1_y_9(self):
        # 0 pasajes falla
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reserva.objects.create(
                pasajero=self.pasajero,
                contacto_email='test@mail.com',
                vuelo=self.vuelo,
                cantidad_pasajes=0,
            )
        # 10 pasajes falla
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reserva.objects.create(
                pasajero=self.pasajero,
                contacto_email='test@mail.com',
                vuelo=self.vuelo,
                cantidad_pasajes=10,
            )


    def test_pasajes_en_el_orden_de_los_pasajeros(self):
        # El código lleva una parte aleatoria por pasajero: el orden lo da el índice final, no el código entero.
        reserva = Reserva.objects.create(
            pasajero=self.pasajero, contacto_email='test@mail.com', vuelo=self.vuelo, cantidad_pasajes=3,
        )
        for codigo in ['FA1001-000000-03', 'FA1001-FFFFFF-01', 'FA1001-888888-02']:
            Pasaje.objects.create(
                reserva=reserva, codigo_pasaje=codigo, nombre_pasajero='A', apellido_pasajero='B',
                dni_pasajero='1', clase='economy', precio=Decimal('1.00'),
            )
        self.assertEqual(
            [p.codigo_pasaje[-2:] for p in reserva.pasajes.all()], ['01', '02', '03'],
        )


class ReservasEndpointTests(ReservasBaseTestCase):
    def ida_y_vuelta(self, vuelta):
        datos = {'clase': 'economy', 'cantidad_pasajes': 1, 'pasajeros': pasajeros(1)}
        return self.client.post(
            '/api/reservas/ida-vuelta/',
            {'vuelo_ida': str(self.vuelo.id), 'vuelo_vuelta': str(vuelta.id), 'ida': datos, 'vuelta': datos},
            format='json',
        )

    def test_ida_y_vuelta_crea_dos_reservas_para_pagar_por_separado(self):
        res = self.client.post(
            '/api/reservas/ida-vuelta/',
            {
                'vuelo_ida': str(self.vuelo.id),
                'vuelo_vuelta': str(self.vuelo_vuelta.id),
                'ida': {
                    'clase': 'economy',
                    'cantidad_pasajes': 2,
                    'pasajeros': [
                        {'nombre_pasajero': 'Juan', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '12345678'},
                        {'nombre_pasajero': 'Lucía', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '87654321'},
                    ],
                },
                'vuelta': {
                    'clase': 'primera',
                    'cantidad_pasajes': 1,
                    'pasajeros': [
                        {'nombre_pasajero': 'Juan', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '12345678'},
                    ],
                },
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reserva.objects.filter(pasajero=self.pasajero).count(), 2)
        self.assertEqual(res.data['ida']['vuelo']['id'], str(self.vuelo.id))
        self.assertEqual(res.data['vuelta']['vuelo']['id'], str(self.vuelo_vuelta.id))
        self.assertEqual(res.data['ida']['monto'], '200000.00')
        self.assertEqual(res.data['vuelta']['monto'], '270000.00')
        self.assertEqual(res.data['ida']['clase'], 'economy')
        self.assertEqual(res.data['vuelta']['clase'], 'primera')
        self.assertEqual(res.data['ida']['cantidad_pasajes'], 2)
        self.assertEqual(res.data['vuelta']['cantidad_pasajes'], 1)
        self.assertEqual(res.data['ida']['estado'], 'pendiente')
        self.assertEqual(res.data['vuelta']['estado'], 'pendiente')
        self.assertEqual(len(res.data['ida']['pasajes']), 2)
        self.assertEqual(len(res.data['vuelta']['pasajes']), 1)

    def test_ida_y_vuelta_no_deja_reserva_si_el_segundo_vuelo_no_es_valido(self):
        self.vuelo_vuelta.estado = Vuelo.Estado.CANCELADO
        self.vuelo_vuelta.save()

        res = self.client.post(
            '/api/reservas/ida-vuelta/',
            {
                'vuelo_ida': str(self.vuelo.id),
                'vuelo_vuelta': str(self.vuelo_vuelta.id),
                'ida': {'clase': 'economy', 'cantidad_pasajes': 1, 'pasajeros': pasajeros(1)},
                'vuelta': {'clase': 'economy', 'cantidad_pasajes': 1, 'pasajeros': pasajeros(1)},
            },
            format='json',
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Reserva.objects.filter(pasajero=self.pasajero).count(), 0)
        self.assertEqual(Pasaje.objects.count(), 0)

    def test_ida_y_vuelta_rechaza_vuelta_que_no_hace_la_ruta_inversa(self):
        Vuelo.objects.filter(id=self.vuelo_vuelta.id).update(aeropuerto_origen=self.aep, aeropuerto_destino=self.cor)
        res = self.ida_y_vuelta(self.vuelo_vuelta)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vuelo_vuelta', res.data)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_ida_y_vuelta_rechaza_vuelta_que_sale_antes_de_que_llegue_la_ida(self):
        Vuelo.objects.filter(id=self.vuelo_vuelta.id).update(
            fecha_operacion=self.vuelo.fecha_llegada, hora_partida=self.vuelo.hora_llegada
        )
        res = self.ida_y_vuelta(self.vuelo_vuelta)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vuelo_vuelta', res.data)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_exige_los_datos_de_cada_pasajero(self):
        incompletos = [
            {'cantidad_pasajes': 1},
            {'cantidad_pasajes': 2, 'pasajeros': pasajeros(1)},
            {'cantidad_pasajes': 1, 'pasajeros': [{**pasajeros(1)[0], 'dni_pasajero': ''}]},
        ]
        for datos in incompletos:
            res = self.client.post(
                '/api/reservas/', {'vuelo_id': str(self.vuelo.id), 'clase': 'economy', **datos}, format='json'
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, datos)
            self.assertIn('pasajeros', res.data)
        self.assertEqual(Reserva.objects.count(), 0)

    def test_rechaza_nombre_apellido_o_dni_invalidos(self):
        invalidos = [
            ('nombre_pasajero', '30111222'),
            ('nombre_pasajero', 'Juan2'),
            ('apellido_pasajero', '-Pérez'),
            ('apellido_pasajero', '@@'),
            ('dni_pasajero', '123'),
            ('dni_pasajero', '1234567890123456'),
            ('dni_pasajero', '30$111'),
        ]
        for campo, valor in invalidos:
            res = self.client.post('/api/reservas/', {
                'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 1,
                'pasajeros': [{**pasajeros(1)[0], campo: valor}],
            }, format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, (campo, valor))
            self.assertIn(campo, res.data['pasajeros'][0], (campo, valor))
        self.assertEqual(Reserva.objects.count(), 0)

    def test_acepta_nombres_compuestos_y_normaliza_el_dni(self):
        res = self.client.post('/api/reservas/', {
            'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 1,
            'pasajeros': [{'nombre_pasajero': 'María José', 'apellido_pasajero': "D'Alessandro-Muñoz",
                           'dni_pasajero': '30.111 222'}],
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        pasaje = Pasaje.objects.get()
        self.assertEqual(pasaje.dni_pasajero, '30111222')
        self.assertEqual(pasaje.apellido_pasajero, "D'Alessandro-Muñoz")

    def test_reserva_exitosa_clase_economy(self):
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 2,
            'pasajeros': [
                {'nombre_pasajero': 'Juan', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '12345678'},
                {'nombre_pasajero': 'Lucía', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '87654321'},
            ],
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data

        self.assertEqual(data['estado'], 'pendiente')
        self.assertEqual(data['cantidad_pasajes'], 2)
        self.assertEqual(data['clase'], 'economy')
        self.assertEqual(data['monto'], '200000.00')
        self.assertEqual(len(data['pasajes']), 2)
        self.assertEqual(data['vuelo']['id'], str(self.vuelo.id))

        # Base de datos
        reserva = Reserva.objects.get(id=data['id'])
        self.assertEqual(reserva.pasajero, self.pasajero)
        self.assertEqual(reserva.vuelo, self.vuelo)
        self.assertEqual(reserva.estado, Reserva.Estado.PENDIENTE)
        self.assertEqual(reserva.pasajes.count(), 2)
        self.assertEqual(reserva.pasajes.first().precio, Decimal('100000.00'))

    def test_reserva_exitosa_clase_primera(self):
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'primera',
            'cantidad_pasajes': 3,
            'pasajeros': pasajeros(3),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['monto'], '750000.00')
        self.assertEqual(len(res.data['pasajes']), 3)

    def test_no_permite_mas_de_9_pasajes(self):
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 10,
            'pasajeros': pasajeros(10),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cantidad_pasajes', res.data)

    def test_no_permite_menos_de_1_pasaje(self):
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 0,
            'pasajeros': pasajeros(0),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cantidad_pasajes', res.data)

    def test_rechaza_si_supera_disponibilidad(self):
        # En primera hay solo 4 asientos disponibles
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'primera',
            'cantidad_pasajes': 5,
            'pasajeros': pasajeros(5),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Mensaje indicando el motivo
        self.assertIn('non_field_errors', res.data)
        self.assertIn('disponibles', str(res.data['non_field_errors'][0]).lower())

    def test_rechaza_vuelo_inexistente(self):
        url = '/api/reservas/'
        payload = {
            'vuelo_id': '00000000-0000-0000-0000-000000000000',
            'clase': 'economy',
            'cantidad_pasajes': 1,
            'pasajeros': pasajeros(1),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_vuelo_cancelado(self):
        self.vuelo.estado = Vuelo.Estado.CANCELADO
        self.vuelo.save()

        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 1,
            'pasajeros': pasajeros(1),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rechaza_vuelo_que_ya_salio(self):
        self.vuelo.fecha_operacion = HOY - dt.timedelta(days=1)
        self.vuelo.fecha_llegada = HOY - dt.timedelta(days=1)
        self.vuelo.save()

        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 1,
            'pasajeros': pasajeros(1),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_usuario_sin_autenticar_401(self):
        self.client.logout()
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 1,
            'pasajeros': pasajeros(1),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rol_no_pasajero_403(self):
        self.client.force_authenticate(self.admin)
        url = '/api/reservas/'
        payload = {
            'vuelo_id': str(self.vuelo.id),
            'clase': 'economy',
            'cantidad_pasajes': 1,
            'pasajeros': pasajeros(1),
        }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_listar_solo_reservas_propias(self):
        # Crear reserva para pasajero
        res_propia = self.client.post(
            '/api/reservas/',
            {'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 1, 'pasajeros': pasajeros(1)},
            format='json',
        ).data['id']

        # Cambiar a otro pasajero y crear otra
        self.client.force_authenticate(self.otro_pasajero)
        res_otra = self.client.post(
            '/api/reservas/',
            {'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 2, 'pasajeros': pasajeros(2)},
            format='json',
        ).data['id']

        # El otro pasajero solo ve la suya
        res = self.client.get('/api/reservas/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [r['id'] for r in res.data]
        self.assertIn(res_otra, ids)
        self.assertNotIn(res_propia, ids)

    def test_detalle_reserva_propia_y_ajena(self):
        res_propia = self.client.post(
            '/api/reservas/',
            {'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 1, 'pasajeros': pasajeros(1)},
            format='json',
        ).data['id']

        # El dueño puede verla
        res = self.client.get(f'/api/reservas/{res_propia}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['id'], res_propia)

        # Otro pasajero recibe 404
        self.client.force_authenticate(self.otro_pasajero)
        res_ajena = self.client.get(f'/api/reservas/{res_propia}/')
        self.assertEqual(res_ajena.status_code, status.HTTP_404_NOT_FOUND)

    def test_reserva_creada_se_puede_pagar_con_tarjeta(self):
        # Flujo integral US06 + US07 + US08:
        # 1. Reservar (US06)
        res = self.client.post(
            '/api/reservas/',
            {'vuelo_id': str(self.vuelo.id), 'clase': 'economy', 'cantidad_pasajes': 2, 'pasajeros': pasajeros(2)},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reserva_id = res.data['id']

        # 2. Pagar la reserva creada con tarjeta aprobada (US07 / US08)
        pago_res = self.client.post(
            '/api/pagos/tarjeta/',
            {
                'reserva_id': reserva_id,
                'numero': '4242424242424242',
                'titular': 'Juan Pérez',
                'vencimiento': '12/30',
                'cvv': '123',
            },
            format='json',
        )
        self.assertEqual(pago_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pago_res.data['estado'], 'aprobado')

        # 3. Verificar que la reserva pasa a 'pagada' y se descontaron los asientos
        reserva = Reserva.objects.get(id=reserva_id)
        self.assertEqual(reserva.estado, Reserva.Estado.PAGADA)
        self.vuelo.refresh_from_db()
        self.assertEqual(self.vuelo.asientos_disponibles_economy, 8)  # 10 - 2 = 8


class TicketElectronicoTests(ReservasBaseTestCase):
    """Pruebas de la US09: Generar ticket electrónico."""

    def crear_reserva_con_pasaje(self):
        res = self.client.post(
            '/api/reservas/',
            {
                'vuelo_id': str(self.vuelo.id),
                'clase': 'economy',
                'cantidad_pasajes': 2,
                'pasajeros': [
                    {'nombre_pasajero': 'Juan', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '12345678'},
                    {'nombre_pasajero': 'Lucía', 'apellido_pasajero': 'Pérez', 'dni_pasajero': '87654321'},
                ],
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reserva_id = res.data['id']
        pasajes = res.data['pasajes']
        p1 = next(p for p in pasajes if p['nombre_pasajero'] == 'Juan')
        p2 = next(p for p in pasajes if p['nombre_pasajero'] == 'Lucía')
        return reserva_id, p1['codigo_pasaje'], p2['codigo_pasaje']

    def pagar_reserva(self, reserva_id, tarjeta_aprobada=True):
        numero = '4242424242424242' if tarjeta_aprobada else '4000000000000002'
        return self.client.post(
            '/api/pagos/tarjeta/',
            {
                'reserva_id': reserva_id,
                'numero': numero,
                'titular': 'Juan Pérez',
                'vencimiento': '12/30',
                'cvv': '123',
            },
            format='json',
        )

    def test_ticket_no_se_genera_si_compra_no_confirmada(self):
        # 1. Reserva recién creada (pendiente)
        _, codigo, _ = self.crear_reserva_con_pasaje()

        # Intentar descargar el PDF da 400
        res_pdf = self.client.get(f'/api/pasajes/{codigo}/pdf/')
        self.assertEqual(res_pdf.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirmadas', res_pdf.data['detail'].lower())

        # Intentar ver el detalle JSON da 400
        res_json = self.client.get(f'/api/pasajes/{codigo}/')
        self.assertEqual(res_json.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_no_se_genera_ante_pago_rechazado(self):
        reserva_id, codigo, _ = self.crear_reserva_con_pasaje()

        # Pagar con tarjeta que rechaza
        pago_res = self.pagar_reserva(reserva_id, tarjeta_aprobada=False)
        self.assertEqual(pago_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pago_res.data['estado'], 'rechazado')

        # El ticket no se genera
        res = self.client.get(f'/api/pasajes/{codigo}/pdf/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res_detalle = self.client.get(f'/api/pasajes/{codigo}/')
        self.assertEqual(res_detalle.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ticket_se_genera_y_descarga_tras_pago_aprobado(self):
        reserva_id, codigo, _ = self.crear_reserva_con_pasaje()

        # Pagar con tarjeta aprobada
        pago_res = self.pagar_reserva(reserva_id, tarjeta_aprobada=True)
        self.assertEqual(pago_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pago_res.data['estado'], 'aprobado')

        # Descargar ticket en PDF
        res = self.client.get(f'/api/pasajes/{codigo}/pdf/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(f'attachment; filename="ticket-{codigo}.pdf"', res.get('Content-Disposition', '') or res.headers.get('Content-Disposition', ''))

        # Es un PDF real
        contenido = res.content
        self.assertTrue(contenido.startswith(b'%PDF'), 'El archivo generado debe ser un PDF válido')
        self.assertGreater(len(contenido), 500)

    def test_visualizar_ticket_detalle_json(self):
        reserva_id, codigo, _ = self.crear_reserva_con_pasaje()
        self.pagar_reserva(reserva_id, tarjeta_aprobada=True)

        res = self.client.get(f'/api/pasajes/{codigo}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.data

        # Criterio: incluye pasajero, vuelo, fecha, horario, origen, destino y clase
        self.assertEqual(data['codigo_pasaje'], codigo)
        self.assertEqual(data['nombre_pasajero'], 'Juan')
        self.assertEqual(data['apellido_pasajero'], 'Pérez')
        self.assertEqual(data['dni_pasajero'], '12345678')
        self.assertEqual(data['clase'], 'economy')
        self.assertEqual(data['estado_compra'], 'pagada')
        self.assertEqual(data['vuelo']['numero_vuelo'], 'FA 1001')
        self.assertEqual(data['vuelo']['origen'], 'AEP')
        self.assertEqual(data['vuelo']['destino'], 'COR')
        self.assertEqual(data['vuelo']['fecha_operacion'], str(self.vuelo.fecha_operacion))
        self.assertEqual(data['vuelo']['fecha_llegada'], str(self.vuelo.fecha_llegada))
        self.assertEqual(data['vuelo']['hora_partida'], '10:00:00')
        self.assertEqual(data['vuelo']['hora_llegada'], '11:30:00')
        self.assertEqual(data['ticket_pdf_url'], f'/api/pasajes/{codigo}/pdf/')

    def test_ticket_ajeno_da_404(self):
        reserva_id, codigo, _ = self.crear_reserva_con_pasaje()
        self.pagar_reserva(reserva_id, tarjeta_aprobada=True)

        # Otro pasajero no puede ver ni descargar el ticket
        self.client.force_authenticate(self.otro_pasajero)

        res_json = self.client.get(f'/api/pasajes/{codigo}/')
        self.assertEqual(res_json.status_code, status.HTTP_404_NOT_FOUND)

        res_pdf = self.client.get(f'/api/pasajes/{codigo}/pdf/')
        self.assertEqual(res_pdf.status_code, status.HTTP_404_NOT_FOUND)

    def test_ticket_sin_autenticar_da_401(self):
        reserva_id, codigo, _ = self.crear_reserva_con_pasaje()
        self.pagar_reserva(reserva_id, tarjeta_aprobada=True)

        self.client.logout()

        res_json = self.client.get(f'/api/pasajes/{codigo}/')
        self.assertEqual(res_json.status_code, status.HTTP_401_UNAUTHORIZED)

        res_pdf = self.client.get(f'/api/pasajes/{codigo}/pdf/')
        self.assertEqual(res_pdf.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cada_ticket_se_identifica_individualmente(self):
        reserva_id, codigo_1, codigo_2 = self.crear_reserva_con_pasaje()
        self.pagar_reserva(reserva_id, tarjeta_aprobada=True)

        self.assertNotEqual(codigo_1, codigo_2)

        # Pasaje 1: Juan
        t1 = self.client.get(f'/api/pasajes/{codigo_1}/').data
        self.assertEqual(t1['nombre_pasajero'], 'Juan')

        # Pasaje 2: Lucía
        t2 = self.client.get(f'/api/pasajes/{codigo_2}/').data
        self.assertEqual(t2['nombre_pasajero'], 'Lucía')
