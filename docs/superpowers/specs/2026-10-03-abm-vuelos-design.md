# ABM de vuelos (administrador) - diseño

Fecha: 2026-10-03. Rama: `feat/abm-vuelos`. Cubre US01 (crear), US02 (modificar) y US03 (cancelar).

## Objetivo

El administrador gestiona los vuelos desde `/admin/vuelos`: crea vuelos con recurrencia (una instancia independiente por fecha), edita una instancia y cancela una instancia, sin afectar a las demás.

## Fuera de alcance

- Emails a pasajeros por cambio de horario o cancelación (US15, US16).
- ABM de aeropuertos y aviones (se cargan con `seed` o desde Django Admin).
- Editar o cancelar una serie completa: no existe la serie, cada vuelo es una fila suelta.
- Planificación de flota: tiempo de rotación entre vuelos y que el avión esté en el aeropuerto de origen.

## Decisiones

| Tema | Decisión |
|---|---|
| Recurrencia | No se persiste. Los períodos viajan en el pedido de alta y el backend genera una fila de `vuelos` por fecha. |
| Identificador | El `id` UUID de cada fila. Dos fechas nunca comparten `id`. |
| Número de vuelo | Lo genera el backend, uno por alta, compartido por todas sus instancias. No es editable. |
| Aviones | Uno por período. Cada instancia tiene un solo avión. |
| Qué define cada período | Desde, hasta, días de la semana, avión, precio economy y precio primera. |
| Qué es común al alta | Origen, destino, hora de partida y hora de llegada. |
| Vuelos que cruzan medianoche | Soportados con el campo nuevo `fecha_llegada`. |
| Avión libre | Se valida en el alta y en la edición. |
| Cancelar | Cambia `estado` a `cancelado`. No hay borrado físico. |

## Cambio de esquema: `fecha_llegada`

`vuelos` suma `fecha_llegada date [not null]`, a continuación de `fecha_operacion`.

- El admin no la escribe. El backend la calcula: si `hora_llegada` es menor que `hora_partida`, el vuelo llega al día siguiente (`fecha_operacion + 1`); si es mayor, llega el mismo día. Horas iguales se rechazan: un vuelo dura menos de 24 horas.
- Constraint nuevo en la base: la llegada es posterior a la partida, es decir `fecha_llegada > fecha_operacion`, o `fecha_llegada = fecha_operacion` y `hora_llegada > hora_partida`.
- Migración en dos archivos: el primero agrega la columna aceptando nulos y completa las filas existentes con `fecha_llegada = fecha_operacion` (todos los vuelos actuales llegan el mismo día); el segundo la pasa a obligatoria y agrega el constraint. Van separados para no mezclar datos y cambios de esquema en una misma transacción de Postgres.

Lo que hay que tocar para no romper nada:

| Lugar | Cambio |
|---|---|
| `docs/modelo.dbml` | Columna y constraint nuevos. |
| `vuelos/models.py` | Campo y `CheckConstraint`. |
| `vuelos/serializers.py` | `fecha_llegada` en `VueloSerializer` (cambio aditivo para la búsqueda y el detalle). |
| `vuelos/management/commands/seed.py` | Completar `fecha_llegada`. |
| `vuelos/tests.py` | El ayudante que crea vuelos y la lista de campos esperados. |
| `frontend/src/lib/vuelos.ts` | Tipo `Vuelo`; `duracionDe` suma 24 h si llega al día siguiente; `vueltasPosibles` compara con `fecha_llegada + hora_llegada`. |
| `CardVuelo`, `DetalleVuelo`, `Vuelos.tsx` | Marca "+1" junto a la hora de llegada cuando llega al día siguiente. |
| `frontend/scripts/check.ts` | Casos de duración y vueltas con cruce de medianoche. |

**Supabase:** `build.sh` ya corre `migrate` en cada deploy, así que la base compartida se migra sola al mergear a `main`. No se aplica antes a mano: el backend de `main` corre `seed` en cada deploy y, con la columna obligatoria ya creada, sus altas fallarían.

## Reglas de negocio (backend)

### Alta (US01)

Entrada:

```json
{
  "origen": "AEP",
  "destino": "BRC",
  "hora_partida": "08:30",
  "hora_llegada": "10:45",
  "periodos": [
    {
      "desde": "2026-11-01",
      "hasta": "2026-12-15",
      "dias": [0, 2, 4],
      "avion": "<id del avión>",
      "precio_economy": "85000.00",
      "precio_primera": "190000.00"
    }
  ]
}
```

`dias` usa 0 = lunes a 6 = domingo (igual que `date.weekday()` de Python).

Validaciones:

- Todos los campos son obligatorios; al menos un período y al menos un día por período.
- Origen distinto de destino y en distinta ciudad (la misma regla que la búsqueda).
- `hora_llegada` distinta de `hora_partida`.
- `desde` no anterior a hoy; `hasta` no anterior a `desde`; `hasta` a lo sumo un año desde hoy.
- Cada período genera al menos una fecha.
- Precios mayores a cero.
- Ninguna fecha repetida entre los períodos del alta.
- Avión libre en cada fecha generada (ver abajo).

Generación, dentro de `transaction.atomic()` (se crean todas las instancias o ninguna):

- Una fila por cada fecha del rango que caiga en un día elegido.
- `numero_vuelo`: `FA ` más el correlativo siguiente al más alto existente. El índice único (`numero_vuelo`, `fecha_operacion`) es la red de seguridad ante dos altas simultáneas: la segunda falla con un error que pide reintentar.
- `asientos_disponibles_*` igual a la capacidad del avión del período.
- `creado_por` igual al administrador autenticado; `estado` igual a `activo`.

### Avión libre

Un avión está ocupado si tiene otro vuelo `activo` cuyo intervalo (fecha y hora de partida a fecha y hora de llegada) se superpone con el del vuelo nuevo. Los cancelados no ocupan. En la edición se excluye al propio vuelo. Ante un choque se rechaza el pedido completo indicando avión, fecha y vuelo en conflicto, por ejemplo: "LV-FAA ya está asignado al FA 1203 el 2026-11-04 de 10:00 a 12:15".

### Edición (US02)

- Solo vuelos `activos` que todavía no salieron (fecha y hora de partida posteriores a ahora, hora de Buenos Aires).
- Editables: `fecha_operacion`, horarios, origen, destino, avión y precios, con las validaciones del alta que apliquen. `fecha_llegada` se recalcula.
- No editables: `numero_vuelo`, `estado`, `asientos_disponibles_*`, `creado_por`.
- Al cambiar de avión: asientos disponibles nuevos = capacidad nueva menos vendidos (vendidos = capacidad anterior menos disponibles). Si da negativo en alguna clase, se rechaza.
- Si la fecha nueva choca con otra instancia del mismo número, error en `fecha_operacion`.
- Afecta solo a la fila elegida.

### Cancelación (US03)

- Solo vuelos existentes (si no, 404), `activos` y que no salieron (si no, 400).
- Cambia `estado` a `cancelado`. La fila y sus datos se conservan.
- La búsqueda ya excluye cancelados; el detalle los sigue mostrando como cancelados.

## API

Todo lo nuevo exige rol `administrador`: 401 sin sesión, 403 con otro rol. Errores 400 con el formato de DRF y mensajes en español; los de un período llegan en `periodos[i].campo` y los que no son de un campo (avión ocupado, fechas repetidas, vuelo cancelado o que ya salió) en `non_field_errors`.

| Endpoint | Descripción |
|---|---|
| `GET /api/vuelos/` | Listado paginado (50 por página, `{count, next, previous, results}`), ordenado por fecha y hora. Filtros: `q` (id exacto o parte del número), `origen`, `destino`, `desde`, `hasta`, `estado`. Sin `desde` ni `q`, lista desde hoy (con `q` busca en todas las fechas, para poder llegar a un vuelo por su ID). Cada vuelo incluye el avión. |
| `POST /api/vuelos/` | Alta con períodos. Responde 201 con `{numero_vuelo, cantidad}`. |
| `GET /api/vuelos/{id}/` | Ya existe y sigue público. El avión anidado suma `id`, `capacidad_economy` y `capacidad_primera`. |
| `PATCH /api/vuelos/{id}/` | Edita una instancia. Responde el vuelo actualizado. |
| `POST /api/vuelos/{id}/cancelar/` | Cancela una instancia. Responde el vuelo actualizado. |
| `GET /api/aviones/` | Catálogo para el selector del formulario. |

## Pantalla

Rutas, todas detrás de la guarda de rol `administrador`:

- **`/admin/vuelos` - listado.** Tabla con ID, número, fecha, ruta, partida, llegada, avión, precios y estado. Arriba, los filtros (incluido el campo para buscar por ID o número) y el botón "Nuevo vuelo". Cada fila tiene un botón con lápiz (editar) y uno con tacho (cancelar). En los vuelos cancelados o que ya salieron el tacho queda deshabilitado y el lápiz abre el formulario en solo lectura. Paginación centrada al pie, con flechas y números.
- **`/admin/vuelos/nuevo` - formulario de alta.** Datos comunes y la lista de períodos, que se agregan y quitan. Días de la semana como casillas; fechas y horas con los inputs nativos. Si la llegada es anterior a la partida, muestra "llega al día siguiente". Antes de guardar muestra cuántos vuelos se van a generar. Al guardar vuelve al listado filtrado por el número asignado.
- **`/admin/vuelos/:id` - formulario de edición.** El mismo formulario, cargado con los datos del vuelo: una sola fecha en lugar de períodos, y el número y el ID en solo lectura. Al guardar vuelve al listado.
- **Cancelar.** El tacho abre un `<dialog>` nativo: "¿Cancelar el vuelo {id}?", con número, fecha y ruta debajo, y los botones "Cancelar vuelo" y "Volver". Al confirmar, la fila queda marcada como cancelada.

Los botones de lápiz y tacho llevan `aria-label` ("Editar vuelo {id}", "Cancelar vuelo {id}"). Las llamadas a la API van por `src/lib/api.ts`. Los errores del backend se muestran junto al campo que corresponde.

## Datos de ejemplo (`seed`)

`seed` hoy carga tres cosas: aeropuertos, aviones y vuelos inventados para los próximos 60 días, y corre en cada deploy.

- Los vuelos de ejemplo salen de `build.sh`: con el ABM los carga el administrador. Además no pasan por la validación de avión libre (hay miles de vuelos sobre 4 aviones), así que casi cualquier alta nueva chocaría con ellos.
- Aeropuertos, aviones y el usuario `sistema` se siguen cargando en cada deploy: no tienen ABM y sin ellos el formulario no tiene qué ofrecer.
- Implementación: `seed` carga solo el catálogo; `seed --vuelos` agrega los vuelos de ejemplo, para desarrollo local.
- La flota pasa de 4 a 10 aviones. Los vuelos de ejemplo usan solo los 4 primeros (LV-FAA a LV-FAD); los 6 nuevos quedan libres para las altas del administrador.

**Supabase, después del merge:** se borran los vuelos de ejemplo (creados por `sistema@flyaway.local`) con fecha posterior a hoy + 30 días, para que la programación futura quede en manos del administrador y la búsqueda siga teniendo datos para la demo. Es un paso manual y destructivo sobre la base compartida: se ejecuta solo con confirmación explícita en el momento.

## Pruebas

Backend (`vuelos/tests.py`):

- Permisos: sin sesión, pasajero y empleado no pueden listar, crear, editar ni cancelar.
- Alta: fechas generadas según días y rango; varios períodos; un `id` distinto por instancia; número compartido; asientos según el avión; cada validación; cruce de medianoche (`fecha_llegada`); alta atómica ante un error.
- Avión libre: choque en el alta, en la edición, cruzando medianoche, y que un cancelado no ocupa.
- Edición: cambia solo la instancia elegida; recalcula asientos al cambiar de avión; rechaza vuelos cancelados o que ya salieron.
- Cancelación: cambia solo la instancia elegida; el vuelo deja de aparecer en la búsqueda; la fila se conserva; rechaza uno ya cancelado.
- Migración: las filas existentes quedan con `fecha_llegada = fecha_operacion`.

Frontend: `npm run check` cubre el conteo de fechas de un período, la duración y las vueltas con cruce de medianoche. Además `npm run build` y `npm run lint`.

## Documentación

Actualizar `docs/modelo.dbml`, `docs/arquitectura.md` (modelo, API, `seed`) y `docs/memoria.md` (estado, decisiones, pendientes).
