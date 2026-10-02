# Backend de vuelos — diseño

Fecha: 2026-10-02 · Rama: `feat/backend-vuelos` (sale de `main`) · Alcance: **backend de búsqueda y detalle + conexión del front**.

Sigue a la [interfaz de inicio](2026-10-02-interfaz-inicio-design.md) y al [detalle de vuelo](2026-10-02-detalle-vuelo-design.md), que hoy funcionan con datos mock.

## Objetivo

Que la búsqueda, el detalle y la elección de vuelos usen datos reales de la base y no el generador mock de `frontend/src/lib/vuelos.ts`. El comportamiento que ve el pasajero es el mismo, con dos cambios pedidos:

- Se elimina el límite de 14 días del rango de fechas.
- En **ida y vuelta**, tanto la ida como la vuelta se pueden buscar en una fecha exacta o en un rango ("entre W y Z").

## Fuera de alcance

- **Login, registro y `/auth/yo/`:** son de otra US, a cargo de otro integrante. La sesión del front (`auth.ts`, `sesion.tsx`, `Login.tsx`) queda mockeada y no se toca. Esta rama deja listo el modelo `usuarios` para esa US.
- Reservas, pasajes, pagos y notificaciones, con sus modelos.
- ABM de vuelos para el admin. Hasta que exista, los vuelos se cargan con el comando `seed` o desde el admin de Django.
- Paginación de resultados (ver "Límites conocidos").

## Backend

### Apps

| App | Contenido |
|---|---|
| `usuarios` (reemplaza a `accounts`) | Modelo `Usuario`, tabla `usuarios` |
| `vuelos` (nueva) | `Aeropuerto`, `Avion`, `Vuelo`; serializers, vistas, comando `seed` |

Se borran `accounts` y su migración. `AUTH_USER_MODEL = 'usuarios.Usuario'`. La BD local (SQLite) se recrea y la de Supabase se resetea; ninguna de las dos tiene datos reales (ya estaba previsto en la memoria).

### Modelos

Los nombres de campos y tablas son los de `docs/modelo.dbml` y todos los `id` son UUID.

**`Usuario`** (`AbstractBaseUser`, sin `PermissionsMixin` para no agregar tablas fuera del DBML):
- Campos: `email` (login, único), `nombre`, `apellido`, `rol` (`administrador` | `empleado_mostrador` | `pasajero`), `activo`, `creado_en`, `actualizado_en`.
- La contraseña se guarda en la columna `password_hash` (`db_column`). Se quita `last_login` (`last_login = None`) porque no está en el DBML.
- `is_active` lee `activo`. `is_staff`, `has_perm` y `has_module_perms` son verdaderos solo para el `administrador`, que es el único que entra al admin de Django.
- `createsuperuser` crea un usuario con rol `administrador`.

**`Aeropuerto`:** `codigo_iata` (3 caracteres, único), `nombre`, `ciudad`, `pais`.

**`Avion`:** `matricula` (única), `modelo`, `capacidad_economy`, `capacidad_primera`.

**`Vuelo`:**
- Campos: `numero_vuelo`, `avion`, `aeropuerto_origen`, `aeropuerto_destino`, `fecha_operacion`, `hora_partida`, `hora_llegada`, `precio_economy`, `precio_primera` (decimal 10,2), `asientos_disponibles_economy`, `asientos_disponibles_primera`, `estado` (`activo` | `cancelado`), `creado_por` (FK a usuario), `creado_en`, `actualizado_en`.
- Constraints en la BD:
  - Único (`numero_vuelo`, `fecha_operacion`).
  - CHECK origen ≠ destino.
  - CHECK `asientos_disponibles_* >= 0`.

Los tres modelos de `vuelos` se registran en el admin de Django para poder cargar o corregir datos a mano.

### Endpoints

Todos son públicos (lectura). La permission por defecto, `IsAuthenticatedOrReadOnly`, ya lo permite.

| Método y ruta | Respuesta |
|---|---|
| `GET /api/aeropuertos/` | Lista de `{id, codigo_iata, nombre, ciudad, pais}` ordenada por ciudad |
| `GET /api/vuelos/buscar/` | Lista de vuelos (forma `Vuelo` del front) |
| `GET /api/vuelos/{id}/` | Un vuelo + `avion {matricula, modelo}` (forma `VueloDetalle`). Incluye cancelados. Si el id no existe o no es un UUID, devuelve 404 |

El vuelo se serializa con la misma forma que los tipos de `frontend/src/lib/vuelos.ts`. Los campos `origen` y `destino` llevan el aeropuerto anidado (salen de `aeropuerto_origen` y `aeropuerto_destino`) y los decimales se serializan como string.

### `GET /api/vuelos/buscar/`

Parámetros (query string):

| Parámetro | Obligatorio | Regla |
|---|---|---|
| `origen` | uno de los dos | Código IATA existente |
| `destino` | uno de los dos | Código IATA existente, ≠ origen, en otra ciudad |
| `desde` | sí | Fecha `YYYY-MM-DD`, no anterior a hoy |
| `hasta` | no | Fecha ≥ `desde`; sin límite de días. Vacío = solo `desde` |
| `pasajeros` | no (1) | Entero de 1 a 9 |
| `clase` | no (`economy`) | `economy` o `primera` |
| `precio_min`, `precio_max` | no | Número ≥ 0; `precio_min` ≤ `precio_max` |

Devuelve los vuelos que cumplen **todas** estas condiciones (es la misma regla que aplica hoy el mock):
1. `estado = activo`.
2. Ruta: el origen y/o el destino pedidos.
3. `fecha_operacion` entre `desde` y `hasta`.
4. `asientos_disponibles_<clase> >= pasajeros`.
5. `precio_<clase>` dentro de `[precio_min, precio_max]`.
6. Que no hayan salido: si la fecha es hoy, `hora_partida` tiene que ser posterior a la hora actual de `America/Argentina/Buenos_Aires` (el `TIME_ZONE` del proyecto).

Se ordenan por `fecha_operacion` y `hora_partida` (y `numero_vuelo` como desempate). La consulta usa `select_related` para traer los aeropuertos sin hacer N+1 queries.

La validación la hace un `Serializer` de DRF sobre `request.query_params`.

### Errores (400)

Usamos el formato estándar de DRF: un objeto con el **nombre del parámetro** como clave y una lista de mensajes como valor. Así el front puede mostrar cada error junto a su campo. Los mensajes están en español y son los mismos que ya muestra la validación del front:

```json
HTTP 400
{
  "desde": ["La fecha no puede ser en el pasado."],
  "pasajeros": ["Tienen que ser entre 1 y 9 pasajeros."]
}
```

| Caso | Clave | Mensaje |
|---|---|---|
| Sin origen ni destino | `origen` | Indicá un origen, un destino o ambos. |
| IATA desconocido | `origen` / `destino` | No conocemos el aeropuerto "XXX". |
| Destino = origen | `destino` | El destino tiene que ser distinto del origen. |
| Misma ciudad | `destino` | Origen y destino están en la misma ciudad. |
| Falta `desde` / fecha inválida | `desde` | Indicá una fecha válida (AAAA-MM-DD). |
| `desde` en el pasado | `desde` | La fecha no puede ser en el pasado. |
| `hasta` < `desde` | `hasta` | "Hasta" no puede ser antes de "Desde". |
| Pasajeros fuera de rango | `pasajeros` | Tienen que ser entre 1 y 9 pasajeros. |
| Clase inválida | `clase` | La clase tiene que ser economy o primera. |
| Precio negativo o no numérico | `precio_min` / `precio_max` | Ingresá un monto válido. |
| Mínimo > máximo | `precio_min` | El mínimo no puede ser mayor que el máximo. |

El 404 del detalle usa el formato por defecto de DRF: `{"detail": "No encontrado."}`.

### Comando `seed`

`python manage.py seed` carga **datos de ejemplo** en una BD vacía, porque todavía no existe otra forma de crear vuelos:
- Los 11 aeropuertos y los 4 aviones que hoy usa el mock.
- Un usuario `sistema@flyaway.local`, rol `administrador`, con contraseña inutilizable (no puede iniciar sesión). Es el `creado_por` de los vuelos generados.
- Vuelos para los próximos 60 días (`--dias N` para cambiarlo), con la misma lógica del mock:
  - De 0 a 4 vuelos por ruta y día, con duración fija por ruta.
  - Números de vuelo por bloque de ruta.
  - Precios y asientos al azar, con un `random.Random` sembrado por ruta y fecha, para que el resultado sea repetible.
  - Alrededor de un 10 % cancelados.
  - Sin rutas entre aeropuertos de la misma ciudad.

Es **idempotente**: usa `get_or_create`/`update_or_create` por clave natural (`codigo_iata`, `matricula`, `numero_vuelo` + `fecha_operacion`) y los vuelos que ya existen no se pisan. Por eso se puede correr en cada deploy. Se agrega a `backend/build.sh` después de `migrate`, así Render (plan free, sin shell) queda con datos y cada deploy extiende la ventana de 60 días. **Hay que sacarlo de `build.sh` cuando exista el ABM de vuelos.**

## Frontend

### `src/lib/vuelos.ts`
- `getAeropuertos` → `api('/aeropuertos/')`.
- `buscarVuelos(p)` → `api('/vuelos/buscar/?…')`, con `precioMin`/`precioMax` pasados como `precio_min`/`precio_max` y omitiendo los parámetros vacíos. Deja de recibir `ahora` porque "ya salió" lo resuelve el back.
- `getVuelo(id)` → `api(`/vuelos/${id}/`)`.
- Se borra todo el mock: `AEROPUERTOS`, `FLOTA`, `generarVuelos`, `semilla`, `azar`, `fechasDelRango` y `esperar`.
- `vueltasPosibles(vueltas, ida)`: ahora la vuelta puede caer en un rango que se superpone con la ida, así que la regla pasa a ser "parte después de que la ida aterriza": `fecha + hora_partida` de la vuelta > `fecha + hora_llegada` de la ida.

`src/lib/api.ts` no cambia. Los 400 no deberían llegar al pasajero porque el front valida lo mismo antes de pedir. Si llegan, se ve el error genérico de carga que ya existe.

### Búsqueda sin límite y con rango en ida y vuelta
- `busqueda.ts`:
  - Se borra `MAX_DIAS_RANGO` y su validación.
  - `Filtros` suma `vueltaHasta: string` ('' = solo el día `vuelta`), que va a la URL como `vueltaHasta`.
  - En ida y vuelta, `hasta` ya no se fuerza a ''.
  - Validaciones nuevas: `vueltaHasta` ≥ `vuelta`, y `vuelta` ≥ `ida`, como hasta ahora.
- `BuscadorVuelos.tsx`: en ida y vuelta se muestran cuatro fechas: Ida, Hasta (opcional), Vuelta, Hasta (opcional). En solo ida no cambia nada.
- `Vuelos.tsx`: la búsqueda de la vuelta pasa `hasta: f.vueltaHasta`. Los subtítulos muestran el rango cuando lo hay (`rangoFechas`).

## Pruebas

**Backend** (`manage.py test`, con `TestCase` de Django, sin librerías nuevas):
- Búsqueda:
  - Filtra cancelados, falta de asientos, rango de precio y vuelos que ya salieron (la hora se fija con `unittest.mock.patch` sobre `timezone.now`).
  - Respeta el rango de fechas y la ruta (solo origen, solo destino, ambos).
  - Devuelve los vuelos ordenados.
- Cada caso de la tabla de errores devuelve 400 con su clave y mensaje.
- Detalle: trae el avión, devuelve los cancelados y responde 404 a un UUID inexistente.
- `seed`: dos ejecuciones seguidas dejan la misma cantidad de filas.
- Constraint de BD: un vuelo con origen = destino da `IntegrityError`.

**Frontend** (`npm run check`):
- Se borran los chequeos del generador mock (`generarVuelos`, `buscarVuelos`, `getVuelo` y `getAeropuertos` del mock).
- Se actualizan los de `validarBusqueda` (sin límite de 14 días, `vueltaHasta`), `leerFiltros`/`aParams` (round trip con `vueltaHasta`) y `vueltasPosibles` (vuelta en un rango superpuesto).

**A mano:** con `runserver` + `npm run dev` y la BD cargada por `seed`, probar buscar en solo ida y en ida y vuelta con rangos, abrir el detalle y elegir un vuelo.

## Documentación
- `docs/arquitectura.md`: se marcan como hechos los endpoints de aeropuertos, buscar y detalle; se saca "rango ≤ 14 días"; se agrega el comando `seed` y el formato de errores.
- `docs/memoria.md`: estado, decisiones (sin límite de rango, formato de 400, `seed` en `build.sh`) y un aviso para la US de login: el modelo `usuarios` ya existe y faltan `/auth/registro/` y `/auth/yo/`.

## Límites conocidos
- **Sin paginación:** una búsqueda "solo origen" con un rango de un año puede devolver miles de vuelos. Con los datos del seed (60 días) no pasa. Se agrega `PageNumberPagination` si se vuelve un problema.
- **Deploy:** después de mergear, Supabase necesita el reset (drop de las tablas de `accounts`) antes del primer `migrate`.
