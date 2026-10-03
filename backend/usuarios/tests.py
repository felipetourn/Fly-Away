from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test import Client, TestCase, override_settings
from rest_framework.test import APIClient

Usuario = get_user_model()


class UsuarioTests(TestCase):
    def test_create_user_hashea_la_clave_y_es_pasajero(self):
        u = Usuario.objects.create_user('ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez')
        self.assertEqual(u.rol, Usuario.Rol.PASAJERO)
        self.assertNotEqual(u.password, 'clave-segura-1')
        self.assertTrue(u.check_password('clave-segura-1'))
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.has_perm('vuelos.add_vuelo'))

    def test_superusuario_es_administrador_y_entra_al_admin(self):
        u = Usuario.objects.create_superuser('admin@mail.com', 'clave-segura-1', nombre='Ada', apellido='Admin')
        self.assertEqual(u.rol, Usuario.Rol.ADMINISTRADOR)
        self.assertTrue(u.is_staff)
        self.assertTrue(u.has_perm('vuelos.add_vuelo'))
        self.assertTrue(u.has_module_perms('vuelos'))

    def test_login_rechaza_usuario_inexistente_y_clave_incorrecta(self):
        Usuario.objects.create_user(
            'ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez'
        )
        cliente = APIClient()
        inexistente = cliente.post(
            '/api/auth/token/',
            {'email': 'nadie@mail.com', 'password': 'clave-segura-1'},
            format='json',
        )
        incorrecta = cliente.post(
            '/api/auth/token/',
            {'email': 'ana@mail.com', 'password': 'otra-clave'},
            format='json',
        )
        self.assertEqual(inexistente.status_code, 401)
        self.assertEqual(incorrecta.status_code, 401)
        self.assertEqual(inexistente.data, incorrecta.data)

    def test_inactivo_no_esta_activo(self):
        u = Usuario.objects.create_user('ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez', activo=False)
        self.assertFalse(u.is_active)

    def test_tabla_y_columnas_del_dbml(self):
        self.assertEqual(Usuario._meta.db_table, 'usuarios')
        self.assertEqual(Usuario._meta.get_field('password').column, 'password_hash')
        with self.assertRaises(FieldDoesNotExist):
            Usuario._meta.get_field('last_login')

    def test_login_jwt_con_email(self):
        Usuario.objects.create_user('ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez')
        r = APIClient().post('/api/auth/token/', {'email': 'ana@mail.com', 'password': 'clave-segura-1'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        renovacion = APIClient().post(
            '/api/auth/token/refresh/',
            {'refresh': r.data['refresh']},
            format='json',
        )
        self.assertEqual(renovacion.status_code, 200)
        self.assertIn('access', renovacion.data)

    def test_registro_crea_solo_pasajeros_y_hashea_clave(self):
        r = APIClient().post(
            '/api/auth/registro/',
            {
                'email': ' ANA@MAIL.COM ',
                'nombre': 'Ana',
                'apellido': 'Pérez',
                'password': 'Vuela-mate-83-Zebra',
                'rol': 'administrador',
            },
            format='json',
        )
        self.assertEqual(r.status_code, 201, r.data)
        u = Usuario.objects.get(email='ana@mail.com')
        self.assertEqual(u.rol, Usuario.Rol.PASAJERO)
        self.assertNotEqual(u.password, 'Vuela-mate-83-Zebra')
        self.assertTrue(u.check_password('Vuela-mate-83-Zebra'))
        self.assertNotIn('password', r.data)
        token = APIClient().post(
            '/api/auth/token/',
            {'email': 'ana@mail.com', 'password': 'Vuela-mate-83-Zebra'},
            format='json',
        )
        self.assertEqual(token.status_code, 200, token.data)
        self.assertIn('access', token.data)

    def test_registro_rechaza_email_existente_sin_distinguir_mayusculas(self):
        Usuario.objects.create_user('ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez')
        r = APIClient().post(
            '/api/auth/registro/',
            {
                'email': 'ANA@mail.com',
                'nombre': 'Ana',
                'apellido': 'Pérez',
                'password': 'Vuela-mate-83-Zebra',
            },
            format='json',
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Usuario.objects.filter(email__iexact='ANA@mail.com').count(), 1)

    def test_registro_rechaza_contraseña_debil(self):
        r = APIClient().post(
            '/api/auth/registro/',
            {
                'email': 'ana@mail.com',
                'nombre': 'Ana',
                'apellido': 'Pérez',
                'password': '123',
            },
            format='json',
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Usuario.objects.filter(email='ana@mail.com').exists())

    def test_usuario_actual_requiere_jwt_y_no_expone_la_clave(self):
        usuario = Usuario.objects.create_user(
            'ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez'
        )
        cliente = APIClient()
        self.assertEqual(cliente.get('/api/auth/yo/').status_code, 401)
        tokens = cliente.post(
            '/api/auth/token/',
            {'email': usuario.email, 'password': 'clave-segura-1'},
            format='json',
        )
        cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.data['access']}")
        actual = cliente.get('/api/auth/yo/')
        self.assertEqual(actual.status_code, 200)
        self.assertEqual(actual.data['id'], str(usuario.id))
        self.assertEqual(actual.data['rol'], Usuario.Rol.PASAJERO)
        self.assertNotIn('password', actual.data)

    def test_usuario_inactivo_no_puede_obtener_token(self):
        Usuario.objects.create_user(
            'ana@mail.com', 'clave-segura-1', nombre='Ana', apellido='Pérez', activo=False
        )
        r = APIClient().post(
            '/api/auth/token/',
            {'email': 'ana@mail.com', 'password': 'clave-segura-1'},
            format='json',
        )
        self.assertEqual(r.status_code, 401)

    def test_empleado_se_puede_persistir_con_su_rol(self):
        usuario = Usuario.objects.create_user(
            'empleado@mail.com',
            'clave-segura-1',
            nombre='Eva',
            apellido='Empleada',
            rol=Usuario.Rol.EMPLEADO_MOSTRADOR,
        )
        usuario.refresh_from_db()
        self.assertEqual(usuario.rol, Usuario.Rol.EMPLEADO_MOSTRADOR)
        self.assertFalse(usuario.is_staff)

    def test_admin_crea_empleado_y_admin_con_claves_hasheadas_que_autentican(self):
        admin = Usuario.objects.create_superuser(
            'admin@mail.com', 'clave-admin-segura', nombre='Ada', apellido='Admin'
        )
        cliente = Client()
        cliente.force_login(admin)

        cuentas = (
            ('empleado@mail.com', 'Eva', 'Empleada', Usuario.Rol.EMPLEADO_MOSTRADOR, 'Senda-Azul-91-Mapa'),
            ('otro-admin@mail.com', 'Ariel', 'Admin', Usuario.Rol.ADMINISTRADOR, 'Rumbo-Norte-47-Luz'),
        )
        for email, nombre, apellido, rol, password in cuentas:
            respuesta = cliente.post(
                '/admin/usuarios/usuario/add/',
                {
                    'email': email,
                    'nombre': nombre,
                    'apellido': apellido,
                    'rol': rol,
                    'activo': 'on',
                    'password': password,
                },
            )
            self.assertEqual(respuesta.status_code, 302)

            usuario = Usuario.objects.get(email=email)
            self.assertEqual(usuario.rol, rol)
            self.assertNotEqual(usuario.password, password)
            self.assertTrue(usuario.check_password(password))
            token = APIClient().post(
                '/api/auth/token/',
                {'email': email, 'password': password},
                format='json',
            )
            self.assertEqual(token.status_code, 200, token.data)
            self.assertIn('access', token.data)

    @override_settings(
        STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }
    )
    def test_solo_administrador_accede_al_admin_de_django(self):
        administrador = Usuario.objects.create_superuser(
            'admin@mail.com', 'clave-admin-segura', nombre='Ada', apellido='Admin'
        )
        empleado = Usuario.objects.create_user(
            'empleado@mail.com',
            'clave-empleado-segura',
            nombre='Eva',
            apellido='Empleada',
            rol=Usuario.Rol.EMPLEADO_MOSTRADOR,
        )
        pasajero = Usuario.objects.create_user(
            'ana@mail.com', 'clave-pasajero-segura', nombre='Ana', apellido='Pérez'
        )

        self.assertEqual(Client().get('/admin/').status_code, 302)
        for usuario in (empleado, pasajero):
            cliente = Client()
            cliente.force_login(usuario)
            self.assertEqual(cliente.get('/admin/').status_code, 302)

        cliente = Client()
        cliente.force_login(administrador)
        self.assertEqual(cliente.get('/admin/').status_code, 200)
