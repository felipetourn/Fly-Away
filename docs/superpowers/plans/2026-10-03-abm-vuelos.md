# ABM de vuelos (administrador) - plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El administrador crea vuelos con recurrencia, edita una instancia y cancela una instancia desde `/admin/vuelos`.

**Architecture:** Se extiende la app Django `vuelos` con endpoints de administrador sobre `/api/vuelos/`. La recurrencia no se persiste: los períodos viajan en el pedido de alta y el backend genera una fila de `vuelos` por fecha, en una transacción. El front suma dos pantallas (listado y formulario) que llaman a la API vía `src/lib/api.ts`.

**Tech Stack:** Django 5.2 + DRF + SimpleJWT, React 19 + TypeScript + Vite + Tailwind v4 + react-router. Sin dependencias nuevas.

**Spec:** [docs/superpowers/specs/2026-10-03-abm-vuelos-design.md](../specs/2026-10-03-abm-vuelos-design.md)

## Global Constraints

- Idioma: español en código de dominio, mensajes, UI, docs y commits. Nombres de campos como en `docs/modelo.dbml`.
- Commits: Felipe Tourn como único autor. Sin `Co-Authored-By`, sin firmas ni menciones a Claude.
- Textos de UI: nunca el carácter punto medio; usar "-" (etiqueta - valor) o "," (listas).
- Sin dependencias nuevas, ni en `requirements.txt` ni en `package.json`.
- Backend en local siempre contra SQLite: anteponer `DATABASE_URL=` a cada comando `manage.py` (el `.env` puede apuntar a Supabase, que es compartida). Ningún paso de este plan toca Supabase salvo la Task 11, que pide confirmación.
- Reglas de negocio en el backend; el front solo repite validaciones por UX.
- Todo endpoint nuevo exige rol `administrador`: 401 sin sesión, 403 con otro rol.
- Errores 400 con el formato de DRF: `{"campo": ["mensaje"]}`, los de un período en `periodos[i].campo`, los generales en `non_field_errors`.
- El frontend llama a la API solo vía `src/lib/api.ts`.
- `dias`: 0 = lunes a 6 = domingo.
- Comandos (bash, desde la raíz del repo):
  - Tests backend: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos`
  - Front: `cd frontend && npm run check && npm run build && npm run lint`

## Review Focus

1. Alta con `desde` = hoy y una hora de partida que ya pasó: no debe crear un vuelo que ya salió (Task 4, `test_hoy_con_horario_pasado`).
2. `avion` o id de vuelo que no es un UUID: debe responder 400 o 404, nunca 500 (Task 4 `test_validaciones`, Task 6 `test_404`).
3. Doble envío del formulario de alta: la segunda alta idéntica debe rechazarse por avión ocupado y no duplicar vuelos (Task 4, `test_doble_envio`).
4. `PATCH` con cuerpo vacío o con campos no editables (`numero_vuelo`, `estado`, asientos): 200 sin cambios, sin tocar esos campos (Task 5, `test_cuerpo_vacio_y_campos_no_editables`).
5. Vuelo nocturno contra un vuelo del mismo avión en la madrugada siguiente: el chequeo de avión libre debe mirar el día vecino (Task 4, `test_avion_ocupado_cruzando_medianoche`).

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `backend/vuelos/models.py` | Suma `fecha_llegada` y su constraint. |
| `backend/vuelos/migrations/0002_vuelo_fecha_llegada.py` | Columna nueva y relleno de filas existentes. |
| `backend/vuelos/migrations/0003_vuelo_fecha_llegada_obligatoria.py` | NOT NULL y constraint. |
| `backend/vuelos/permissions.py` (nuevo) | `EsAdministrador`. |
| `backend/vuelos/servicios.py` (nuevo) | Reglas del ABM: fechas de un período, fecha de llegada, número siguiente, avión libre, alta atómica. |
| `backend/vuelos/serializers.py` | Serializers de filtros, alta y edición. |
| `backend/vuelos/views.py`, `urls.py` | Listado, alta, edición, cancelación, aviones. |
| `backend/vuelos/management/commands/seed.py` | Catálogo siempre, vuelos solo con `--vuelos`, flota de 10. |
| `backend/vuelos/tests.py` | Tests de todo lo anterior. |
| `frontend/src/lib/vuelos.ts` | `fecha_llegada`, duración y vueltas con cruce de medianoche. |
| `frontend/src/lib/adminVuelos.ts` (nuevo) | Llamadas del ABM y lógica pura (fechas de un período). |
| `frontend/src/pages/AdminVuelos.tsx` (nuevo) | Listado, filtros, paginación, confirmación de cancelación. |
| `frontend/src/pages/AdminVueloForm.tsx` (nuevo) | Formulario de alta y de edición. |
| `frontend/src/App.tsx` | Rutas `/admin/vuelos`, `/admin/vuelos/nuevo`, `/admin/vuelos/:id`. |

---

### Task 1: `fecha_llegada` en el backend

**Files:**
- Modify: `docs/modelo.dbml` (tabla `vuelos`)
- Modify: `backend/vuelos/models.py`
- Create: `backend/vuelos/migrations/0002_vuelo_fecha_llegada.py`
- Create: `backend/vuelos/migrations/0003_vuelo_fecha_llegada_obligatoria.py`
- Modify: `backend/vuelos/serializers.py` (`VueloSerializer`)
- Modify: `backend/vuelos/management/commands/seed.py`
- Test: `backend/vuelos/tests.py`

**Interfaces:**
- Produces: `Vuelo.fecha_llegada` (`DateField`, obligatorio); la API de búsqueda y detalle devuelve `fecha_llegada` (`"YYYY-MM-DD"`); el ayudante de tests `Datos.vuelo(...)` completa `fecha_llegada` solo.

- [ ] **Step 1: Actualizar los tests**

En `backend/vuelos/tests.py`, reemplazar el método `Datos.vuelo` por:

```python
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
```

Agregar a `ModeloVueloTests`:

```python
    def test_la_llegada_es_posterior_a_la_partida(self):
        nocturno = self.vuelo(partida='23:30')  # llega 00:30 del día siguiente
        self.assertEqual(nocturno.fecha_llegada, nocturno.fecha_operacion + dt.timedelta(days=1))
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo('FA 2', hora_llegada=dt.time(14, 0))  # mismo día, llega antes de salir
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.vuelo('FA 3', fecha_llegada=HOY)  # llega el día anterior
```

En `VUELO_CAMPOS` agregar `'fecha_llegada'`. En `DetalleTests.test_detalle_con_avion_y_forma_de_la_api` agregar:

```python
        self.assertEqual(d['fecha_llegada'], str(HOY + dt.timedelta(days=1)))
```

En `BuscarTests.test_hoy_es_la_fecha_de_buenos_aires`, quitar el `hora_llegada=dt.time(23, 59)` (el ayudante ya resuelve el cruce de medianoche):

```python
        self.vuelo('FA 2', fecha=HOY, partida='23:45')
```

Agregar al final del archivo (y sumar a los imports `from django.db import connection`, `from django.db.migrations.executor import MigrationExecutor`, `from django.test import TransactionTestCase`):

```python
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
        apps = self.migrar(ultima)
        self.assertEqual(apps.get_model('vuelos', 'Vuelo').objects.get().fecha_llegada, HOY)
```

- [ ] **Step 2: Correr los tests y ver que fallan**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos`
Expected: FAIL con `TypeError: Vuelo() got unexpected keyword arguments: 'fecha_llegada'`.

- [ ] **Step 3: Modelo**

En `backend/vuelos/models.py`, en `Vuelo`, agregar el campo debajo de `fecha_operacion`:

```python
    fecha_llegada = models.DateField()
```

y el constraint al final de `Meta.constraints`:

```python
            models.CheckConstraint(
                condition=Q(fecha_llegada__gt=F('fecha_operacion'))
                | Q(fecha_llegada=F('fecha_operacion'), hora_llegada__gt=F('hora_partida')),
                name='vuelo_llegada_posterior_a_partida',
            ),
```

- [ ] **Step 4: Migraciones**

Crear `backend/vuelos/migrations/0002_vuelo_fecha_llegada.py`:

```python
from django.db import migrations, models
from django.db.models import F


def completar(apps, schema_editor):
    # Hasta acá ningún vuelo cruzaba medianoche: todos llegan el día en que salen.
    apps.get_model('vuelos', 'Vuelo').objects.update(fecha_llegada=F('fecha_operacion'))


class Migration(migrations.Migration):
    dependencies = [('vuelos', '0001_initial')]

    operations = [
        migrations.AddField(model_name='vuelo', name='fecha_llegada', field=models.DateField(null=True)),
        migrations.RunPython(completar, migrations.RunPython.noop),
    ]
```

Crear `backend/vuelos/migrations/0003_vuelo_fecha_llegada_obligatoria.py`:

```python
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [('vuelos', '0002_vuelo_fecha_llegada')]

    operations = [
        migrations.AlterField(model_name='vuelo', name='fecha_llegada', field=models.DateField()),
        migrations.AddConstraint(
            model_name='vuelo',
            constraint=models.CheckConstraint(
                condition=Q(fecha_llegada__gt=F('fecha_operacion'))
                | Q(fecha_llegada=F('fecha_operacion'), hora_llegada__gt=F('hora_partida')),
                name='vuelo_llegada_posterior_a_partida',
            ),
        ),
    ]
```

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py makemigrations --check --dry-run`
Expected: `No changes detected` (las migraciones a mano coinciden con el modelo).

- [ ] **Step 5: Serializer y seed**

En `backend/vuelos/serializers.py`, en `VueloSerializer.Meta.fields`, agregar `'fecha_llegada'` después de `'fecha_operacion'`.

En `backend/vuelos/management/commands/seed.py`, en el `Vuelo(...)` del bucle, agregar debajo de `fecha_operacion=fecha,`:

```python
                            fecha_llegada=fecha,
```

- [ ] **Step 6: DBML**

En `docs/modelo.dbml`, tabla `vuelos`, agregar debajo de `fecha_operacion date [not null]`:

```
  fecha_llegada date [not null, note: 'La calcula el backend: fecha_operacion, o el día siguiente si hora_llegada < hora_partida']
```

y en la nota de la tabla, a la lista de constraints:

```
    CHECK (fecha_llegada > fecha_operacion OR (fecha_llegada = fecha_operacion AND hora_llegada > hora_partida))
```

- [ ] **Step 7: Correr los tests**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos`
Expected: PASS (todos, incluidos los que ya existían).

- [ ] **Step 8: Commit**

```bash
git add docs/modelo.dbml backend/vuelos
git commit -m "feat(backend): fecha_llegada en vuelos para los que cruzan medianoche"
```

---

### Task 2: `fecha_llegada` en el frontend

**Files:**
- Modify: `frontend/src/lib/vuelos.ts`
- Modify: `frontend/src/components/CardVuelo.tsx`, `frontend/src/components/DetalleVuelo.tsx`, `frontend/src/pages/Vuelos.tsx`
- Test: `frontend/scripts/check.ts`

**Interfaces:**
- Consumes: la API devuelve `fecha_llegada` (Task 1).
- Produces: `Vuelo.fecha_llegada: string`; `llegaAlDiaSiguiente(v: Vuelo): boolean`.

- [ ] **Step 1: Chequeos que fallan**

En `frontend/scripts/check.ts`, sumar `llegaAlDiaSiguiente` al import de `../src/lib/vuelos.ts` y reemplazar desde la línea de `duracionDe` hasta el `assert.deepEqual(vueltasPosibles(...))` por:

```ts
assert.equal(duracionDe({ fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-14', hora_partida: '06:40:00', hora_llegada: '08:05:00' } as Vuelo), 85)
const nocturno = { fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-15', hora_partida: '23:00:00', hora_llegada: '01:30:00' } as Vuelo
assert.equal(duracionDe(nocturno), 150, 'cruza medianoche')
assert.equal(llegaAlDiaSiguiente(nocturno), true)

// vueltasPosibles: solo las que salen después de que aterriza la ida (la vuelta puede ser un rango superpuesto)
const ida = { fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-14', hora_llegada: '12:00:00' } as Vuelo
const vueltas = [
  { id: 'diaAnterior', fecha_operacion: '2026-11-13', hora_partida: '18:00:00' },
  { id: 'aLaManana', fecha_operacion: '2026-11-14', hora_partida: '09:00:00' },
  { id: 'alAterrizar', fecha_operacion: '2026-11-14', hora_partida: '12:00:00' },
  { id: 'aLaTarde', fecha_operacion: '2026-11-14', hora_partida: '15:00:00' },
  { id: 'otroDia', fecha_operacion: '2026-11-15', hora_partida: '06:00:00' },
] as Vuelo[]
assert.deepEqual(vueltasPosibles(vueltas, ida).map((v) => v.id), ['aLaTarde', 'otroDia'])
assert.deepEqual(vueltasPosibles(vueltas, nocturno).map((v) => v.id), ['otroDia'], 'la ida aterriza el 15 a la 01:30')
```

- [ ] **Step 2: Ver que falla**

Run: `cd frontend && npm run check`
Expected: FAIL (`llegaAlDiaSiguiente` no existe).

- [ ] **Step 3: Lógica**

En `frontend/src/lib/vuelos.ts`:

En `interface Vuelo`, debajo de `fecha_operacion`:

```ts
  fecha_llegada: string // la del día siguiente si el vuelo cruza medianoche
```

Reemplazar `duracionDe` y `vueltasPosibles`:

```ts
export const llegaAlDiaSiguiente = (v: Vuelo) => v.fecha_llegada > v.fecha_operacion

/** Duración en minutos. */
export const duracionDe = (v: Vuelo) =>
  aMinutos(v.hora_llegada) - aMinutos(v.hora_partida) + (llegaAlDiaSiguiente(v) ? 24 * 60 : 0)

/** Solo sirven las vueltas que salen después de que aterriza la ida (la vuelta puede ser un rango que se superpone). */
export function vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[] {
  const aterriza = ida.fecha_llegada + ida.hora_llegada
  return vueltas.filter((v) => v.fecha_operacion + v.hora_partida > aterriza)
}
```

- [ ] **Step 4: Marca "+1" en las tres vistas**

`frontend/src/components/CardVuelo.tsx`: sumar `llegaAlDiaSiguiente` al import de `../lib/vuelos` y reemplazar la línea de la hora de llegada:

```tsx
          <p className="text-2xl font-extrabold">
            {hora(vuelo.hora_llegada)}
            {llegaAlDiaSiguiente(vuelo) && (
              <sup className="ml-0.5 text-xs font-bold text-naranja" title="Llega al día siguiente">+1</sup>
            )}
          </p>
```

`frontend/src/components/DetalleVuelo.tsx`: sumar `llegaAlDiaSiguiente` al import y reemplazar el `Extremo` de destino:

```tsx
          <Extremo etiqueta="Destino" horario={v.hora_llegada} aeropuerto={v.destino} derecha>
            {llegaAlDiaSiguiente(v) && <p className="mt-1 text-xs font-semibold text-naranja">Llega al día siguiente</p>}
          </Extremo>
```

`frontend/src/pages/Vuelos.tsx`: sumar `llegaAlDiaSiguiente` al import de `../lib/vuelos` y, en `LineaVuelo`, reemplazar `{hora(vuelo.hora_llegada)},{' '}` por:

```tsx
{hora(vuelo.hora_llegada)}{llegaAlDiaSiguiente(vuelo) ? ' (+1)' : ''},{' '}
```

- [ ] **Step 5: Verificar**

Run: `cd frontend && npm run check && npm run build && npm run lint`
Expected: los tres pasan.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): vuelos que llegan al día siguiente"
```

---

### Task 3: `seed` con catálogo y flota de 10

**Files:**
- Modify: `backend/vuelos/management/commands/seed.py`
- Modify: `backend/build.sh`
- Test: `backend/vuelos/tests.py` (`SeedTests`)

**Interfaces:**
- Produces: `manage.py seed` carga aeropuertos, 10 aviones y el usuario `sistema`; `manage.py seed --vuelos [--dias N]` agrega los vuelos de ejemplo, solo sobre LV-FAA a LV-FAD.

- [ ] **Step 1: Tests**

En `SeedTests`, reemplazar `correr` y `test_carga_datos_de_ejemplo`, y agregar dos tests:

```python
    def correr(self, vuelos=True):
        call_command('seed', dias=3, vuelos=vuelos, stdout=StringIO())

    def test_carga_datos_de_ejemplo(self):
        self.correr()
        self.assertEqual(Aeropuerto.objects.count(), 11)
        self.assertEqual(Avion.objects.count(), 10)
        self.assertGreater(Vuelo.objects.count(), 0)
        sistema = get_user_model().objects.get(email='sistema@flyaway.local')
        self.assertEqual(sistema.rol, 'administrador')
        self.assertFalse(sistema.has_usable_password())

    def test_sin_vuelos_carga_solo_el_catalogo(self):
        self.correr(vuelos=False)
        self.assertEqual((Aeropuerto.objects.count(), Avion.objects.count(), Vuelo.objects.count()), (11, 10, 0))

    def test_los_vuelos_de_ejemplo_usan_los_primeros_cuatro_aviones(self):
        self.correr()
        usados = set(Vuelo.objects.values_list('avion__matricula', flat=True))
        self.assertLessEqual(usados, {'LV-FAA', 'LV-FAB', 'LV-FAC', 'LV-FAD'})
```

- [ ] **Step 2: Ver que fallan**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos.tests.SeedTests`
Expected: FAIL (`TypeError` por el argumento `vuelos` desconocido).

- [ ] **Step 3: Implementar**

En `seed.py`, reemplazar el docstring del módulo y `FLOTA`:

```python
"""Catálogo (aeropuertos, flota, usuario sistema) y, con --vuelos, vuelos de ejemplo. Idempotente.

El catálogo corre en build.sh porque aeropuertos y aviones no tienen ABM.
Los vuelos los carga el administrador; --vuelos queda para desarrollo local.
Solo crea lo que falta: no pisa correcciones hechas desde el admin.
"""
```

```python
FLOTA = [
    ('LV-FAA', 'Airbus A320', 150, 12),
    ('LV-FAB', 'Boeing 737-800', 162, 12),
    ('LV-FAC', 'Embraer E190', 96, 8),
    ('LV-FAD', 'Airbus A330-200', 250, 24),
    ('LV-FAE', 'Airbus A320', 150, 12),
    ('LV-FAF', 'Boeing 737-800', 162, 12),
    ('LV-FAG', 'Embraer E190', 96, 8),
    ('LV-FAH', 'Airbus A321', 190, 16),
    ('LV-FAI', 'Boeing 737 MAX 8', 170, 12),
    ('LV-FAJ', 'Embraer E195-E2', 120, 12),
]
AVIONES_DE_EJEMPLO = 4  # los vuelos de ejemplo no validan avión libre: el resto de la flota queda sin ocupar
```

Reemplazar `help`, `add_arguments` y la firma de `handle`:

```python
    help = 'Carga aeropuertos y flota; con --vuelos, también vuelos de ejemplo (no pisa lo que ya existe).'

    def add_arguments(self, parser):
        parser.add_argument('--vuelos', action='store_true', help='Agrega vuelos de ejemplo (desarrollo local).')
        parser.add_argument('--dias', type=int, default=60, help='Días hacia adelante con vuelos (default 60).')

    def handle(self, *args, dias, vuelos, **opciones):
```

Dentro de `handle`, renombrar la lista local `vuelos = []` a `nuevos = []` (y sus dos usos: `nuevos.append(...)` y `bulk_create(nuevos, ...)`), y envolver la generación para que solo corra con el flag. Justo después de armar `aviones`:

```python
        if vuelos:
            self.cargar_vuelos(sistema, aeropuertos, aviones[:AVIONES_DE_EJEMPLO], dias)
        self.stdout.write(self.style.SUCCESS(
            f'Seed listo: {len(aeropuertos)} aeropuertos, {len(aviones)} aviones, {Vuelo.objects.count()} vuelos.'
        ))

    def cargar_vuelos(self, sistema, aeropuertos, aviones, dias):
        hoy = timezone.localdate()
        nuevos = []
```

El resto del cuerpo (los bucles por ruta y fecha y el `bulk_create`) queda igual dentro de `cargar_vuelos`, sin el `self.stdout.write` final, que ya está en `handle`.

En `backend/build.sh`, reemplazar las dos últimas líneas por:

```bash
# Catálogo (aeropuertos, flota): no tiene ABM. Los vuelos los carga el administrador.
python manage.py seed
```

- [ ] **Step 4: Correr los tests**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos.tests.SeedTests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/vuelos/management/commands/seed.py backend/vuelos/tests.py backend/build.sh
git commit -m "feat(backend): seed carga el catálogo y la flota de 10; vuelos de ejemplo solo con --vuelos"
```

---

### Task 4: Alta con recurrencia (US01)

**Files:**
- Create: `backend/vuelos/permissions.py`
- Create: `backend/vuelos/servicios.py`
- Modify: `backend/vuelos/serializers.py`, `backend/vuelos/views.py`, `backend/vuelos/urls.py`
- Test: `backend/vuelos/tests.py`

**Interfaces:**
- Produces (Python):
  - `vuelos.permissions.EsAdministrador`
  - `vuelos.servicios.fechas_de_periodo(desde: date, hasta: date, dias: list[int]) -> list[date]`
  - `vuelos.servicios.fecha_llegada_de(fecha: date, hora_partida: time, hora_llegada: time) -> date`
  - `vuelos.servicios.ya_salio(vuelo) -> bool`
  - `vuelos.servicios.errores_de_ruta_y_horas(origen, destino, hora_partida, hora_llegada) -> dict[str, str]`
  - `vuelos.servicios.choque_de_avion(vuelos: list[Vuelo], excluir=None) -> str | None` (mensaje del primer choque)
  - `vuelos.servicios.error_general(mensaje: str) -> serializers.ValidationError` (cuerpo `{"non_field_errors": [mensaje]}`)
  - `vuelos.servicios.crear_vuelos(datos: dict, usuario) -> tuple[str, int]`
  - Ayudantes de tests: clase `AdminDatos(Datos)` con `self.pasajero`, `self.empleado`, `self.avion2` y `self.solo_admin(metodo, url)`.
- Produces (HTTP): `POST /api/vuelos/` → 201 `{"numero_vuelo": "FA 1000", "cantidad": 4}`.

- [ ] **Step 1: Tests**

En `backend/vuelos/tests.py`, mover la constante `MANANA = HOY + dt.timedelta(days=1)` arriba, junto a `HOY`, y agregar al final:

```python
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
            errores = self.rechaza(self.datos(periodos=[self.periodo(**cambios)]))['periodos'][0]
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
```

- [ ] **Step 2: Ver que fallan**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos.tests.AltaTests`
Expected: FAIL (el `POST /api/vuelos/` responde 404: la ruta no existe).

- [ ] **Step 3: Permiso**

Crear `backend/vuelos/permissions.py`:

```python
from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    """El ABM es del rol administrador. Sin sesión, DRF responde 401; con otro rol, 403."""

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol == 'administrador')
```

- [ ] **Step 4: Servicios**

Crear `backend/vuelos/servicios.py`:

```python
"""Reglas del ABM de vuelos (docs/superpowers/specs/2026-10-03-abm-vuelos-design.md)."""
import datetime as dt
from collections import defaultdict

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Avion, Vuelo

UN_DIA = dt.timedelta(days=1)


def fechas_de_periodo(desde, hasta, dias):
    """Fechas de `desde` a `hasta` (inclusive) que caen en `dias` (0 = lunes ... 6 = domingo)."""
    rango = (desde + dt.timedelta(days=n) for n in range((hasta - desde).days + 1))
    return [fecha for fecha in rango if fecha.weekday() in dias]


def fecha_llegada_de(fecha, hora_partida, hora_llegada):
    """Si llega más temprano de lo que sale, llega al día siguiente."""
    return fecha + UN_DIA if hora_llegada < hora_partida else fecha


def ya_salio(vuelo):
    ahora = timezone.localtime()  # hora de Buenos Aires (TIME_ZONE)
    return (vuelo.fecha_operacion, vuelo.hora_partida) <= (ahora.date(), ahora.time())


def error_general(mensaje):
    return serializers.ValidationError({'non_field_errors': [mensaje]})


def exigir_modificable(vuelo):
    if vuelo.estado == Vuelo.Estado.CANCELADO:
        raise error_general('El vuelo ya está cancelado.')
    if ya_salio(vuelo):
        raise error_general('El vuelo ya salió.')


def errores_de_ruta_y_horas(origen, destino, hora_partida, hora_llegada):
    errores = {}
    if origen == destino:
        errores['destino'] = 'El destino tiene que ser distinto del origen.'
    elif origen.ciudad == destino.ciudad:
        errores['destino'] = 'Origen y destino están en la misma ciudad.'
    if hora_partida == hora_llegada:
        errores['hora_llegada'] = 'La llegada no puede ser a la misma hora que la partida.'
    return errores


def siguiente_numero():
    # ponytail: recorre los números distintos (cientos); pasar a una secuencia de la base si crecen mucho.
    usados = Vuelo.objects.order_by().values_list('numero_vuelo', flat=True).distinct()
    numeros = [int(n[3:]) for n in usados if n.startswith('FA ') and n[3:].isdigit()]
    return f'FA {max(numeros, default=999) + 1}'


def _intervalo(vuelo):
    return (
        dt.datetime.combine(vuelo.fecha_operacion, vuelo.hora_partida),
        dt.datetime.combine(vuelo.fecha_llegada, vuelo.hora_llegada),
    )


def choque_de_avion(vuelos, excluir=None):
    """Mensaje del primer vuelo activo que usa el mismo avión en un horario superpuesto, o None.

    `vuelos` pueden no estar guardados. `excluir` es el id del vuelo que se está editando.
    No contempla rotación ni dónde está el avión (fuera de alcance).
    """
    por_avion = defaultdict(list)
    for vuelo in vuelos:
        por_avion[vuelo.avion_id].append(vuelo)
    for avion_id, propios in por_avion.items():
        fechas = [v.fecha_operacion for v in propios]
        # Un día de margen a cada lado: un vuelo puede cruzar medianoche.
        existentes = Vuelo.objects.filter(
            avion_id=avion_id,
            estado=Vuelo.Estado.ACTIVO,
            fecha_operacion__range=(min(fechas) - UN_DIA, max(fechas) + UN_DIA),
        )
        if excluir:
            existentes = existentes.exclude(pk=excluir)
        por_fecha = defaultdict(list)
        for existente in existentes:
            por_fecha[existente.fecha_operacion].append(existente)
        for vuelo in propios:
            sale, llega = _intervalo(vuelo)
            for fecha in (vuelo.fecha_operacion - UN_DIA, vuelo.fecha_operacion, vuelo.fecha_operacion + UN_DIA):
                for otro in por_fecha[fecha]:
                    otro_sale, otro_llega = _intervalo(otro)
                    if sale < otro_llega and otro_sale < llega:
                        return (
                            f'{vuelo.avion.matricula} ya está asignado al {otro.numero_vuelo} '
                            f'el {otro.fecha_operacion} de {otro.hora_partida:%H:%M} a {otro.hora_llegada:%H:%M}.'
                        )
    return None


@transaction.atomic
def crear_vuelos(datos, usuario):
    """Una fila por fecha de cada período, todas o ninguna. Devuelve (numero_vuelo, cantidad).

    `datos` es el `validated_data` de AltaVueloSerializer (cada período trae sus `fechas`).
    """
    # Lock sobre los aviones: el chequeo de avión libre y el alta son una sola operación.
    list(Avion.objects.select_for_update().filter(pk__in={p['avion'].pk for p in datos['periodos']}))
    numero = siguiente_numero()
    vuelos = [
        Vuelo(
            numero_vuelo=numero,
            avion=periodo['avion'],
            aeropuerto_origen=datos['origen'],
            aeropuerto_destino=datos['destino'],
            fecha_operacion=fecha,
            fecha_llegada=fecha_llegada_de(fecha, datos['hora_partida'], datos['hora_llegada']),
            hora_partida=datos['hora_partida'],
            hora_llegada=datos['hora_llegada'],
            precio_economy=periodo['precio_economy'],
            precio_primera=periodo['precio_primera'],
            asientos_disponibles_economy=periodo['avion'].capacidad_economy,
            asientos_disponibles_primera=periodo['avion'].capacidad_primera,
            creado_por=usuario,
        )
        for periodo in datos['periodos']
        for fecha in periodo['fechas']
    ]
    choque = choque_de_avion(vuelos)
    if choque:
        raise error_general(choque)
    Vuelo.objects.bulk_create(vuelos, batch_size=1000)
    return numero, len(vuelos)
```

- [ ] **Step 5: Serializers del alta**

En `backend/vuelos/serializers.py`, sumar a los imports:

```python
import datetime as dt
from collections import Counter
from decimal import Decimal

from .servicios import errores_de_ruta_y_horas, fechas_de_periodo
```

y agregar al final:

```python
def _aeropuerto():
    return serializers.SlugRelatedField(
        slug_field='codigo_iata',
        queryset=Aeropuerto.objects.all(),
        error_messages={'does_not_exist': 'No conocemos el aeropuerto "{value}".'},
    )


def _precio():
    return serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
        error_messages={'min_value': 'El precio tiene que ser mayor a cero.'},
    )


MAX_DIAS_ADELANTE = 365


class PeriodoSerializer(serializers.Serializer):
    desde = serializers.DateField()
    hasta = serializers.DateField()
    dias = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6), allow_empty=False)
    avion = serializers.PrimaryKeyRelatedField(queryset=Avion.objects.all())
    precio_economy = _precio()
    precio_primera = _precio()

    def validate(self, periodo):
        hoy = timezone.localdate()
        errores = {}
        if periodo['desde'] < hoy:
            errores['desde'] = 'La fecha no puede ser en el pasado.'
        if periodo['hasta'] < periodo['desde']:
            errores['hasta'] = '"Hasta" no puede ser antes de "Desde".'
        elif periodo['hasta'] > hoy + dt.timedelta(days=MAX_DIAS_ADELANTE):
            errores['hasta'] = 'El período no puede pasar de un año desde hoy.'
        else:
            periodo['fechas'] = fechas_de_periodo(periodo['desde'], periodo['hasta'], periodo['dias'])
            if not periodo['fechas']:
                errores['dias'] = 'Ningún día del rango cae en los días elegidos.'
        if errores:
            raise serializers.ValidationError(errores)
        return periodo


class AltaVueloSerializer(serializers.Serializer):
    """Cuerpo de POST /vuelos/. Lo común al alta y sus períodos; cada período sale con sus `fechas`."""

    origen = _aeropuerto()
    destino = _aeropuerto()
    hora_partida = serializers.TimeField()
    hora_llegada = serializers.TimeField()
    periodos = PeriodoSerializer(many=True, allow_empty=False)

    def validate(self, datos):
        errores = errores_de_ruta_y_horas(
            datos['origen'], datos['destino'], datos['hora_partida'], datos['hora_llegada']
        )
        veces = Counter(fecha for periodo in datos['periodos'] for fecha in periodo['fechas'])
        ahora = timezone.localtime()
        if ahora.date() in veces and datos['hora_partida'] <= ahora.time():
            errores['hora_partida'] = 'Ese horario ya pasó para hoy.'
        if errores:
            raise serializers.ValidationError(errores)
        repetidas = sorted(fecha for fecha, n in veces.items() if n > 1)
        if repetidas:
            raise serializers.ValidationError(
                f'Hay fechas repetidas entre períodos: {", ".join(map(str, repetidas))}.'
            )
        return datos
```

- [ ] **Step 6: Vista y ruta**

En `backend/vuelos/views.py`, sumar a los imports:

```python
from django.db import IntegrityError

from .permissions import EsAdministrador
from .serializers import AltaVueloSerializer
from .servicios import crear_vuelos, error_general
```

y agregar la vista:

```python
class VuelosView(generics.GenericAPIView):
    """ABM de vuelos del administrador: alta con recurrencia (el listado se suma en el GET)."""

    permission_classes = [EsAdministrador]

    def post(self, request):
        alta = AltaVueloSerializer(data=request.data)
        alta.is_valid(raise_exception=True)
        try:
            numero, cantidad = crear_vuelos(alta.validated_data, request.user)
        except IntegrityError:
            # Dos altas a la vez tomaron el mismo número: el índice único frena a la segunda.
            raise error_general('No se pudo asignar el número de vuelo. Probá de nuevo.')
        return Response({'numero_vuelo': numero, 'cantidad': cantidad}, status=201)
```

En `backend/vuelos/urls.py`, agregar antes de `vuelos/buscar/`:

```python
    path('vuelos/', views.VuelosView.as_view()),
```

- [ ] **Step 7: Correr los tests**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos`
Expected: PASS (todos).

- [ ] **Step 8: Commit**

```bash
git add backend/vuelos
git commit -m "feat(backend): alta de vuelos con recurrencia y avión libre (US01)"
```

---

### Task 5: Listado del administrador y catálogo de aviones

**Files:**
- Modify: `backend/vuelos/serializers.py`, `backend/vuelos/views.py`, `backend/vuelos/urls.py`
- Test: `backend/vuelos/tests.py`

**Interfaces:**
- Consumes: `EsAdministrador`, `AdminDatos` (Task 4).
- Produces (HTTP):
  - `GET /api/vuelos/?q=&origen=&destino=&desde=&hasta=&estado=&page=` → `{"count", "next", "previous", "results": [vuelo con avion]}`, 50 por página.
  - `GET /api/aviones/` → `[{"id", "matricula", "modelo", "capacidad_economy", "capacidad_primera"}]`.
  - El `avion` anidado en el detalle y el listado pasa a tener esos cinco campos.

- [ ] **Step 1: Tests**

En `DetalleTests.test_detalle_con_avion_y_forma_de_la_api`, reemplazar la aserción del avión:

```python
        self.assertEqual(d['avion'], {
            'id': str(self.avion.id), 'matricula': 'LV-FAA', 'modelo': 'Airbus A320',
            'capacidad_economy': 150, 'capacidad_primera': 12,
        })
```

Agregar al final de `tests.py`:

```python
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
```

- [ ] **Step 2: Ver que fallan**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos.tests.ListadoTests vuelos.tests.DetalleTests`
Expected: FAIL (`GET /api/vuelos/` responde 405 y `/api/aviones/` 404).

- [ ] **Step 3: Serializers**

En `backend/vuelos/serializers.py`, reemplazar `AvionSerializer.Meta.fields`:

```python
        fields = ['id', 'matricula', 'modelo', 'capacidad_economy', 'capacidad_primera']
```

y agregar debajo de `BusquedaSerializer`:

```python
class FiltrosListadoSerializer(serializers.Serializer):
    """Parámetros de GET /vuelos/ (listado del administrador). Todos opcionales."""

    q = serializers.CharField(required=False)
    origen = serializers.CharField(required=False)
    destino = serializers.CharField(required=False)
    desde = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid'))
    hasta = serializers.DateField(required=False, error_messages=_errores(FECHA_INVALIDA, 'invalid'))
    estado = serializers.ChoiceField(choices=Vuelo.Estado.choices, required=False)
```

- [ ] **Step 4: Vistas y rutas**

En `backend/vuelos/views.py`, sumar a los imports `import uuid`, `from rest_framework.pagination import PageNumberPagination`, `from .models import Avion`, `AvionSerializer` y `FiltrosListadoSerializer`. Agregar:

```python
class Paginacion(PageNumberPagination):
    page_size = 50


class AvionesView(generics.ListAPIView):
    permission_classes = [EsAdministrador]
    queryset = Avion.objects.order_by('matricula')
    serializer_class = AvionSerializer
```

Cambiar `VuelosView` para que herede de `generics.ListAPIView` (el `post` queda igual) y sumarle:

```python
class VuelosView(generics.ListAPIView):
    """ABM de vuelos del administrador: listado paginado con filtros y alta con recurrencia."""

    permission_classes = [EsAdministrador]
    serializer_class = VueloDetalleSerializer
    pagination_class = Paginacion

    def get_queryset(self):
        filtros = FiltrosListadoSerializer(data={k: v for k, v in self.request.query_params.items() if v != ''})
        filtros.is_valid(raise_exception=True)
        f = filtros.validated_data
        vuelos = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino').order_by(
            'fecha_operacion', 'hora_partida', 'numero_vuelo'
        )
        q = f.get('q')
        if q:
            try:
                vuelos = vuelos.filter(pk=uuid.UUID(q))
            except ValueError:
                vuelos = vuelos.filter(numero_vuelo__icontains=q)
        # Sin `desde` ni `q`, desde hoy; con `q` se busca en todas las fechas (un id puede ser de un vuelo pasado).
        desde = f.get('desde') or (None if q else timezone.localdate())
        if desde:
            vuelos = vuelos.filter(fecha_operacion__gte=desde)
        if 'hasta' in f:
            vuelos = vuelos.filter(fecha_operacion__lte=f['hasta'])
        if 'estado' in f:
            vuelos = vuelos.filter(estado=f['estado'])
        if 'origen' in f:
            vuelos = vuelos.filter(aeropuerto_origen__codigo_iata=f['origen'].upper())
        if 'destino' in f:
            vuelos = vuelos.filter(aeropuerto_destino__codigo_iata=f['destino'].upper())
        return vuelos
```

En `backend/vuelos/urls.py`, agregar:

```python
    path('aviones/', views.AvionesView.as_view()),
```

- [ ] **Step 5: Correr los tests**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/vuelos
git commit -m "feat(backend): listado de vuelos del administrador y catálogo de aviones"
```

---

### Task 6: Edición (US02) y cancelación (US03)

**Files:**
- Modify: `backend/vuelos/serializers.py`, `backend/vuelos/views.py`, `backend/vuelos/urls.py`
- Test: `backend/vuelos/tests.py`

**Interfaces:**
- Consumes: `exigir_modificable`, `choque_de_avion`, `fecha_llegada_de`, `errores_de_ruta_y_horas`, `EsAdministrador`, `AdminDatos`.
- Produces (HTTP):
  - `PATCH /api/vuelos/{id}/` con cualquier subconjunto de `fecha_operacion`, `hora_partida`, `hora_llegada`, `origen` (IATA), `destino` (IATA), `avion` (id), `precio_economy`, `precio_primera` → 200 con el vuelo (forma del detalle).
  - `POST /api/vuelos/{id}/cancelar/` → 200 con el vuelo, `estado: "cancelado"`.
  - `GET /api/vuelos/{id}/` sigue público.

- [ ] **Step 1: Tests**

Agregar al final de `tests.py`:

```python
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
```

- [ ] **Step 2: Ver que fallan**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos.tests.EdicionTests vuelos.tests.CancelacionTests`
Expected: FAIL (`PATCH` responde 405 y `/cancelar/` 404).

- [ ] **Step 3: Serializer de edición**

En `backend/vuelos/serializers.py`, sumar `choque_de_avion` y `fecha_llegada_de` al import de `.servicios` y agregar al final:

```python
CLASES = ('economy', 'primera')


class EdicionVueloSerializer(serializers.Serializer):
    """Cuerpo de PATCH /vuelos/<id>/ (siempre parcial). Lo que no se manda queda como está.

    numero_vuelo, estado, asientos y fecha_llegada no son campos: si llegan, se ignoran.
    """

    fecha_operacion = serializers.DateField()
    hora_partida = serializers.TimeField()
    hora_llegada = serializers.TimeField()
    origen = _aeropuerto()
    destino = _aeropuerto()
    avion = serializers.PrimaryKeyRelatedField(queryset=Avion.objects.all())
    precio_economy = _precio()
    precio_primera = _precio()

    def _asientos(self, avion):
        """Asientos disponibles por clase si el vuelo pasara a `avion`: capacidad nueva menos vendidos."""
        vuelo = self.instance
        return {
            clase: getattr(avion, f'capacidad_{clase}')
            - (getattr(vuelo.avion, f'capacidad_{clase}') - getattr(vuelo, f'asientos_disponibles_{clase}'))
            for clase in CLASES
        }

    def validate(self, datos):
        vuelo = self.instance
        fecha = datos.get('fecha_operacion', vuelo.fecha_operacion)
        partida = datos.get('hora_partida', vuelo.hora_partida)
        llegada = datos.get('hora_llegada', vuelo.hora_llegada)
        avion = datos.get('avion', vuelo.avion)
        errores = errores_de_ruta_y_horas(
            datos.get('origen', vuelo.aeropuerto_origen), datos.get('destino', vuelo.aeropuerto_destino), partida, llegada
        )
        ahora = timezone.localtime()
        if (fecha, partida) <= (ahora.date(), ahora.time()):
            errores['fecha_operacion'] = 'La partida tiene que ser en el futuro.'
        elif fecha > ahora.date() + dt.timedelta(days=MAX_DIAS_ADELANTE):
            errores['fecha_operacion'] = 'La fecha no puede pasar de un año desde hoy.'
        elif Vuelo.objects.filter(numero_vuelo=vuelo.numero_vuelo, fecha_operacion=fecha).exclude(pk=vuelo.pk).exists():
            errores['fecha_operacion'] = f'El {vuelo.numero_vuelo} ya tiene un vuelo ese día.'
        if avion != vuelo.avion and min(self._asientos(avion).values()) < 0:
            errores['avion'] = 'Ese avión no tiene lugar para los pasajes ya vendidos.'
        if errores:
            raise serializers.ValidationError(errores)
        candidato = Vuelo(
            avion=avion, fecha_operacion=fecha, fecha_llegada=fecha_llegada_de(fecha, partida, llegada),
            hora_partida=partida, hora_llegada=llegada,
        )
        choque = choque_de_avion([candidato], excluir=vuelo.pk)
        if choque:
            raise serializers.ValidationError(choque)
        return datos

    def update(self, vuelo, datos):
        avion = datos.get('avion', vuelo.avion)
        if avion != vuelo.avion:
            for clase, asientos in self._asientos(avion).items():
                setattr(vuelo, f'asientos_disponibles_{clase}', asientos)
            vuelo.avion = avion
        vuelo.aeropuerto_origen = datos.get('origen', vuelo.aeropuerto_origen)
        vuelo.aeropuerto_destino = datos.get('destino', vuelo.aeropuerto_destino)
        for campo in ('fecha_operacion', 'hora_partida', 'hora_llegada', 'precio_economy', 'precio_primera'):
            setattr(vuelo, campo, datos.get(campo, getattr(vuelo, campo)))
        vuelo.fecha_llegada = fecha_llegada_de(vuelo.fecha_operacion, vuelo.hora_partida, vuelo.hora_llegada)
        vuelo.save()
        return vuelo
```

- [ ] **Step 4: Vistas y ruta**

En `backend/vuelos/views.py`, sumar a los imports `from django.db import transaction`, `EdicionVueloSerializer` y `exigir_modificable`. Reemplazar `VueloDetalleView` y agregar `CancelarVueloView`:

```python
VUELOS_CON_RELACIONES = Vuelo.objects.select_related('avion', 'aeropuerto_origen', 'aeropuerto_destino')


class VueloDetalleView(generics.RetrieveAPIView):
    """GET público (incluye cancelados: el detalle informa la cancelación). PATCH solo del administrador.

    Un id que no es UUID da 404 (no 500).
    """

    serializer_class = VueloDetalleSerializer

    def get_queryset(self):
        if self.request.method == 'PATCH':
            return VUELOS_CON_RELACIONES.select_for_update(of=('self',))
        return VUELOS_CON_RELACIONES

    def get_permissions(self):
        return [EsAdministrador()] if self.request.method == 'PATCH' else super().get_permissions()

    @transaction.atomic
    def patch(self, request, *args, **kwargs):
        vuelo = self.get_object()
        exigir_modificable(vuelo)
        edicion = EdicionVueloSerializer(vuelo, data=request.data, partial=True)
        edicion.is_valid(raise_exception=True)
        edicion.save()
        return Response(VueloDetalleSerializer(vuelo).data)


class CancelarVueloView(generics.GenericAPIView):
    """Cancela una instancia: cambia el estado, no borra la fila (US03)."""

    permission_classes = [EsAdministrador]
    queryset = VUELOS_CON_RELACIONES.select_for_update(of=('self',))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        vuelo = self.get_object()
        exigir_modificable(vuelo)
        vuelo.estado = Vuelo.Estado.CANCELADO
        vuelo.save(update_fields=['estado', 'actualizado_en'])
        return Response(VueloDetalleSerializer(vuelo).data)
```

En `VuelosView.get_queryset`, usar `VUELOS_CON_RELACIONES.order_by(...)` en lugar de repetir el `select_related`.

En `backend/vuelos/urls.py`, agregar antes de `vuelos/<str:pk>/`:

```python
    path('vuelos/<str:pk>/cancelar/', views.CancelarVueloView.as_view()),
```

- [ ] **Step 5: Correr los tests**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test vuelos usuarios`
Expected: PASS (todo el backend).

- [ ] **Step 6: Commit**

```bash
git add backend/vuelos
git commit -m "feat(backend): editar y cancelar una instancia de vuelo (US02, US03)"
```

---

### Task 7: Cliente del ABM en el frontend

**Files:**
- Modify: `frontend/src/lib/vuelos.ts` (`interface Avion`)
- Create: `frontend/src/lib/adminVuelos.ts`
- Test: `frontend/scripts/check.ts`

**Interfaces:**
- Consumes: endpoints de las Tasks 4, 5 y 6; `api`, `ApiError` de `./api.ts`; `VueloDetalle`, `Avion` de `./vuelos.ts`.
- Produces (TypeScript, todo exportado desde `adminVuelos.ts`):
  - `interface Pagina<T> { count: number; next: string | null; previous: string | null; results: T[] }`
  - `interface FiltrosAdmin { q: string; origen: string; destino: string; desde: string; hasta: string; estado: string; page: number }`
  - `interface Periodo { desde: string; hasta: string; dias: number[]; avion: string; precio_economy: string; precio_primera: string }`
  - `interface AltaVuelo { origen: string; destino: string; hora_partida: string; hora_llegada: string; periodos: Periodo[] }`
  - `interface EdicionVuelo { fecha_operacion: string; hora_partida: string; hora_llegada: string; origen: string; destino: string; avion: string; precio_economy: string; precio_primera: string }`
  - `type ErroresApi = Record<string, unknown>`
  - `DIAS: string[]`, `fechasDePeriodo(desde, hasta, dias): string[]`, `queryListado(f): URLSearchParams`, `yaSalio(v, ahora?): boolean`, `erroresDe(e): ErroresApi`, `primero(valor): string`
  - `listarVuelos(f)`, `getAviones()`, `crearVuelos(alta)`, `editarVuelo(id, cambios)`, `cancelarVuelo(id)`

- [ ] **Step 1: Chequeos que fallan**

En `frontend/scripts/check.ts`, agregar el import:

```ts
import { erroresDe, fechasDePeriodo, primero, queryListado, yaSalio } from '../src/lib/adminVuelos.ts'
import { ApiError } from '../src/lib/api.ts'
```

y al final del archivo:

```ts
// adminVuelos: fechas de un período (0 = lunes ... 6 = domingo, como el backend)
assert.deepEqual(
  fechasDePeriodo('2026-10-21', '2026-11-03', [0, 2]),
  ['2026-10-21', '2026-10-26', '2026-10-28', '2026-11-02'],
  'lunes y miércoles',
)
assert.deepEqual(fechasDePeriodo('2026-10-25', '2026-10-25', [6]), ['2026-10-25'], 'domingo = 6')
assert.deepEqual(fechasDePeriodo('2026-10-21', '2026-10-21', [0]), [], 'ningún día cae en el rango')
assert.deepEqual(fechasDePeriodo('', '2026-10-21', [0]), [], 'sin fecha')
assert.deepEqual(fechasDePeriodo('2026-10-22', '2026-10-21', [0, 1, 2, 3, 4, 5, 6]), [], 'rango al revés')
assert.equal(fechasDePeriodo('2026-01-01', '2026-12-31', [0, 1, 2, 3, 4, 5, 6]).length, 365)

const filtrosAdmin = { q: '', origen: '', destino: '', desde: '', hasta: '', estado: '', page: 1 }
assert.equal(queryListado(filtrosAdmin).toString(), '', 'sin filtros')
assert.equal(
  queryListado({ ...filtrosAdmin, q: 'FA 1432', origen: 'BHI', estado: 'cancelado', page: 3 }).toString(),
  'q=FA+1432&origen=BHI&estado=cancelado&page=3',
)

const partida = { fecha_operacion: '2026-10-21', hora_partida: '15:00:00' }
assert.equal(yaSalio(partida, new Date('2026-10-21T14:59:00')), false)
assert.equal(yaSalio(partida, new Date('2026-10-21T15:00:00')), true)

const e400 = new ApiError(400, { origen: ['No conocemos el aeropuerto "ZZZ".'], periodos: [{}, { desde: ['x'] }] })
assert.equal(primero(erroresDe(e400).origen), 'No conocemos el aeropuerto "ZZZ".')
assert.equal(primero(erroresDe(e400).destino), '')
assert.deepEqual(erroresDe(new ApiError(500, 'boom')), {})
assert.deepEqual(erroresDe(new Error('red')), {})

console.log('adminVuelos: OK')
```

- [ ] **Step 2: Ver que falla**

Run: `cd frontend && npm run check`
Expected: FAIL (no existe `src/lib/adminVuelos.ts`).

- [ ] **Step 3: Implementar**

En `frontend/src/lib/vuelos.ts`, reemplazar `interface Avion`:

```ts
export interface Avion {
  id: string
  matricula: string
  modelo: string
  capacidad_economy: number
  capacidad_primera: number
}
```

Crear `frontend/src/lib/adminVuelos.ts`:

```ts
import { api, ApiError } from './api.ts'
import type { Avion, VueloDetalle } from './vuelos.ts'

// ABM de vuelos del administrador. Nombres de la API (docs/modelo.dbml).

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** Filtros de GET /vuelos/. '' = sin filtrar. `q` = id del vuelo o parte del número. */
export interface FiltrosAdmin {
  q: string
  origen: string
  destino: string
  desde: string
  hasta: string
  estado: string
  page: number
}

export interface Periodo {
  desde: string
  hasta: string
  dias: number[] // 0 = lunes ... 6 = domingo
  avion: string // id
  precio_economy: string
  precio_primera: string
}

export interface AltaVuelo {
  origen: string // código IATA
  destino: string
  hora_partida: string
  hora_llegada: string
  periodos: Periodo[]
}

export interface EdicionVuelo {
  fecha_operacion: string
  hora_partida: string
  hora_llegada: string
  origen: string
  destino: string
  avion: string
  precio_economy: string
  precio_primera: string
}

/** Cuerpo de un 400 de DRF: { campo: ["mensaje"], periodos: [{ campo: ["mensaje"] }], non_field_errors: ["mensaje"] } */
export type ErroresApi = Record<string, unknown>

export const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

const dosDigitos = (n: number) => String(n).padStart(2, '0')
const aISO = (d: Date) => `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(d.getDate())}`

/** Fechas de `desde` a `hasta` (inclusive) que caen en `dias`. La misma regla que el backend, para la vista previa. */
export function fechasDePeriodo(desde: string, hasta: string, dias: number[]): string[] {
  if (!desde || !hasta) return []
  const fechas: string[] = []
  const fin = new Date(`${hasta}T00:00:00`) // hora local, no UTC
  // ponytail: tope de 400 vueltas; el backend rechaza períodos de más de un año.
  for (let d = new Date(`${desde}T00:00:00`), n = 0; d <= fin && n < 400; d.setDate(d.getDate() + 1), n++) {
    if (dias.includes((d.getDay() + 6) % 7)) fechas.push(aISO(d))
  }
  return fechas
}

/** Query string de GET /vuelos/. Omite lo vacío y la página 1. */
export function queryListado(f: FiltrosAdmin): URLSearchParams {
  const q = new URLSearchParams()
  for (const clave of ['q', 'origen', 'destino', 'desde', 'hasta', 'estado'] as const) {
    if (f[clave]) q.set(clave, f[clave])
  }
  if (f.page > 1) q.set('page', String(f.page))
  return q
}

/** ponytail: usa el reloj del navegador (se asume hora de Argentina); solo deshabilita botones, el backend decide. */
export function yaSalio(v: { fecha_operacion: string; hora_partida: string }, ahora = new Date()): boolean {
  return new Date(`${v.fecha_operacion}T${v.hora_partida}`) <= ahora
}

export function erroresDe(e: unknown): ErroresApi {
  return e instanceof ApiError && e.status === 400 && e.data !== null && typeof e.data === 'object'
    ? (e.data as ErroresApi)
    : {}
}

/** Primer mensaje de un campo de ErroresApi; '' si no hay. */
export const primero = (valor: unknown): string => (Array.isArray(valor) && typeof valor[0] === 'string' ? valor[0] : '')

export const listarVuelos = (f: FiltrosAdmin) => api<Pagina<VueloDetalle>>(`/vuelos/?${queryListado(f)}`)

export const getAviones = () => api<Avion[]>('/aviones/')

export const crearVuelos = (alta: AltaVuelo) =>
  api<{ numero_vuelo: string; cantidad: number }>('/vuelos/', { method: 'POST', body: JSON.stringify(alta) })

export const editarVuelo = (id: string, cambios: Partial<EdicionVuelo>) =>
  api<VueloDetalle>(`/vuelos/${encodeURIComponent(id)}/`, { method: 'PATCH', body: JSON.stringify(cambios) })

export const cancelarVuelo = (id: string) =>
  api<VueloDetalle>(`/vuelos/${encodeURIComponent(id)}/cancelar/`, { method: 'POST' })
```

- [ ] **Step 4: Verificar**

Run: `cd frontend && npm run check && npm run build && npm run lint`
Expected: los tres pasan; `npm run check` imprime `adminVuelos: OK`.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): cliente del ABM de vuelos"
```

---

### Task 8: Listado y cancelación en `/admin/vuelos`

**Files:**
- Create: `frontend/src/pages/AdminVuelos.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `listarVuelos`, `cancelarVuelo`, `yaSalio`, `FiltrosAdmin`, `Pagina` (Task 7); `getAeropuertos`, `llegaAlDiaSiguiente`, `VueloDetalle`, `Aeropuerto`; `fechaCorta`, `hora`, `precio` de `lib/formato`.
- Produces: página `AdminVuelos` (export default). Enlaza a `/admin/vuelos/nuevo` y `/admin/vuelos/:id` (Task 9). Los filtros viven en la query string (`q`, `origen`, `destino`, `desde`, `hasta`, `estado`, `page`).

- [ ] **Step 1: Página**

Crear `frontend/src/pages/AdminVuelos.tsx`:

```tsx
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { cancelarVuelo, listarVuelos, yaSalio, type FiltrosAdmin, type Pagina } from '../lib/adminVuelos'
import { fechaCorta, hora, precio } from '../lib/formato'
import { getAeropuertos, llegaAlDiaSiguiente, type Aeropuerto, type VueloDetalle } from '../lib/vuelos'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20'
const ICONO = 'grid h-9 w-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-marino aria-disabled:pointer-events-none aria-disabled:opacity-30 disabled:cursor-not-allowed disabled:opacity-30'

function leerFiltros(params: URLSearchParams): FiltrosAdmin {
  const texto = (clave: string) => params.get(clave) ?? ''
  return {
    q: texto('q'),
    origen: texto('origen'),
    destino: texto('destino'),
    desde: texto('desde'),
    hasta: texto('hasta'),
    estado: texto('estado'),
    page: Math.max(1, Number(params.get('page')) || 1),
  }
}

function Icono({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  )
}
const LAPIZ = 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z'
const TACHO = 'M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6'

/** Confirmación de la cancelación. Se abre al montarse; al cerrarse avisa con `onCerrar`. */
function ConfirmarCancelacion({
  vuelo,
  onCancelado,
  onCerrar,
}: {
  vuelo: VueloDetalle
  onCancelado: (v: VueloDetalle) => void
  onCerrar: () => void
}) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // StrictMode monta dos veces en desarrollo: no volver a abrir un diálogo abierto.
    const d = dialogo.current
    if (d && !d.open) d.showModal()
  }, [])

  async function confirmar() {
    setEnviando(true)
    setError('')
    try {
      onCancelado(await cancelarVuelo(vuelo.id))
      dialogo.current?.close()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo cancelar el vuelo.')
      setEnviando(false)
    }
  }

  return (
    <dialog
      ref={dialogo}
      onClose={onCerrar}
      aria-labelledby="titulo-cancelar"
      className="m-auto w-[min(32rem,calc(100%-2rem))] rounded-3xl p-6 text-slate-900 shadow-2xl backdrop:bg-marino/45 backdrop:backdrop-blur-sm"
    >
      <h2 id="titulo-cancelar" className="text-lg font-extrabold text-marino">
        ¿Cancelar el vuelo <span className="font-mono text-base break-all">{vuelo.id}</span>?
      </h2>
      <p className="mt-3 text-sm text-slate-600">
        {vuelo.numero_vuelo}, {fechaCorta(vuelo.fecha_operacion)}, {vuelo.origen.codigo_iata} → {vuelo.destino.codigo_iata},{' '}
        {hora(vuelo.hora_partida)}
      </p>
      <p className="mt-2 text-sm text-slate-600">
        Deja de ofrecerse para la compra. Los demás vuelos {vuelo.numero_vuelo} no cambian y el vuelo queda en el historial.
      </p>
      {error && <p role="alert" className="mt-3 text-sm font-medium text-red-700">{error}</p>}
      <div className="mt-6 flex justify-end gap-3">
        <button type="button" onClick={() => dialogo.current?.close()} className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-marino hover:border-cielo">
          Volver
        </button>
        <button type="button" onClick={confirmar} disabled={enviando} className="rounded-xl bg-red-700 px-5 py-2.5 font-bold text-white hover:bg-red-800 disabled:cursor-wait disabled:opacity-60">
          {enviando ? 'Cancelando…' : 'Cancelar vuelo'}
        </button>
      </div>
    </dialog>
  )
}

export default function AdminVuelos() {
  const [params, setParams] = useSearchParams()
  const clave = params.toString()
  const filtros = leerFiltros(params)
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [resultado, setResultado] = useState<{ clave: string; pagina: Pagina<VueloDetalle> | null; error: string }>({
    clave: '',
    pagina: null,
    error: '',
  })
  const [aCancelar, setACancelar] = useState<VueloDetalle | null>(null)

  useEffect(() => {
    // Sin la lista, los selectores quedan solo con "Todos": el listado funciona igual.
    getAeropuertos().then(setAeropuertos, () => {})
  }, [])

  useEffect(() => {
    let vigente = true
    listarVuelos(leerFiltros(new URLSearchParams(clave))).then(
      (pagina) => {
        if (vigente) setResultado({ clave, pagina, error: '' })
      },
      (e) => {
        if (vigente) setResultado({ clave, pagina: null, error: e instanceof Error ? e.message : 'No pudimos cargar los vuelos.' })
      },
    )
    return () => {
      vigente = false
    }
  }, [clave])

  const cargando = resultado.clave !== clave
  const { pagina, error } = resultado

  function filtrar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nuevos = new URLSearchParams()
    for (const [campo, valor] of new FormData(event.currentTarget)) {
      if (typeof valor === 'string' && valor.trim()) nuevos.set(campo, valor.trim())
    }
    setParams(nuevos) // sin `page`: un filtro nuevo vuelve a la primera página
  }

  function irAPagina(page: number) {
    const nuevos = new URLSearchParams(params)
    if (page > 1) nuevos.set('page', String(page))
    else nuevos.delete('page')
    setParams(nuevos)
  }

  function marcarCancelado(cancelado: VueloDetalle) {
    setResultado((r) =>
      r.pagina ? { ...r, pagina: { ...r.pagina, results: r.pagina.results.map((v) => (v.id === cancelado.id ? cancelado : v)) } } : r,
    )
  }

  const opciones = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <main className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold text-marino">Gestión de vuelos</h1>
        <Link to="/admin/vuelos/nuevo" className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo">
          Nuevo vuelo
        </Link>
      </div>

      {/* key: al cambiar la URL (atrás, alta nueva) el formulario toma los valores de la URL. */}
      <form key={clave} onSubmit={filtrar} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-7">
        <label className="text-sm font-semibold text-slate-700 lg:col-span-2">
          ID o número de vuelo
          <input name="q" defaultValue={filtros.q} className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Origen
          <select name="origen" defaultValue={filtros.origen} className={CAMPO}>
            <option value="">Todos</option>
            {opciones}
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Destino
          <select name="destino" defaultValue={filtros.destino} className={CAMPO}>
            <option value="">Todos</option>
            {opciones}
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Desde
          <input type="date" name="desde" defaultValue={filtros.desde} className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Hasta
          <input type="date" name="hasta" defaultValue={filtros.hasta} className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Estado
          <select name="estado" defaultValue={filtros.estado} className={CAMPO}>
            <option value="">Todos</option>
            <option value="activo">Activo</option>
            <option value="cancelado">Cancelado</option>
          </select>
        </label>
        <div className="flex gap-3 sm:col-span-2 lg:col-span-7">
          <button type="submit" className="rounded-xl bg-marino px-5 py-2 text-sm font-bold text-white hover:bg-cielo">
            Filtrar
          </button>
          <Link to="/admin/vuelos" className="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-marino hover:border-cielo">
            Limpiar
          </Link>
        </div>
      </form>

      {error && !cargando && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      {cargando && <p role="status" className="mt-6 text-sm text-slate-500">Cargando vuelos…</p>}

      {pagina && !cargando && (
        <>
          <p className="mt-6 text-sm text-slate-500">
            {pagina.count} {pagina.count === 1 ? 'vuelo' : 'vuelos'}
            {!filtros.desde && !filtros.q ? ' desde hoy' : ''}
          </p>
          <div className="mt-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <caption className="sr-only">Vuelos</caption>
              <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
                <tr>
                  {['ID', 'Número', 'Fecha', 'Ruta', 'Partida', 'Llegada', 'Avión', 'Economy', 'Primera', 'Estado', 'Acciones'].map((t) => (
                    <th key={t} scope="col" className="px-3 py-3 font-semibold">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagina.results.map((v) => {
                  const bloqueado = v.estado === 'cancelado' || yaSalio(v)
                  return (
                    <tr key={v.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-2 font-mono text-xs text-slate-500">{v.id}</td>
                      <th scope="row" className="px-3 py-2 font-bold text-marino">{v.numero_vuelo}</th>
                      <td className="px-3 py-2">{fechaCorta(v.fecha_operacion)}</td>
                      <td className="px-3 py-2">{v.origen.codigo_iata} → {v.destino.codigo_iata}</td>
                      <td className="px-3 py-2">{hora(v.hora_partida)}</td>
                      <td className="px-3 py-2">
                        {hora(v.hora_llegada)}
                        {llegaAlDiaSiguiente(v) && <sup className="ml-0.5 font-bold text-naranja" title="Llega al día siguiente">+1</sup>}
                      </td>
                      <td className="px-3 py-2">{v.avion.matricula}</td>
                      <td className="px-3 py-2">{precio(Number(v.precio_economy))}</td>
                      <td className="px-3 py-2">{precio(Number(v.precio_primera))}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${v.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                          {v.estado === 'activo' ? 'Activo' : 'Cancelado'}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <Link to={`/admin/vuelos/${v.id}`} aria-label={`Editar vuelo ${v.id}`} title={bloqueado ? 'Ver' : 'Editar'} className={ICONO}>
                            <Icono d={LAPIZ} />
                          </Link>
                          <button type="button" onClick={() => setACancelar(v)} disabled={bloqueado} aria-label={`Cancelar vuelo ${v.id}`} title="Cancelar" className={ICONO}>
                            <Icono d={TACHO} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {pagina.results.length === 0 && (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-slate-500">No hay vuelos con esos filtros.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <nav aria-label="Páginas" className="mt-4 flex items-center justify-end gap-3 text-sm">
            <button type="button" onClick={() => irAPagina(filtros.page - 1)} disabled={!pagina.previous} className="rounded-xl border border-slate-300 bg-white px-4 py-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40">
              Anterior
            </button>
            <span className="text-slate-500">Página {filtros.page}</span>
            <button type="button" onClick={() => irAPagina(filtros.page + 1)} disabled={!pagina.next} className="rounded-xl border border-slate-300 bg-white px-4 py-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40">
              Siguiente
            </button>
          </nav>
        </>
      )}

      {aCancelar && <ConfirmarCancelacion vuelo={aCancelar} onCancelado={marcarCancelado} onCerrar={() => setACancelar(null)} />}
    </main>
  )
}
```

Nota: el lápiz queda habilitado también en vuelos cancelados o que ya salieron, porque abre el formulario en solo lectura (así se cumple "consultar individualmente cada instancia"). El tacho sí se deshabilita.

- [ ] **Step 2: Ruta**

En `frontend/src/App.tsx`, agregar `import AdminVuelos from './pages/AdminVuelos'` y reemplazar el elemento de la ruta `admin/vuelos`:

```tsx
          <Route path="admin/vuelos" element={<RutaProtegida roles={['administrador']}><AdminVuelos /></RutaProtegida>} />
```

- [ ] **Step 3: Verificar**

Run: `cd frontend && npm run build && npm run lint`
Expected: ambos pasan.

Verificación manual (backend local con SQLite y datos de ejemplo):

```bash
cd backend && DATABASE_URL= .venv/Scripts/python manage.py migrate && DATABASE_URL= .venv/Scripts/python manage.py seed --vuelos --dias 10
DATABASE_URL= .venv/Scripts/python manage.py createsuperuser   # si no hay un administrador local
DATABASE_URL= .venv/Scripts/python manage.py runserver
cd frontend && npm run dev
```

Con `VITE_API_URL=http://localhost:8000/api` en `frontend/.env.local`, entrar como administrador a `http://localhost:5173/admin/vuelos` y comprobar: la tabla lista los vuelos desde hoy; filtrar por número, por ID pegado, por estado; paginar; el tacho abre la confirmación con el ID, "Volver" no cambia nada y "Cancelar vuelo" deja la fila en "Cancelado" con el tacho deshabilitado; el vuelo cancelado ya no aparece en la búsqueda de `/`.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): listado y cancelación de vuelos en /admin/vuelos"
```

---

### Task 9: Formulario de alta y de edición

**Files:**
- Create: `frontend/src/pages/AdminVueloForm.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `crearVuelos`, `editarVuelo`, `getAviones`, `fechasDePeriodo`, `erroresDe`, `primero`, `yaSalio`, `DIAS`, `Periodo`, `ErroresApi` (Task 7); `getAeropuertos`, `getVuelo`, `Aeropuerto`, `Avion`, `VueloDetalle`; `hora` de `lib/formato`.
- Produces: página `AdminVueloForm` (export default) para `/admin/vuelos/nuevo` (alta) y `/admin/vuelos/:id` (edición o solo lectura). Al guardar navega a `/admin/vuelos?q=<número o id>`.

- [ ] **Step 1: Página**

Crear `frontend/src/pages/AdminVueloForm.tsx`:

```tsx
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  DIAS,
  crearVuelos,
  editarVuelo,
  erroresDe,
  fechasDePeriodo,
  getAviones,
  primero,
  yaSalio,
  type ErroresApi,
  type Periodo,
} from '../lib/adminVuelos'
import { hora } from '../lib/formato'
import { getAeropuertos, getVuelo, type Aeropuerto, type Avion, type VueloDetalle } from '../lib/vuelos'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20 disabled:bg-slate-100'
const PERIODO_VACIO: Periodo = { desde: '', hasta: '', dias: [], avion: '', precio_economy: '', precio_primera: '' }

function Campo({ etiqueta, error, children }: { etiqueta: string; error: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {etiqueta}
      {children}
      {error && <span role="alert" className="mt-1 block text-xs font-medium text-red-700">{error}</span>}
    </label>
  )
}

/** Alta (sin `id` en la ruta): datos comunes y períodos. Edición (con `id`): una sola fecha, la del vuelo. */
export default function AdminVueloForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [aviones, setAviones] = useState<Avion[]>([])
  const [vuelo, setVuelo] = useState<VueloDetalle | null>(null)
  const [listo, setListo] = useState(false)
  const [errorCarga, setErrorCarga] = useState('')
  const [comunes, setComunes] = useState({ origen: '', destino: '', hora_partida: '', hora_llegada: '' })
  // En la edición hay un solo "período": `desde` es la fecha del vuelo; `hasta` y `dias` no se usan.
  const [periodos, setPeriodos] = useState<Periodo[]>([PERIODO_VACIO])
  const [errores, setErrores] = useState<ErroresApi>({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    let vigente = true
    Promise.all([getAeropuertos(), getAviones(), id ? getVuelo(id) : null]).then(
      ([listaAeropuertos, listaAviones, v]) => {
        if (!vigente) return
        setAeropuertos(listaAeropuertos)
        setAviones(listaAviones)
        if (v) {
          setVuelo(v)
          setComunes({
            origen: v.origen.codigo_iata,
            destino: v.destino.codigo_iata,
            hora_partida: hora(v.hora_partida),
            hora_llegada: hora(v.hora_llegada),
          })
          setPeriodos([
            { ...PERIODO_VACIO, desde: v.fecha_operacion, avion: v.avion.id, precio_economy: v.precio_economy, precio_primera: v.precio_primera },
          ])
        }
        setListo(true)
      },
      (e) => {
        if (vigente) setErrorCarga(e instanceof Error ? e.message : 'No pudimos cargar los datos.')
      },
    )
    return () => {
      vigente = false
    }
  }, [id])

  const soloLectura = vuelo !== null && (vuelo.estado === 'cancelado' || yaSalio(vuelo))
  const cargando = !errorCarga && !listo
  const total = periodos.reduce((n, p) => n + fechasDePeriodo(p.desde, p.hasta, p.dias).length, 0)
  const llegaDespues = comunes.hora_partida !== '' && comunes.hora_llegada !== '' && comunes.hora_llegada < comunes.hora_partida

  const cambiarComun = (campo: keyof typeof comunes, valor: string) => setComunes((c) => ({ ...c, [campo]: valor }))
  const cambiarPeriodo = (i: number, cambios: Partial<Periodo>) =>
    setPeriodos((lista) => lista.map((p, j) => (j === i ? { ...p, ...cambios } : p)))

  function errorDePeriodo(i: number, campo: keyof Periodo): string {
    if (id) return primero(errores[campo === 'desde' ? 'fecha_operacion' : campo])
    const lista = errores.periodos
    const item: unknown = Array.isArray(lista) ? lista[i] : null
    return item !== null && typeof item === 'object' ? primero((item as ErroresApi)[campo]) : ''
  }

  async function guardar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrores({})
    setErrorGeneral('')
    setEnviando(true)
    try {
      if (id) {
        const [p] = periodos
        await editarVuelo(id, { ...comunes, fecha_operacion: p.desde, avion: p.avion, precio_economy: p.precio_economy, precio_primera: p.precio_primera })
        navigate(`/admin/vuelos?q=${encodeURIComponent(id)}`)
      } else {
        const { numero_vuelo } = await crearVuelos({ ...comunes, periodos })
        navigate(`/admin/vuelos?q=${encodeURIComponent(numero_vuelo)}`)
      }
    } catch (e) {
      const detalle = erroresDe(e)
      setErrores(detalle)
      setErrorGeneral(
        primero(detalle.non_field_errors) ||
          (Object.keys(detalle).length ? 'Revisá los campos marcados.' : e instanceof Error ? e.message : 'No se pudo guardar.'),
      )
      setEnviando(false)
    }
  }

  if (errorCarga) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-8">
        <p role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{errorCarga}</p>
        <Link to="/admin/vuelos" className="mt-4 inline-block font-semibold text-marino underline">Volver al listado</Link>
      </main>
    )
  }
  if (cargando) return <main className="mx-auto max-w-3xl px-4 py-8" aria-busy="true">Cargando…</main>

  const opcionesAeropuerto = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <Link to="/admin/vuelos" className="text-sm font-semibold text-marino underline">Volver al listado</Link>
      <h1 className="mt-2 text-3xl font-extrabold text-marino">{vuelo ? `Vuelo ${vuelo.numero_vuelo}` : 'Nuevo vuelo'}</h1>
      {vuelo && <p className="mt-1 font-mono text-xs break-all text-slate-500">ID - {vuelo.id}</p>}
      {soloLectura && (
        <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-100 p-4 text-sm font-semibold text-slate-600">
          {vuelo?.estado === 'cancelado' ? 'Este vuelo está cancelado' : 'Este vuelo ya salió'}: no se puede modificar.
        </p>
      )}

      <form onSubmit={guardar} className="mt-6">
        <fieldset disabled={soloLectura || enviando} className="space-y-6">
          <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2">
            <Campo etiqueta="Aeropuerto de origen" error={primero(errores.origen)}>
              <select required value={comunes.origen} onChange={(e) => cambiarComun('origen', e.target.value)} className={CAMPO}>
                <option value="">Elegí un aeropuerto</option>
                {opcionesAeropuerto}
              </select>
            </Campo>
            <Campo etiqueta="Aeropuerto de destino" error={primero(errores.destino)}>
              <select required value={comunes.destino} onChange={(e) => cambiarComun('destino', e.target.value)} className={CAMPO}>
                <option value="">Elegí un aeropuerto</option>
                {opcionesAeropuerto}
              </select>
            </Campo>
            <Campo etiqueta="Hora de partida" error={primero(errores.hora_partida)}>
              <input type="time" required value={comunes.hora_partida} onChange={(e) => cambiarComun('hora_partida', e.target.value)} className={CAMPO} />
            </Campo>
            <Campo etiqueta="Hora de llegada" error={primero(errores.hora_llegada)}>
              <input type="time" required value={comunes.hora_llegada} onChange={(e) => cambiarComun('hora_llegada', e.target.value)} className={CAMPO} />
              {llegaDespues && <span className="mt-1 block text-xs font-semibold text-naranja">Llega al día siguiente</span>}
            </Campo>
          </section>

          {periodos.map((p, i) => (
            <section key={i} aria-label={id ? 'Fecha, avión y precios' : `Período ${i + 1}`} className="rounded-2xl border border-slate-200 bg-white p-5">
              {!id && (
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-extrabold text-marino">Período {i + 1}</h2>
                  {periodos.length > 1 && (
                    <button type="button" onClick={() => setPeriodos((lista) => lista.filter((_, j) => j !== i))} className="text-sm font-semibold text-red-700 underline">
                      Quitar
                    </button>
                  )}
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo etiqueta={id ? 'Fecha' : 'Desde'} error={errorDePeriodo(i, 'desde')}>
                  <input type="date" required value={p.desde} onChange={(e) => cambiarPeriodo(i, { desde: e.target.value })} className={CAMPO} />
                </Campo>
                {!id && (
                  <Campo etiqueta="Hasta" error={errorDePeriodo(i, 'hasta')}>
                    <input type="date" required min={p.desde} value={p.hasta} onChange={(e) => cambiarPeriodo(i, { hasta: e.target.value })} className={CAMPO} />
                  </Campo>
                )}
                {!id && (
                  <fieldset className="sm:col-span-2">
                    <legend className="text-sm font-semibold text-slate-700">Días de la semana</legend>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {DIAS.map((nombre, dia) => (
                        <label key={dia} className="flex cursor-pointer items-center gap-1.5 rounded-xl border border-slate-300 px-3 py-2 text-sm has-checked:border-marino has-checked:bg-marino/5">
                          <input
                            type="checkbox"
                            checked={p.dias.includes(dia)}
                            onChange={(e) => cambiarPeriodo(i, { dias: e.target.checked ? [...p.dias, dia].sort() : p.dias.filter((d) => d !== dia) })}
                          />
                          {nombre}
                        </label>
                      ))}
                    </div>
                    {errorDePeriodo(i, 'dias') && <span role="alert" className="mt-1 block text-xs font-medium text-red-700">{errorDePeriodo(i, 'dias')}</span>}
                  </fieldset>
                )}
                <div className={id ? '' : 'sm:col-span-2'}>
                  <Campo etiqueta="Avión" error={errorDePeriodo(i, 'avion')}>
                    <select required value={p.avion} onChange={(e) => cambiarPeriodo(i, { avion: e.target.value })} className={CAMPO}>
                      <option value="">Elegí un avión</option>
                      {aviones.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.matricula} - {a.modelo} ({a.capacidad_economy} economy, {a.capacidad_primera} primera)
                        </option>
                      ))}
                    </select>
                  </Campo>
                </div>
                <Campo etiqueta="Precio economy" error={errorDePeriodo(i, 'precio_economy')}>
                  <input type="number" required min="0.01" step="0.01" value={p.precio_economy} onChange={(e) => cambiarPeriodo(i, { precio_economy: e.target.value })} className={CAMPO} />
                </Campo>
                <Campo etiqueta="Precio primera" error={errorDePeriodo(i, 'precio_primera')}>
                  <input type="number" required min="0.01" step="0.01" value={p.precio_primera} onChange={(e) => cambiarPeriodo(i, { precio_primera: e.target.value })} className={CAMPO} />
                </Campo>
              </div>
              {!id && (
                <p className="mt-3 text-xs text-slate-500">
                  {fechasDePeriodo(p.desde, p.hasta, p.dias).length} vuelos en este período
                </p>
              )}
            </section>
          ))}

          {!id && (
            <button type="button" onClick={() => setPeriodos((lista) => [...lista, PERIODO_VACIO])} className="rounded-xl border border-marino bg-white px-4 py-2 text-sm font-bold text-marino hover:border-cielo hover:text-cielo">
              Agregar período
            </button>
          )}

          {errorGeneral && <p role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{errorGeneral}</p>}

          {!soloLectura && (
            <div className="flex flex-wrap items-center justify-end gap-4">
              {!id && (
                <p className="mr-auto text-sm font-semibold text-slate-600">
                  Se {total === 1 ? 'va a generar 1 vuelo' : `van a generar ${total} vuelos`}
                </p>
              )}
              <Link to="/admin/vuelos" className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-marino hover:border-cielo">
                Descartar
              </Link>
              <button type="submit" disabled={!id && total === 0} className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo disabled:cursor-not-allowed disabled:bg-slate-300">
                {enviando ? 'Guardando…' : id ? 'Guardar cambios' : 'Crear vuelos'}
              </button>
            </div>
          )}
        </fieldset>
      </form>
    </main>
  )
}
```

- [ ] **Step 2: Rutas**

En `frontend/src/App.tsx`, agregar `import AdminVueloForm from './pages/AdminVueloForm'` y, debajo de la ruta `admin/vuelos`:

```tsx
          <Route path="admin/vuelos/nuevo" element={<RutaProtegida roles={['administrador']}><AdminVueloForm /></RutaProtegida>} />
          <Route path="admin/vuelos/:id" element={<RutaProtegida roles={['administrador']}><AdminVueloForm /></RutaProtegida>} />
```

- [ ] **Step 3: Verificar**

Run: `cd frontend && npm run check && npm run build && npm run lint`
Expected: los tres pasan.

Verificación manual, con el backend y el front de la Task 8 corriendo:

1. "Nuevo vuelo": elegir ruta y horas, un período de dos semanas con dos días y un avión de LV-FAE en adelante (libres). El contador muestra los vuelos a generar. "Crear vuelos" lleva al listado filtrado por el número nuevo, con una fila por fecha y un ID distinto en cada una.
2. Repetir el alta idéntica: aparece el error de avión ocupado y no se crea nada.
3. Agregar un segundo período con otro avión y otros precios: se crean con el mismo número.
4. Poner la llegada antes que la partida: aparece "Llega al día siguiente" y en el listado la llegada muestra "+1".
5. Dejar un origen igual al destino: el error aparece debajo de "Aeropuerto de destino".
6. Lápiz en una fila: el formulario carga los datos de ese vuelo. Cambiar precio y hora, "Guardar cambios": el listado muestra el cambio en esa fila y las demás del mismo número quedan igual.
7. Lápiz en un vuelo cancelado: el formulario está en solo lectura con el aviso.
8. Entrar a `/admin/vuelos/nuevo` como pasajero: redirige a `/`.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): formulario de alta y edición de vuelos"
```

---

### Task 10: Documentación

**Files:**
- Modify: `docs/arquitectura.md`
- Modify: `docs/memoria.md`
- Modify: `CLAUDE.md` (solo si quedó desactualizado el comando de `seed`; hoy no lo menciona, no tocar)

- [ ] **Step 1: `docs/arquitectura.md`**

- En "Estructura de carpetas": la línea de `vuelos/` pasa a `aeropuertos, aviones, vuelos; búsqueda, detalle y ABM del administrador; comando seed`; en `pages/` y `components/` no hace falta listar cada archivo.
- En "Ideas clave del modelo", reemplazar el primer punto por:

```markdown
- **Sin tabla de recurrencia.** El admin define en el alta uno o más períodos (desde, hasta, días de la semana, avión y precios); el backend genera **una fila en `vuelos` por fecha**, todas con el mismo `numero_vuelo` (lo asigna el backend) y cada una con su `id`. Cada fila es independiente: modificar o cancelar una no afecta a las demás.
- **Llegada:** `fecha_llegada` la calcula el backend; es el día siguiente a `fecha_operacion` cuando `hora_llegada` es menor que `hora_partida`.
- **Avión libre:** un avión no puede tener dos vuelos activos con horarios superpuestos. Se valida en el alta y en la edición; no contempla rotación ni la ubicación del avión.
```

- En "API", reemplazar las líneas `CRUD /api/vuelos/` y `POST /api/vuelos/{id}/cancelar/` por:

```
GET  /api/vuelos/                (admin) ✅ listado paginado (50): q (id o número), origen, destino, desde, hasta, estado;
                                 sin desde ni q, desde hoy
POST /api/vuelos/                (admin) ✅ alta: origen, destino, horas y periodos[{desde, hasta, dias, avion, precios}]
                                 → 201 {numero_vuelo, cantidad}; genera una fila por fecha, todo o nada
PATCH /api/vuelos/{id}/          (admin) ✅ edita una instancia activa que no salió (fecha, horas, ruta, avión, precios)
POST /api/vuelos/{id}/cancelar/  (admin) ✅ estado = cancelado; la fila se conserva. Falta notificar por email (US16)
GET  /api/aviones/               (admin) ✅ catálogo para el formulario
```

- En "Errores 400", agregar: `Los errores de un período llegan en periodos[i].campo; los que no son de un campo, en non_field_errors.`
- Reemplazar el párrafo "Datos de ejemplo" por:

```markdown
**Catálogo y datos de ejemplo:** `python manage.py seed` carga los aeropuertos, la flota (10 aviones) y el usuario `sistema`; corre en `build.sh` porque no tienen ABM. `python manage.py seed --vuelos [--dias 60]` agrega vuelos de ejemplo sobre los primeros 4 aviones, para desarrollo local. Es idempotente y no pisa lo existente.
```

- En "Correr en local", cambiar el comentario de `python manage.py seed` a `# catálogo; con --vuelos, también vuelos de ejemplo`.

- [ ] **Step 2: `docs/memoria.md`**

Agregar arriba de "Estado actual":

```markdown
**2026-10-03 - ABM de vuelos, US01, US02 y US03 (rama `feat/abm-vuelos`)**
- `/admin/vuelos`: listado con filtros y paginación, alta con períodos de recurrencia, edición de una instancia (lápiz) y cancelación con confirmación (tacho). Spec y plan en `docs/superpowers/`.
- Backend: `GET/POST /api/vuelos/`, `PATCH /api/vuelos/{id}/`, `POST /api/vuelos/{id}/cancelar/`, `GET /api/aviones/`, todos solo para el rol administrador. Reglas en `vuelos/servicios.py`.
- `vuelos.fecha_llegada` nuevo (vuelos que cruzan medianoche). Las filas existentes quedaron con `fecha_llegada = fecha_operacion`.
- `seed` carga el catálogo y la flota de 10; los vuelos de ejemplo solo con `--vuelos` y ya no corren en `build.sh`.
- Límite actual: cancelar o cambiar el horario no avisa a los pasajeros (US15, US16); no hay reservas todavía.
```

Agregar a la tabla "Decisiones" (arriba):

```markdown
| 2026-10-03 | El backend asigna `numero_vuelo` (uno por alta, `FA ` + correlativo) y no se edita | El identificador de cada instancia es su `id`; evita choques con el índice único. Un alta nueva siempre recibe un número nuevo |
| 2026-10-03 | Un avión y un par de precios por período de recurrencia | Cubre "el o los aviones" y temporadas sin cambiar el esquema: cada fila sigue teniendo un solo avión |
| 2026-10-03 | `fecha_llegada` en `vuelos`, calculada por el backend | Soporta vuelos que cruzan medianoche sin ambigüedad en duración, vueltas posibles y avión libre |
| 2026-10-03 | Se valida que el avión esté libre (sin vuelos activos superpuestos) | Evita programar dos vuelos con el mismo avión; rotación y ubicación quedan fuera |
| 2026-10-03 | Cancelar cambia `estado`; no hay borrado | La US03 pide conservar el historial |
```

En "Próximos pasos", quitar el punto 2 (ABM de vuelos) y renumerar. En "Pendientes", agregar:

```markdown
- [ ] **Supabase tras mergear `feat/abm-vuelos`:** borrar los vuelos de ejemplo posteriores a hoy + 30 días (ocupan LV-FAA a LV-FAD) con el comando del plan, previa confirmación.
- [ ] **Extender un vuelo existente:** un alta nueva siempre recibe un número nuevo. Si hace falta sumar fechas a un número ya usado, agregar un campo opcional al alta.
```

- [ ] **Step 3: Verificar y commitear**

Run: `cd backend && DATABASE_URL= .venv/Scripts/python manage.py test && cd ../frontend && npm run check && npm run build && npm run lint`
Expected: todo pasa.

```bash
git add docs
git commit -m "docs: ABM de vuelos en arquitectura y memoria"
```

---

### Task 11: Supabase, después del merge (manual, con confirmación)

No se ejecuta durante la implementación. Requiere que `feat/abm-vuelos` esté mergeada a `main` y que Felipe confirme cada paso en el momento.

- [ ] **Step 1: Verificar el deploy.** Al mergear, Render corre `build.sh`: `migrate` aplica `0002` y `0003` sobre Supabase y `seed` agrega los 6 aviones nuevos. Comprobar en `https://fly-away-iz7s.onrender.com/api/vuelos/buscar/?origen=AEP&desde=<hoy>` que los vuelos traen `fecha_llegada`.

- [ ] **Step 2: Contar lo que se borraría.** Con `backend/.env` apuntando a Supabase:

```bash
cd backend && .venv/Scripts/python manage.py shell -c "
import datetime as dt
from django.utils import timezone
from vuelos.models import Vuelo
corte = timezone.localdate() + dt.timedelta(days=30)
q = Vuelo.objects.filter(creado_por__email='sistema@flyaway.local', fecha_operacion__gt=corte)
print('Se borrarían', q.count(), 'de', Vuelo.objects.count(), 'vuelos (posteriores a', corte, ')')
"
```

- [ ] **Step 3: Borrar, solo con el OK explícito de Felipe sobre el número del paso anterior.** El mismo comando, cambiando la última línea por `print(q.delete())`.

- [ ] **Step 4:** Tachar el pendiente en `docs/memoria.md` y commitear.
