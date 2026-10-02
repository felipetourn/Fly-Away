from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.test import TestCase
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
