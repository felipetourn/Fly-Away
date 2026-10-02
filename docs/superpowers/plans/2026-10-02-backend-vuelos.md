# Backend de vuelos — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** que la búsqueda, el detalle y la elección de vuelos del front usen la base de datos real a través de la API de Django, en lugar del mock.

**Arquitectura:**
- La app `usuarios` reemplaza a `accounts`, con el modelo del DBML.
- La app nueva `vuelos` tiene los modelos `Aeropuerto`, `Avion` y `Vuelo`, tres vistas de DRF (aeropuertos, buscar, detalle) y un comando `seed` que carga datos de ejemplo.
- En el front solo cambia `src/lib/` (los cuerpos de `getAeropuertos`, `buscarVuelos` y `getVuelo`) y el buscador, que suma un rango de fechas para la vuelta y pierde el límite de 14 días.

**Tech stack:** Django 5.2, DRF 3.15+, SimpleJWT, React 19 + TS, Node `assert` (`npm run check`).

**Spec:** [docs/superpowers/specs/2026-10-02-backend-vuelos-design.md](../specs/2026-10-02-backend-vuelos-design.md)

## Restricciones globales

- **Commits sin coautor:** solo Felipe como autor. Nunca agregar `Co-Authored-By` ni firmas de Claude, ni en commits ni en PRs.
- **Rama:** `feat/backend-vuelos`. Ya existe, sale de `main` y tiene la spec commiteada.
- **Idioma:** español en código de dominio, mensajes, commits y docs. Nombres de tablas y campos: los de `docs/modelo.dbml`.
- **Sin dependencias nuevas:** ni en `requirements.txt` ni en `package.json`.
- **Front:** se llama a la API solo con `api()` de `src/lib/api.ts`. `VITE_API_URL` ya incluye `/api` (`http://localhost:8000/api`).
- **No tocar la sesión** (`auth.ts`, `sesion.tsx`, `Login.tsx`): es de otra US.
- **Comandos del backend:** desde `backend/`, con `.venv/Scripts/python manage.py …`. Los del front, desde `frontend/`.
- **Mensajes de error 400:** el texto exacto de la tabla de la spec, en el formato `{"param": ["mensaje"]}`.

## Foco de revisión

Casos que la spec implica pero que ninguna tarea cubriría por sí sola. Cada uno tiene su test en la tarea indicada:

1. **Parámetros vacíos en la URL** (`?hasta=&precio_min=`): cuentan como no enviados y la respuesta es 200, no 400. Va en la Tarea 4.
2. **"Hoy" de noche:** a las 23:30 de Buenos Aires en UTC ya es el día siguiente, y aun así "hoy" tiene que ser la fecha de Buenos Aires. La búsqueda acepta `desde` = hoy y ofrece el vuelo de las 23:45. Va en la Tarea 4.
3. **IATA en minúsculas** (`origen=bhi`): se acepta igual que `BHI`. Va en la Tarea 4.
4. **Id de detalle que no es UUID** (`/api/vuelos/abc/`): devuelve 404 en JSON, ni 500 ni HTML. Va en la Tarea 3.
5. **Vuelta en un rango que se superpone con la ida:** no se ofrece una vuelta que sale el día anterior o antes de que aterrice la ida. Va en la Tarea 7.

---

## Mapa de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `backend/accounts/` | Borrar | User provisorio |
| `backend/usuarios/{__init__,apps,models,admin,tests}.py`, `migrations/` | Crear | Modelo `Usuario` (tabla `usuarios`) |
| `backend/vuelos/{__init__,apps,models,admin,serializers,views,urls,tests}.py`, `migrations/` | Crear | Dominio de vuelos y API |
| `backend/vuelos/management/commands/seed.py` (+ `__init__.py` en `management/` y `commands/`) | Crear | Datos de ejemplo |
| `backend/config/settings.py` | Modificar | `INSTALLED_APPS`, `AUTH_USER_MODEL` |
| `backend/config/urls.py` | Modificar | `include('vuelos.urls')` |
| `backend/build.sh` | Modificar | Correr `seed` en el deploy |
| `frontend/src/lib/busqueda.ts` | Modificar | Sin límite de 14 días, `vueltaHasta` |
| `frontend/src/components/BuscadorVuelos.tsx` | Modificar | Cuatro fechas en ida y vuelta |
| `frontend/src/pages/Vuelos.tsx` | Modificar | La búsqueda de la vuelta usa el rango |
| `frontend/src/lib/vuelos.ts` | Modificar | Llama a la API, se borra el mock |
| `frontend/scripts/check.ts` | Modificar | Chequeos sin el mock |
| `docs/arquitectura.md`, `docs/memoria.md` | Modificar | Documentación |

---

### Tarea 1: Modelo `usuarios` (reemplaza a `accounts`)

**Archivos:**
- Borrar: `backend/accounts/` (completa), `backend/db.sqlite3` (no está versionada)
- Crear: `backend/usuarios/` (`startapp`), `backend/usuarios/models.py`, `backend/usuarios/admin.py`, `backend/usuarios/tests.py`
- Modificar: `backend/config/settings.py:31` (`'accounts'` → `'usuarios'`), `backend/config/settings.py:73`

**Interfaces:**
- Produce: `usuarios.models.Usuario` (vía `get_user_model()`), con `Usuario.Rol.{ADMINISTRADOR, EMPLEADO_MOSTRADOR, PASAJERO}`, `Usuario.objects.create_user(email, password, **campos)` y `Usuario.objects.create_superuser(email, password, **campos)`. Campos: `id` (UUID), `email`, `nombre`, `apellido`, `rol`, `activo`, `creado_en`, `actualizado_en`.

- [ ] **Paso 1: Borrar `accounts` y crear la app**

```bash
cd backend
git rm -r -q accounts
rm -rf accounts db.sqlite3
.venv/Scripts/python manage.py startapp usuarios
```

En `backend/config/settings.py`, cambiar `'accounts',` por `'usuarios',` en `INSTALLED_APPS` y `AUTH_USER_MODEL = 'accounts.User'` por:

```python
AUTH_USER_MODEL = 'usuarios.Usuario'
```

Borrar `usuarios/views.py`, que no se usa.

- [ ] **Paso 2: Escribir los tests que fallan** — `backend/usuarios/tests.py`

```python
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
```

- [ ] **Paso 3: Correr los tests y verificar que fallan**

Correr: `.venv/Scripts/python manage.py test usuarios`
Esperado: ERROR. Django no encuentra `usuarios.Usuario` (`AUTH_USER_MODEL refers to model 'usuarios.Usuario' that has not been installed`).

- [ ] **Paso 4: Implementar el modelo** — `backend/usuarios/models.py`

```python
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **campos):
        if not email:
            raise ValueError('El email es obligatorio')
        usuario = self.model(email=self.normalize_email(email), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, password=None, **campos):
        campos['rol'] = Usuario.Rol.ADMINISTRADOR
        return self.create_user(email, password, **campos)


class Usuario(AbstractBaseUser):
    """Tabla `usuarios` del DBML. Sin PermissionsMixin: el rol define el acceso."""

    class Rol(models.TextChoices):
        ADMINISTRADOR = 'administrador', 'Administrador'
        EMPLEADO_MOSTRADOR = 'empleado_mostrador', 'Empleado de mostrador'
        PASAJERO = 'pasajero', 'Pasajero'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, db_column='password_hash')
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.PASAJERO)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    last_login = None  # no está en el DBML

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellido']

    class Meta:
        db_table = 'usuarios'

    def __str__(self):
        return self.email

    @property
    def is_active(self):
        return self.activo

    # El admin de Django es una herramienta interna: solo para administradores.
    @property
    def is_staff(self):
        return self.activo and self.rol == self.Rol.ADMINISTRADOR

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
```

`backend/usuarios/admin.py`:

```python
from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    # ponytail: sin alta/cambio de contraseña desde el admin; eso llega con la US de login/registro.
    fields = ('email', 'nombre', 'apellido', 'rol', 'activo')
    list_display = ('email', 'nombre', 'apellido', 'rol', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('email', 'nombre', 'apellido')
```

- [ ] **Paso 5: Crear la migración y correr los tests**

```bash
.venv/Scripts/python manage.py makemigrations usuarios
.venv/Scripts/python manage.py test usuarios
.venv/Scripts/python manage.py check
```

Esperado: se crea `usuarios/migrations/0001_initial.py`, pasan 5 tests y `check` sale sin issues.

- [ ] **Paso 6: Commit**

```bash
git add -A backend/usuarios backend/config/settings.py backend/accounts
git commit -m "feat(backend): modelo usuarios del DBML reemplaza a accounts"
```

---

### Tarea 2: Modelos de vuelos (aeropuertos, aviones, vuelos)

**Archivos:**
- Crear: `backend/vuelos/` (`startapp`), `backend/vuelos/models.py`, `backend/vuelos/admin.py`, `backend/vuelos/tests.py`
- Modificar: `backend/config/settings.py` (sumar `'vuelos',` a `INSTALLED_APPS`, después de `'usuarios',`)

**Interfaces:**
- Consume: `settings.AUTH_USER_MODEL` (Tarea 1).
- Produce:
  - `vuelos.models.Aeropuerto(codigo_iata, nombre, ciudad, pais)`.
  - `Avion(matricula, modelo, capacidad_economy, capacidad_primera)`.
  - `Vuelo` con `numero_vuelo`, `avion`, `aeropuerto_origen`, `aeropuerto_destino`, `fecha_operacion`, `hora_partida`, `hora_llegada`, `precio_economy`, `precio_primera`, `asientos_disponibles_economy`, `asientos_disponibles_primera`, `estado`, `creado_por`, `creado_en` y `actualizado_en`, más `Vuelo.Estado.{ACTIVO, CANCELADO}`.
  - En `vuelos/tests.py`, la clase base `Datos(APITestCase)`, con `self.admin`, `self.bhi`, `self.aep`, `self.eze`, `self.cor` y `self.avion`, el helper `self.vuelo(numero='FA 1000', origen=None, destino=None, fecha=None, partida='15:00', **cambios) -> Vuelo` y las constantes `AHORA`/`HOY` (`timezone.now` se parchea a `AHORA` en cada test).

- [ ] **Paso 1: Crear la app**

```bash
.venv/Scripts/python manage.py startapp vuelos
rm vuelos/views.py
```

Sumar `'vuelos',` a `INSTALLED_APPS` en `backend/config/settings.py`.

- [ ] **Paso 2: Escribir los tests que fallan** — `backend/vuelos/tests.py`

```python
import datetime as dt
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
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
        sale = dt.time.fromisoformat(partida)
        datos = dict(
            numero_vuelo=numero,
            avion=self.avion,
            aeropuerto_origen=origen or self.bhi,
            aeropuerto_destino=destino or self.aep,
            fecha_operacion=fecha or HOY + dt.timedelta(days=1),
            hora_partida=sale,
            hora_llegada=(dt.datetime.combine(HOY, sale) + dt.timedelta(hours=1)).time(),
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
```

- [ ] **Paso 3: Correr los tests y verificar que fallan**

Correr: `.venv/Scripts/python manage.py test vuelos`
Esperado: ERROR con `ImportError: cannot import name 'Aeropuerto' from 'vuelos.models'`.

- [ ] **Paso 4: Implementar los modelos** — `backend/vuelos/models.py`

```python
import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Aeropuerto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo_iata = models.CharField(max_length=3, unique=True)
    nombre = models.CharField(max_length=150)
    ciudad = models.CharField(max_length=100)
    pais = models.CharField(max_length=100)

    class Meta:
        db_table = 'aeropuertos'
        ordering = ['ciudad', 'codigo_iata']

    def __str__(self):
        return f'{self.ciudad} ({self.codigo_iata})'


class Avion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matricula = models.CharField(max_length=10, unique=True)
    modelo = models.CharField(max_length=100)
    capacidad_economy = models.IntegerField()
    capacidad_primera = models.IntegerField()

    class Meta:
        db_table = 'aviones'
        verbose_name_plural = 'aviones'

    def __str__(self):
        return f'{self.matricula} ({self.modelo})'


class Vuelo(models.Model):
    """Una fila por vuelo real en una fecha; independiente de las demás (ver modelo.dbml)."""

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        CANCELADO = 'cancelado', 'Cancelado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_vuelo = models.CharField(max_length=10)
    avion = models.ForeignKey(Avion, on_delete=models.PROTECT, related_name='vuelos')
    aeropuerto_origen = models.ForeignKey(Aeropuerto, on_delete=models.PROTECT, related_name='vuelos_salida')
    aeropuerto_destino = models.ForeignKey(Aeropuerto, on_delete=models.PROTECT, related_name='vuelos_llegada')
    fecha_operacion = models.DateField()
    hora_partida = models.TimeField()
    hora_llegada = models.TimeField()
    precio_economy = models.DecimalField(max_digits=10, decimal_places=2)
    precio_primera = models.DecimalField(max_digits=10, decimal_places=2)
    asientos_disponibles_economy = models.IntegerField()
    asientos_disponibles_primera = models.IntegerField()
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ACTIVO)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='vuelos_creados')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vuelos'
        ordering = ['fecha_operacion', 'hora_partida']
        constraints = [
            models.UniqueConstraint(fields=['numero_vuelo', 'fecha_operacion'], name='vuelo_numero_fecha_unico'),
            models.CheckConstraint(
                condition=~Q(aeropuerto_origen=F('aeropuerto_destino')), name='vuelo_origen_distinto_destino'
            ),
            models.CheckConstraint(condition=Q(asientos_disponibles_economy__gte=0), name='vuelo_asientos_economy_no_negativos'),
            models.CheckConstraint(condition=Q(asientos_disponibles_primera__gte=0), name='vuelo_asientos_primera_no_negativos'),
        ]

    def __str__(self):
        return f'{self.numero_vuelo} {self.fecha_operacion}'
```

`backend/vuelos/admin.py`:

```python
from django.contrib import admin

from .models import Aeropuerto, Avion, Vuelo


@admin.register(Aeropuerto)
class AeropuertoAdmin(admin.ModelAdmin):
    list_display = ('codigo_iata', 'ciudad', 'nombre', 'pais')
    search_fields = ('codigo_iata', 'ciudad', 'nombre')


@admin.register(Avion)
class AvionAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'modelo', 'capacidad_economy', 'capacidad_primera')


@admin.register(Vuelo)
class VueloAdmin(admin.ModelAdmin):
    list_display = ('numero_vuelo', 'fecha_operacion', 'hora_partida', 'aeropuerto_origen', 'aeropuerto_destino', 'estado')
    list_filter = ('estado', 'aeropuerto_origen', 'aeropuerto_destino')
    date_hierarchy = 'fecha_operacion'
    search_fields = ('numero_vuelo',)
```

- [ ] **Paso 5: Crear la migración y correr los tests**

```bash
.venv/Scripts/python manage.py makemigrations vuelos
.venv/Scripts/python manage.py test
```

Esperado: se crea `vuelos/migrations/0001_initial.py` y pasan los 9 tests (5 de usuarios y 4 de vuelos).

- [ ] **Paso 6: Commit**

```bash
git add backend/vuelos backend/config/settings.py
git commit -m "feat(backend): modelos de aeropuertos, aviones y vuelos con constraints del DBML"
```

---

### Tarea 3: API de aeropuertos y detalle de vuelo

**Archivos:**
- Crear: `backend/vuelos/serializers.py`, `backend/vuelos/views.py`, `backend/vuelos/urls.py`
- Modificar: `backend/config/urls.py`, `backend/vuelos/tests.py` (agregar al final)

**Interfaces:**
- Consume: modelos de la Tarea 2 y la base `Datos` de los tests.
- Produce:
  - `AeropuertoSerializer`, `AvionSerializer`, `VueloSerializer` (campos `VUELO_CAMPOS`) y `VueloDetalleSerializer` (agrega `avion`).
  - Rutas `api/aeropuertos/` y `api/vuelos/<str:pk>/`.
  - En `vuelos/urls.py`, la ruta `vuelos/buscar/` va **antes** que `vuelos/<str:pk>/`. Esa ruta la completa la Tarea 4.

- [ ] **Paso 1: Escribir los tests que fallan** (agregar al final de `backend/vuelos/tests.py`)

```python
import uuid  # sumar arriba, junto a los otros imports

VUELO_CAMPOS = {
    'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'hora_partida', 'hora_llegada',
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
```

- [ ] **Paso 2: Correr los tests y verificar que fallan**

Correr: `.venv/Scripts/python manage.py test vuelos.tests.AeropuertosTests vuelos.tests.DetalleTests`
Esperado: FAIL con `404 != 200` (las rutas todavía no existen).

- [ ] **Paso 3: Implementar** — `backend/vuelos/serializers.py`

```python
from rest_framework import serializers

from .models import Aeropuerto, Avion, Vuelo


class AeropuertoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aeropuerto
        fields = ['id', 'codigo_iata', 'nombre', 'ciudad', 'pais']


class AvionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avion
        fields = ['matricula', 'modelo']


class VueloSerializer(serializers.ModelSerializer):
    """Forma de `Vuelo` en frontend/src/lib/vuelos.ts: origen y destino anidados."""

    origen = AeropuertoSerializer(source='aeropuerto_origen')
    destino = AeropuertoSerializer(source='aeropuerto_destino')

    class Meta:
        model = Vuelo
        fields = [
            'id', 'numero_vuelo', 'origen', 'destino', 'fecha_operacion', 'hora_partida', 'hora_llegada',
            'precio_economy', 'precio_primera', 'asientos_disponibles_economy', 'asientos_disponibles_primera',
            'estado',
        ]


class VueloDetalleSerializer(VueloSerializer):
    avion = AvionSerializer()

    class Meta(VueloSerializer.Meta):
        fields = VueloSerializer.Meta.fields + ['avion']
```

`backend/vuelos/views.py`:

```python
from rest_framework import generics

from .models import Aeropuerto, Vuelo
from .serializers import AeropuertoSerializer, VueloDetalleSerializer


class AeropuertosView(generics.ListAPIView):
    queryset = Aeropuerto.objects.all()
    serializer_class = AeropuertoSerializer


class VueloDetalleView(generics.RetrieveAPIView):
    """Incluye cancelados: el detalle informa la cancelación. Un id que no es UUID da 404 (no 500)."""

    queryset = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino')
    serializer_class = VueloDetalleSerializer
```

`backend/vuelos/urls.py`:

```python
from django.urls import path

from . import views

urlpatterns = [
    path('aeropuertos/', views.AeropuertosView.as_view()),
    # str y no uuid: un id inválido llega a DRF y responde 404 en JSON.
    path('vuelos/<str:pk>/', views.VueloDetalleView.as_view()),
]
```

En `backend/config/urls.py`, cambiar `from django.urls import path` por `from django.urls import include, path` y agregar al final de `urlpatterns`:

```python
    path('api/', include('vuelos.urls')),
```

- [ ] **Paso 4: Correr los tests y verificar que pasan**

Correr: `.venv/Scripts/python manage.py test vuelos`
Esperado: todos PASS.

- [ ] **Paso 5: Commit**

```bash
git add backend/vuelos backend/config/urls.py
git commit -m "feat(backend): endpoints de aeropuertos y detalle de vuelo"
```

---

### Tarea 4: `GET /api/vuelos/buscar/` (filtros y errores 400)

**Archivos:**
- Modificar: `backend/vuelos/serializers.py`, `backend/vuelos/views.py`, `backend/vuelos/urls.py`, `backend/vuelos/tests.py` (agregar al final)

**Interfaces:**
- Consume: `VueloSerializer` (Tarea 3), `Datos`, `VUELO_CAMPOS`, `AHORA` y `HOY` (tests).
- Produce:
  - `BusquedaSerializer`, cuyos `validated_data` tienen `origen`/`destino` (`Aeropuerto`, opcionales), `desde` y `hasta` (`date`, `hasta` opcional), `pasajeros` (`int`), `clase` (`str`) y `precio_min`/`precio_max` (`Decimal`, opcionales).
  - `BuscarVuelosView`.

- [ ] **Paso 1: Escribir los tests que fallan** (agregar al final de `backend/vuelos/tests.py`)

```python
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
        self.vuelo('FA 2', fecha=HOY, partida='23:45', hora_llegada=dt.time(23, 59))
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
```

- [ ] **Paso 2: Correr los tests y verificar que fallan**

Correr: `.venv/Scripts/python manage.py test vuelos.tests.BuscarTests vuelos.tests.ErroresBusquedaTests`
Esperado: FAIL. `buscar/` hoy cae en el detalle con `pk='buscar'` y responde 404.

- [ ] **Paso 3: Implementar el serializer de la búsqueda** (agregar al final de `backend/vuelos/serializers.py`; sumar `from django.utils import timezone` arriba)

```python
FECHA_INVALIDA = 'Indicá una fecha válida (AAAA-MM-DD).'
MONTO_INVALIDO = 'Ingresá un monto válido.'
PASAJEROS_INVALIDO = 'Tienen que ser entre 1 y 9 pasajeros.'
MAX_PASAJEROS = 9


def _errores(mensaje, *claves):
    return {clave: mensaje for clave in claves}


class BusquedaSerializer(serializers.Serializer):
    """Parámetros de GET /vuelos/buscar/. Los mensajes son los mismos que muestra el front."""

    origen = serializers.CharField(required=False)
    destino = serializers.CharField(required=False)
    desde = serializers.DateField(error_messages=_errores(FECHA_INVALIDA, 'required', 'invalid', 'null'))
    hasta = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid', 'null'))
    pasajeros = serializers.IntegerField(
        default=1,
        min_value=1,
        max_value=MAX_PASAJEROS,
        error_messages=_errores(PASAJEROS_INVALIDO, 'invalid', 'min_value', 'max_value', 'max_string_length'),
    )
    clase = serializers.ChoiceField(
        choices=['economy', 'primera'],
        default='economy',
        error_messages={'invalid_choice': 'La clase tiene que ser economy o primera.'},
    )
    precio_min = serializers.DecimalField(
        max_digits=None, decimal_places=None, min_value=0, required=False,
        error_messages=_errores(MONTO_INVALIDO, 'invalid', 'min_value', 'max_string_length'),
    )
    precio_max = serializers.DecimalField(
        max_digits=None, decimal_places=None, min_value=0, required=False,
        error_messages=_errores(MONTO_INVALIDO, 'invalid', 'min_value', 'max_string_length'),
    )

    def _aeropuerto(self, codigo):
        codigo = codigo.upper()
        try:
            return Aeropuerto.objects.get(codigo_iata=codigo)
        except Aeropuerto.DoesNotExist:
            raise serializers.ValidationError(f'No conocemos el aeropuerto "{codigo}".')

    def validate_origen(self, valor):
        return self._aeropuerto(valor)

    def validate_destino(self, valor):
        return self._aeropuerto(valor)

    def validate_desde(self, valor):
        if valor < timezone.localdate():
            raise serializers.ValidationError('La fecha no puede ser en el pasado.')
        return valor

    def validate(self, datos):
        origen, destino = datos.get('origen'), datos.get('destino')
        errores = {}
        if not origen and not destino:
            errores['origen'] = 'Indicá un origen, un destino o ambos.'
        elif origen and destino and origen == destino:
            errores['destino'] = 'El destino tiene que ser distinto del origen.'
        elif origen and destino and origen.ciudad == destino.ciudad:
            errores['destino'] = 'Origen y destino están en la misma ciudad.'
        if 'hasta' in datos and datos['hasta'] < datos['desde']:
            errores['hasta'] = '"Hasta" no puede ser antes de "Desde".'
        if 'precio_min' in datos and 'precio_max' in datos and datos['precio_min'] > datos['precio_max']:
            errores['precio_min'] = 'El mínimo no puede ser mayor que el máximo.'
        if errores:
            raise serializers.ValidationError(errores)
        return datos
```

- [ ] **Paso 4: Implementar la vista** (en `backend/vuelos/views.py`)

Imports nuevos arriba:

```python
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AeropuertoSerializer, BusquedaSerializer, VueloDetalleSerializer, VueloSerializer
```

(Reemplaza el import de serializers que ya existe.) Agregar la clase:

```python
class BuscarVuelosView(APIView):
    """Vuelos activos, con lugar para todos, en el rango de precio y que todavía no salieron."""

    def get(self, request):
        # Un parámetro vacío (?hasta=) cuenta como no enviado.
        busqueda = BusquedaSerializer(data={k: v for k, v in request.query_params.items() if v != ''})
        busqueda.is_valid(raise_exception=True)
        d = busqueda.validated_data
        clase = d['clase']
        ahora = timezone.localtime()  # hora de Buenos Aires (TIME_ZONE)

        vuelos = (
            Vuelo.objects.select_related('aeropuerto_origen', 'aeropuerto_destino')
            .filter(
                estado=Vuelo.Estado.ACTIVO,
                fecha_operacion__range=(d['desde'], d.get('hasta', d['desde'])),
                **{f'asientos_disponibles_{clase}__gte': d['pasajeros']},
            )
            .exclude(fecha_operacion=ahora.date(), hora_partida__lte=ahora.time())
            .order_by('fecha_operacion', 'hora_partida', 'numero_vuelo')  # numero_vuelo: desempate estable
        )
        if d.get('origen'):
            vuelos = vuelos.filter(aeropuerto_origen=d['origen'])
        if d.get('destino'):
            vuelos = vuelos.filter(aeropuerto_destino=d['destino'])
        if 'precio_min' in d:
            vuelos = vuelos.filter(**{f'precio_{clase}__gte': d['precio_min']})
        if 'precio_max' in d:
            vuelos = vuelos.filter(**{f'precio_{clase}__lte': d['precio_max']})
        # ponytail: sin paginación; sumar PageNumberPagination si un rango largo devuelve demasiados vuelos.
        return Response(VueloSerializer(vuelos, many=True).data)
```

En `backend/vuelos/urls.py`, agregar la ruta **antes** del detalle:

```python
    path('vuelos/buscar/', views.BuscarVuelosView.as_view()),
```

- [ ] **Paso 5: Correr los tests y verificar que pasan**

Correr: `.venv/Scripts/python manage.py test`
Esperado: todos PASS. Si falla un caso de `ErroresBusquedaTests` porque DRF usa otra clave de error (por ejemplo `max_string_length`), agregar esa clave al `_errores(...)` del campo. No cambiar el test.

- [ ] **Paso 6: Commit**

```bash
git add backend/vuelos
git commit -m "feat(backend): búsqueda de vuelos con filtros y errores 400 en español"
```

---

### Tarea 5: Comando `seed` + deploy

**Archivos:**
- Crear: `backend/vuelos/management/__init__.py` (vacío), `backend/vuelos/management/commands/__init__.py` (vacío), `backend/vuelos/management/commands/seed.py`
- Modificar: `backend/build.sh`, `backend/vuelos/tests.py` (agregar al final)

**Interfaces:**
- Consume: modelos de las Tareas 1 y 2.
- Produce: `python manage.py seed [--dias N]`.

- [ ] **Paso 1: Escribir los tests que fallan** (agregar al final de `backend/vuelos/tests.py`; sumar `from io import StringIO` y `from django.core.management import call_command` arriba)

`Datos` ya crea BHI, AEP, EZE, COR y el avión LV-FAA, que también están en el seed. Como el seed usa `update_or_create`, después de correrlo quedan exactamente 11 aeropuertos y 4 aviones.

```python
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
```

- [ ] **Paso 2: Correr los tests y verificar que fallan**

Correr: `.venv/Scripts/python manage.py test vuelos.tests.SeedTests`
Esperado: ERROR con `CommandError: Unknown command: 'seed'`.

- [ ] **Paso 3: Implementar** — `backend/vuelos/management/commands/seed.py`

```python
"""Datos de ejemplo: aeropuertos, flota y vuelos de los próximos días. Idempotente.

Existe porque todavía no hay ABM de vuelos. Sacarlo de build.sh cuando exista.
"""
import datetime as dt
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from vuelos.models import Aeropuerto, Avion, Vuelo

AEROPUERTOS = [
    ('AEP', 'Buenos Aires', 'Aeroparque Jorge Newbery'),
    ('EZE', 'Buenos Aires', 'Aeropuerto Internacional Ministro Pistarini'),
    ('BHI', 'Bahía Blanca', 'Aeropuerto Comandante Espora'),
    ('BRC', 'San Carlos de Bariloche', 'Aeropuerto Teniente Luis Candelaria'),
    ('COR', 'Córdoba', 'Aeropuerto Ingeniero Ambrosio Taravella'),
    ('MDZ', 'Mendoza', 'Aeropuerto El Plumerillo'),
    ('IGR', 'Puerto Iguazú', 'Aeropuerto Cataratas del Iguazú'),
    ('USH', 'Ushuaia', 'Aeropuerto Malvinas Argentinas'),
    ('FTE', 'El Calafate', 'Aeropuerto Comandante Armando Tola'),
    ('SLA', 'Salta', 'Aeropuerto Martín Miguel de Güemes'),
    ('JUJ', 'San Salvador de Jujuy', 'Aeropuerto Horacio Guzmán'),
]

FLOTA = [
    ('LV-FAA', 'Airbus A320', 150, 12),
    ('LV-FAB', 'Boeing 737-800', 162, 12),
    ('LV-FAC', 'Embraer E190', 96, 8),
    ('LV-FAD', 'Airbus A330-200', 250, 24),
]


class Command(BaseCommand):
    help = 'Carga aeropuertos, flota y vuelos de ejemplo (no pisa lo que ya existe).'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=60, help='Días hacia adelante con vuelos (default 60).')

    def handle(self, *args, dias, **opciones):
        sistema, creado = get_user_model().objects.get_or_create(
            email='sistema@flyaway.local',
            defaults={'nombre': 'Sistema', 'apellido': 'Fly Away', 'rol': 'administrador'},
        )
        if creado:
            sistema.set_unusable_password()
            sistema.save()

        aeropuertos = [
            Aeropuerto.objects.update_or_create(
                codigo_iata=iata, defaults={'ciudad': ciudad, 'nombre': nombre, 'pais': 'Argentina'}
            )[0]
            for iata, ciudad, nombre in AEROPUERTOS
        ]
        aviones = [
            Avion.objects.update_or_create(
                matricula=matricula,
                defaults={'modelo': modelo, 'capacidad_economy': economy, 'capacidad_primera': primera},
            )[0]
            for matricula, modelo, economy, primera in FLOTA
        ]

        hoy = timezone.localdate()
        vuelos = []
        for i, origen in enumerate(aeropuertos):
            for j, destino in enumerate(aeropuertos):
                if origen.ciudad == destino.ciudad:
                    continue
                # Semillas por texto: mismo resultado en cada corrida.
                ruta = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}')
                duracion = 60 + ruta.randrange(30) * 5  # 1 h a 3 h 25 m, fija por ruta
                avion = aviones[ruta.randrange(len(aviones))]
                primer_numero = 1000 + (i * len(aeropuertos) + j) * 10  # bloque de números por ruta
                for n in range(dias):
                    fecha = hoy + dt.timedelta(days=n)
                    r = random.Random(f'{origen.codigo_iata}-{destino.codigo_iata}-{fecha}')
                    for k in range(r.randrange(5)):  # 0 a 4 vuelos ese día
                        partida = (6 + k * 4) * 60 + r.randrange(8) * 15  # 06:00 a 19:45: llega antes de medianoche
                        llegada = partida + duracion
                        economy = round((40000 + duracion * 900 + r.random() * 40000) / 10) * 10
                        vuelos.append(Vuelo(
                            numero_vuelo=f'FA {primer_numero + k}',
                            avion=avion,
                            aeropuerto_origen=origen,
                            aeropuerto_destino=destino,
                            fecha_operacion=fecha,
                            hora_partida=dt.time(partida // 60, partida % 60),
                            hora_llegada=dt.time(llegada // 60, llegada % 60),
                            precio_economy=economy,
                            precio_primera=round(economy * 2.2 / 10) * 10,
                            asientos_disponibles_economy=r.randrange(40),
                            asientos_disponibles_primera=r.randrange(10),
                            estado=Vuelo.Estado.CANCELADO if r.random() < 0.1 else Vuelo.Estado.ACTIVO,
                            creado_por=sistema,
                        ))
        # El índice único (numero_vuelo, fecha_operacion) descarta los que ya existen sin pisarlos.
        Vuelo.objects.bulk_create(vuelos, batch_size=1000, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(
            f'Seed listo: {len(aeropuertos)} aeropuertos, {len(aviones)} aviones, {Vuelo.objects.count()} vuelos.'
        ))
```

En `backend/build.sh`, agregar después de `python manage.py migrate`:

```bash
# Datos de ejemplo hasta que exista el ABM de vuelos (idempotente). Sacar cuando exista.
python manage.py seed
```

- [ ] **Paso 4: Correr los tests y verificar que pasan**

Correr: `.venv/Scripts/python manage.py test`
Esperado: todos PASS.

- [ ] **Paso 5: Probarlo contra la BD local**

```bash
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py seed
.venv/Scripts/python manage.py seed
```

Esperado: las dos corridas imprimen la **misma** cantidad de vuelos, alrededor de 13 000.

- [ ] **Paso 6: Commit**

```bash
git add backend/vuelos backend/build.sh
git commit -m "feat(backend): comando seed con datos de ejemplo y corrida en el deploy"
```

---

### Tarea 6: Front — búsqueda sin límite de días y con rango en la vuelta

**Archivos:**
- Modificar: `frontend/src/lib/busqueda.ts`, `frontend/src/components/BuscadorVuelos.tsx`, `frontend/src/pages/Vuelos.tsx`, `frontend/scripts/check.ts`

**Interfaces:**
- Produce: `Filtros.vueltaHasta: string` ('' = solo el día `vuelta`; siempre '' en solo ida), URL `vueltaHasta=`, error `ErroresBusqueda.vueltaHasta`. En ida y vuelta, `Filtros.hasta` es el rango de la ida.

- [ ] **Paso 1: Actualizar los chequeos para que fallen** — `frontend/scripts/check.ts`

En `base`, agregar `vueltaHasta: '',` después de `vuelta: '2026-10-31',`.

Reemplazar estas dos líneas:

```ts
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2026-11-08' }, hoy), {}, 'rango de 14 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-11-09' }, hoy).hasta, 'rango de 15 días')
```

por:

```ts
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2027-10-01' }, hoy), {}, 'rango sin límite de días')
```

Después de `assert.ok(validarBusqueda({ ...base, vuelta: '2026-10-25' }, hoy).vuelta, 'vuelta antes que la ida')`, agregar:

```ts
const conRangos: Filtros = { ...base, hasta: '2026-10-28', vueltaHasta: '2026-11-04' }
assert.deepEqual(validarBusqueda(conRangos, hoy), {}, 'ida y vuelta con rango en las dos')
assert.ok(validarBusqueda({ ...base, hasta: '2026-10-25' }, hoy).hasta, 'hasta de la ida antes que la ida')
assert.ok(validarBusqueda({ ...base, vueltaHasta: '2026-10-30' }, hoy).vueltaHasta, 'hasta de la vuelta antes que la vuelta')
```

Reemplazar:

```ts
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&vuelta=2026-10-31&hasta=2026-10-28'))!.hasta, '', 'hasta solo en solo ida')
```

por:

```ts
assert.deepEqual(leerFiltros(aParams(conRangos)), conRangos, 'ida y vuelta con rangos por la URL')
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&hasta=2026-10-28&vueltaHasta=2026-11-01'))!.vueltaHasta, '', 'vueltaHasta solo en ida y vuelta')
```

- [ ] **Paso 2: Correr los chequeos y verificar que fallan**

Correr: `npm run check`
Esperado: FAIL en `assert.deepEqual(validarBusqueda(base, hoy), {})` o en el chequeo del rango sin límite (`hasta: 'El rango puede ser de hasta 14 días'`).

- [ ] **Paso 3: Implementar `busqueda.ts`**

Borrar `MAX_DIAS_RANGO` (y su comentario) y `diasEntre`, que no tienen otros usos.

Reemplazar el comentario y la interfaz `Filtros`:

```ts
/**
 * Filtros de búsqueda. Fechas en YYYY-MM-DD.
 * - `vuelta: null` = solo ida (explorador): origen o destino pueden ser '' (cualquiera).
 * - `vuelta: string` = ida y vuelta: origen y destino obligatorios.
 * - `hasta` arma un rango con `ida` ('' = solo ese día); `vueltaHasta` lo mismo con `vuelta` (siempre '' en solo ida).
 * - `precioMin` / `precioMax`: por persona en la clase elegida; `null` = sin límite.
 */
export interface Filtros {
  origen: string
  destino: string
  ida: string
  hasta: string
  vuelta: string | null
  vueltaHasta: string
  pasajeros: number
  clase: Clase
  precioMin: number | null
  precioMax: number | null
}

export type ErroresBusqueda = Partial<
  Record<'origen' | 'destino' | 'ida' | 'hasta' | 'vuelta' | 'vueltaHasta' | 'pasajeros' | 'clase' | 'precio', string>
>
```

En `validarBusqueda`, reemplazar el bloque `if (f.hasta && f.ida) { … }` y el bloque `if (f.vuelta !== null) { … }` por:

```ts
  if (f.hasta && f.ida && f.hasta < f.ida) {
    e.hasta = f.vuelta === null ? 'No puede ser antes de "Desde"' : 'No puede ser antes de la ida'
  }
  if (f.vuelta !== null) {
    if (!f.vuelta) e.vuelta = 'Elegí la fecha de vuelta'
    else if (f.ida && f.vuelta < f.ida) e.vuelta = 'La vuelta no puede ser antes de la ida'
    if (f.vueltaHasta && f.vuelta && f.vueltaHasta < f.vuelta) e.vueltaHasta = 'No puede ser antes de la vuelta'
  }
```

En `leerFiltros`, reemplazar las líneas de `hasta` y `vuelta` del objeto devuelto por:

```ts
    hasta: fecha('hasta'),
    vuelta: idaYVuelta ? fecha('vuelta') : null,
    vueltaHasta: idaYVuelta ? fecha('vueltaHasta') : '',
```

En `aParams`, reemplazar:

```ts
  p.set('ida', f.ida)
  if (f.vuelta !== null) p.set('vuelta', f.vuelta)
  else if (f.hasta) p.set('hasta', f.hasta)
```

por:

```ts
  p.set('ida', f.ida)
  if (f.hasta) p.set('hasta', f.hasta)
  if (f.vuelta !== null) {
    p.set('vuelta', f.vuelta)
    if (f.vueltaHasta) p.set('vueltaHasta', f.vueltaHasta)
  }
```

- [ ] **Paso 4: Correr los chequeos y verificar que pasan**

Correr: `npm run check`
Esperado: `busqueda + formato: OK` y `vuelos: OK`.

- [ ] **Paso 5: Buscador con cuatro fechas** — `frontend/src/components/BuscadorVuelos.tsx`

Agregar `type ReactNode` al import de React: `import { useState, type FormEvent, type ReactNode } from 'react'`.

Después de la función `MensajeError`, agregar:

```tsx
function CampoFecha(props: {
  id: string
  texto: ReactNode
  valor: string
  min: string
  error?: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <div className={caja}>
        <label htmlFor={props.id} className={etiqueta}>
          {props.texto}
        </label>
        <input
          id={props.id}
          type="date"
          min={props.min}
          value={props.valor}
          onChange={(e) => props.onChange(e.target.value)}
          aria-invalid={!!props.error}
          aria-describedby={`error-${props.id}`}
          className={control}
        />
      </div>
      <MensajeError id={`error-${props.id}`} texto={props.error} />
    </div>
  )
}

/** "Hasta (opcional)"; `de` aclara a cuál fecha para lectores de pantalla. */
const hastaOpcional = (de: string) => (
  <>
    Hasta <span className="sr-only">{de} </span>
    <span className="font-normal">(opcional)</span>
  </>
)
```

Después de `const [vuelta, setVuelta] = …`, agregar:

```tsx
  const [vueltaHasta, setVueltaHasta] = useState(inicial?.vueltaHasta ?? '')
```

En `enviar`, reemplazar `hasta: soloIda ? hasta : '',` y `vuelta: soloIda ? null : vuelta,` por:

```tsx
      hasta,
      vuelta: soloIda ? null : vuelta,
      vueltaHasta: soloIda ? '' : vueltaHasta,
```

Reemplazar el `className` de la grilla (`grid gap-2 lg:grid-cols-[1fr_auto_1fr_1fr_1fr_1.3fr_auto] lg:items-start`) por:

```tsx
      <div
        className={`grid gap-2 lg:items-start ${
          soloIda
            ? 'lg:grid-cols-[1fr_auto_1fr_2fr_1.3fr_auto]'
            : 'lg:grid-cols-[1fr_auto_1fr_2fr_2fr_1.3fr_auto]'
        }`}
      >
```

Reemplazar todo el bloque que va desde `<div>` + `<label htmlFor="ida"` hasta el cierre `)}` del condicional `{soloIda ? ( … hasta … ) : ( … vuelta … )}` por:

```tsx
        <div className="grid grid-cols-2 gap-2">
          <CampoFecha
            id="ida"
            texto={soloIda ? 'Desde' : 'Ida'}
            valor={ida}
            min={hoy}
            error={errores.ida}
            onChange={setIda}
          />
          <CampoFecha
            id="hasta"
            texto={hastaOpcional(soloIda ? '' : 'de la ida')}
            valor={hasta}
            min={ida || hoy}
            error={errores.hasta}
            onChange={setHasta}
          />
        </div>

        {!soloIda && (
          <div className="grid grid-cols-2 gap-2">
            <CampoFecha
              id="vuelta"
              texto="Vuelta"
              valor={vuelta}
              min={ida || hoy}
              error={errores.vuelta}
              onChange={setVuelta}
            />
            <CampoFecha
              id="vueltaHasta"
              texto={hastaOpcional('de la vuelta')}
              valor={vueltaHasta}
              min={vuelta || ida || hoy}
              error={errores.vueltaHasta}
              onChange={setVueltaHasta}
            />
          </div>
        )}
```

- [ ] **Paso 6: La vuelta busca en su rango** — `frontend/src/pages/Vuelos.tsx`

En `busquedaVuelta`, cambiar `hasta: '',` por `hasta: f.vueltaHasta,`.

En `sugerencia`, cambiar:

```tsx
        : f.vuelta === null && !f.hasta
```

por:

```tsx
        : !f.hasta || (f.vuelta !== null && !f.vueltaHasta)
```

En el `subtitulo` de la lista de vuelta, cambiar `` `${fechaLarga(f.vuelta)} - ${detalle}` `` por:

```tsx
`${f.vueltaHasta ? rangoFechas(f.vuelta, f.vueltaHasta) : fechaLarga(f.vuelta)} - ${detalle}`
```

- [ ] **Paso 7: Verificar tipos, lint y chequeos**

Correr: `npm run build && npm run lint && npm run check`
Esperado: sin errores. `npm run check` imprime los dos OK.

- [ ] **Paso 8: Commit**

```bash
git add frontend/src/lib/busqueda.ts frontend/src/components/BuscadorVuelos.tsx frontend/src/pages/Vuelos.tsx frontend/scripts/check.ts
git commit -m "feat(frontend): rango de fechas en ida y vuelta y sin límite de 14 días"
```

---

### Tarea 7: Front — conectar `vuelos.ts` a la API

**Archivos:**
- Modificar: `frontend/src/lib/vuelos.ts`, `frontend/scripts/check.ts`

**Interfaces:**
- Consume: `api<T>(path)` de `src/lib/api.ts`. `VITE_API_URL` ya termina en `/api`.
- Produce:
  - `queryBusqueda(p: ParamsBusqueda): URLSearchParams` (exportada para los chequeos).
  - `buscarVuelos(p: ParamsBusqueda): Promise<Vuelo[]>` (ya no recibe `ahora`).
  - `getAeropuertos(): Promise<Aeropuerto[]>` y `getVuelo(id: string): Promise<VueloDetalle>`.
  - `vueltasPosibles` con la regla "sale después de que la ida aterriza".
  - Sin cambios: `precioDe`, `asientosDe`, `duracionDe`, `estadoClase`, `UMBRAL_ULTIMOS` y los tipos.

- [ ] **Paso 1: Reescribir los chequeos de `vuelos`** — `frontend/scripts/check.ts`

Reemplazar el import de `../src/lib/vuelos.ts` por:

```ts
import { duracionDe, estadoClase, queryBusqueda, vueltasPosibles, type ParamsBusqueda, type Vuelo } from '../src/lib/vuelos.ts'
```

Reemplazar todo desde la línea `// vuelos (mock)` hasta el final del archivo por:

```ts
// vuelos: query string de GET /vuelos/buscar/ (nombres del backend, sin parámetros vacíos)
const params: ParamsBusqueda = {
  origen: 'BHI',
  destino: '',
  desde: '2026-10-20',
  hasta: '',
  pasajeros: 2,
  clase: 'primera',
  precioMin: 50000,
  precioMax: null,
}
assert.equal(queryBusqueda(params).toString(), 'origen=BHI&desde=2026-10-20&pasajeros=2&clase=primera&precio_min=50000')
assert.equal(
  queryBusqueda({ ...params, destino: 'AEP', hasta: '2026-10-25', precioMin: 0, precioMax: 90000 }).toString(),
  'origen=BHI&destino=AEP&desde=2026-10-20&hasta=2026-10-25&pasajeros=2&clase=primera&precio_min=0&precio_max=90000',
  'precio 0 se manda',
)

assert.equal(duracionDe({ hora_partida: '06:40:00', hora_llegada: '08:05:00' } as Vuelo), 85)

// vueltasPosibles: solo las que salen después de que aterriza la ida (la vuelta puede ser un rango superpuesto)
const ida = { fecha_operacion: '2026-11-14', hora_llegada: '12:00:00' } as Vuelo
const vueltas = [
  { id: 'diaAnterior', fecha_operacion: '2026-11-13', hora_partida: '18:00:00' },
  { id: 'aLaManana', fecha_operacion: '2026-11-14', hora_partida: '09:00:00' },
  { id: 'alAterrizar', fecha_operacion: '2026-11-14', hora_partida: '12:00:00' },
  { id: 'aLaTarde', fecha_operacion: '2026-11-14', hora_partida: '15:00:00' },
  { id: 'otroDia', fecha_operacion: '2026-11-15', hora_partida: '06:00:00' },
] as Vuelo[]
assert.deepEqual(vueltasPosibles(vueltas, ida).map((v) => v.id), ['aLaTarde', 'otroDia'])

// estadoClase
assert.equal(estadoClase(0), 'agotada')
assert.equal(estadoClase(1), 'ultimos')
assert.equal(estadoClase(5), 'ultimos')
assert.equal(estadoClase(6), 'disponible')

console.log('vuelos: OK')
```

- [ ] **Paso 2: Correr los chequeos y verificar que fallan**

Correr: `npm run check`
Esperado: FAIL. `queryBusqueda` no existe (SyntaxError de import: `does not provide an export named 'queryBusqueda'`).

- [ ] **Paso 3: Reescribir `vuelos.ts`**

Reemplazar desde el comentario `// ponytail: todo lo de abajo es mock…` hasta el final del archivo por lo que sigue. Los tipos, `EstadoClase` y `UMBRAL_ULTIMOS` de arriba quedan como están. Agregar `import { api } from './api.ts'` arriba, junto al import de `Clase`.

```ts
const aMinutos = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))

export const getAeropuertos = () => api<Aeropuerto[]>('/aeropuertos/')

/** Query string de GET /vuelos/buscar/ con los nombres del backend. Omite lo vacío. */
export function queryBusqueda(p: ParamsBusqueda): URLSearchParams {
  const q = new URLSearchParams()
  const poner = (clave: string, valor: string | number | null) => {
    if (valor !== null && valor !== '') q.set(clave, String(valor))
  }
  poner('origen', p.origen)
  poner('destino', p.destino)
  poner('desde', p.desde)
  poner('hasta', p.hasta)
  poner('pasajeros', p.pasajeros)
  poner('clase', p.clase)
  poner('precio_min', p.precioMin)
  poner('precio_max', p.precioMax)
  return q
}

/** Vuelos activos, con lugar para todos, en el rango de precio y que no salieron, por fecha y hora (lo filtra el back). */
export const buscarVuelos = (p: ParamsBusqueda) => api<Vuelo[]>(`/vuelos/buscar/?${queryBusqueda(p)}`)

/** Detalle de un vuelo (incluye cancelados). */
export const getVuelo = (id: string) => api<VueloDetalle>(`/vuelos/${encodeURIComponent(id)}/`)

export const precioDe = (v: Vuelo, clase: Clase) => Number(clase === 'economy' ? v.precio_economy : v.precio_primera)

export const asientosDe = (v: Vuelo, clase: Clase) =>
  clase === 'economy' ? v.asientos_disponibles_economy : v.asientos_disponibles_primera

/** Duración en minutos. */
export const duracionDe = (v: Vuelo) => aMinutos(v.hora_llegada) - aMinutos(v.hora_partida)

/** Solo sirven las vueltas que salen después de que aterriza la ida (la vuelta puede ser un rango que se superpone). */
export function vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[] {
  const aterriza = ida.fecha_operacion + ida.hora_llegada
  return vueltas.filter((v) => v.fecha_operacion + v.hora_partida > aterriza)
}

/** Estado de una clase según sus asientos libres. */
export function estadoClase(asientos: number): EstadoClase {
  if (asientos <= 0) return 'agotada'
  return asientos <= UMBRAL_ULTIMOS ? 'ultimos' : 'disponible'
}
```

Actualizar el comentario de `ParamsBusqueda` para que diga `/** Parámetros de GET /vuelos/buscar/. origen / destino '' = cualquiera. hasta '' = solo el día desde. */`. Si `Avion` queda sin usar fuera de `VueloDetalle`, se deja: es parte del tipo.

- [ ] **Paso 4: Verificar**

Correr: `npm run check && npm run build && npm run lint`
Esperado: `busqueda + formato: OK`, `vuelos: OK`, build y lint sin errores. Si `build` marca algún import muerto (por ejemplo, un uso de `generarVuelos` que no esté en este plan), borrarlo.

- [ ] **Paso 5: Probar de punta a punta a mano**

Con dos terminales:

```bash
# backend/
.venv/Scripts/python manage.py runserver
# frontend/  (con frontend/.env.local → VITE_API_URL=http://localhost:8000/api)
npm run dev
```

En http://localhost:5173 verificar:
1. Los aeropuertos cargan en el buscador.
2. **Solo ida**: con solo origen BHI, desde hoy hasta dentro de 30 días, aparecen resultados de varios días y destinos.
3. **Ida y vuelta**: BHI → AEP con la ida en un rango de 3 días y la vuelta en otro, se elige una ida y las vueltas listadas salen después de que esa ida aterriza.
4. "Ver detalle" muestra el avión y "Elegir" llega a "Tu viaje".
5. El filtro de precio recorta resultados.
6. Con la grilla del buscador en 1024 px, 1280 px y ancho de celular no hay scroll horizontal y los cuatro campos de fecha son legibles.
7. En la pestaña Network del navegador las llamadas van a `localhost:8000/api/...`.

- [ ] **Paso 6: Commit**

```bash
git add frontend/src/lib/vuelos.ts frontend/scripts/check.ts
git commit -m "feat(frontend): búsqueda, aeropuertos y detalle desde la API (sin mock)"
```

---

### Tarea 8: Documentación

**Archivos:**
- Modificar: `docs/arquitectura.md`, `docs/memoria.md`

- [ ] **Paso 1: `docs/arquitectura.md`**

- Cambiar `│   └── accounts/             User custom provisorio del setup (se reemplaza por \`usuarios\`)` y `│   # apps a crear según modelo.dbml` por:

```
│   ├── usuarios/             modelo Usuario (tabla usuarios, login por email, rol)
│   └── vuelos/               aeropuertos, aviones, vuelos; API de búsqueda/detalle; comando seed
```

- En el árbol del frontend, cambiar `api.ts (fetch + JWT), mocks con la forma de la API, lógica pura` por `api.ts (fetch + JWT), llamadas a la API, lógica pura (sesión todavía mock)`.
- En la sección API, marcar `GET /api/aeropuertos/`, `GET /api/vuelos/buscar/…` y `GET /api/vuelos/{id}/` con `✅ hecho`, y reemplazar `origen y/o destino (al menos uno), hasta opcional (rango ≤ 14 días);` por `origen y/o destino (al menos uno), hasta opcional (sin límite de días);`.
- Debajo del bloque de la API, agregar:

```markdown
**Errores 400:** formato estándar de DRF, `{"parametro": ["mensaje"]}`, con mensajes en español (los mismos que muestra el front). Un parámetro vacío (`?hasta=`) cuenta como no enviado. El 404 es `{"detail": "..."}`.

**Datos de ejemplo:** `python manage.py seed [--dias 60]` carga los aeropuertos, la flota y los vuelos de los próximos días. Es idempotente y no pisa vuelos existentes. Corre en `build.sh` hasta que exista el ABM de vuelos.
```

- En "Comandos" de `CLAUDE.md` no se toca nada: `seed` queda documentado en arquitectura.

- [ ] **Paso 2: `docs/memoria.md`**

Arriba de "Estado actual", agregar:

```markdown
**2026-10-02 — Backend de vuelos (rama `feat/backend-vuelos`)**
- Modelo `usuarios` del DBML (login por email, `rol`), que reemplaza a `accounts`. **Para la US de login:** el modelo ya está; faltan `POST /auth/registro/`, `GET /auth/yo/` y conectar `auth.ts`/`sesion.tsx` (hoy mock).
- App `vuelos`: aeropuertos, aviones y vuelos con los constraints del DBML; `GET /api/aeropuertos/`, `/api/vuelos/buscar/` y `/api/vuelos/{id}/`. El front ya no usa el mock de vuelos.
- Búsqueda sin límite de días; en ida y vuelta, la ida y la vuelta aceptan fecha exacta o rango.
- `python manage.py seed`: datos de ejemplo. Corre en `build.sh` (Render free no tiene shell).
- **Deploy:** antes del primer deploy de esta rama, resetear Supabase (borrar todas las tablas: las de `accounts` chocan con la migración nueva).
```

En "Decisiones", agregar arriba:

```markdown
| 2026-10-02 | Sin límite de días en el rango de búsqueda; rango también en ida y vuelta | Pedido del equipo: elegir ida y vuelta en una fecha o entre dos |
| 2026-10-02 | Errores 400 con el formato de DRF (`{"param": ["mensaje"]}`) en español | Estándar del framework; el front puede ubicar cada error en su campo |
| 2026-10-02 | `seed` en `build.sh`, idempotente con `ignore_conflicts` | Render free no tiene shell; hasta que exista el ABM de vuelos no hay otra forma de cargar datos |
| 2026-10-02 | `Usuario` sin `PermissionsMixin`; el admin de Django es solo para `administrador` | El DBML no tiene tablas de permisos; el rol define el acceso |
```

En "Próximos pasos", cambiar el punto 1 por `1. ABM de vuelos (admin), con generación de N filas a partir de días + período. Al terminarlo, sacar \`seed\` de \`build.sh\`.` y borrar el punto 3 (`Búsqueda de vuelos con disponibilidad.`), que ya está hecho. Renumerar.

En "Estado actual", en la entrada de la interfaz de inicio, cambiar `**Todo mockeado** en …` por `Vuelos ya conectados al backend (ver arriba); la sesión (\`lib/auth.ts\`) sigue mockeada.`

- [ ] **Paso 3: Verificación final**

```bash
cd backend && .venv/Scripts/python manage.py test && cd ../frontend && npm run check && npm run build && npm run lint
```

Esperado: todo verde.

- [ ] **Paso 4: Commit**

```bash
git add docs/arquitectura.md docs/memoria.md
git commit -m "docs: memoria y arquitectura del backend de vuelos"
```
