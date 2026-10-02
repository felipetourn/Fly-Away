# US05 — Consultar información de un vuelo — diseño

Fecha: 2026-10-02 · Rama: `feat/detalle-vuelo` (sale de `feat/interfaz-inicio`) · Alcance: **solo frontend, datos mockeados**.

Parte de la [interfaz de inicio](2026-10-02-interfaz-inicio-design.md): reutiliza su buscador, sus resultados y su mock.

## Objetivo

Desde los resultados de búsqueda, el pasajero puede ver toda la información de un vuelo en un diálogo, sin salir del flujo de búsqueda (ni perder la ida elegida en un viaje de ida y vuelta), y elegirlo desde ahí.

La única forma de llegar a un vuelo es buscándolo, así que el detalle **no es una ruta nueva**: es un diálogo sobre los resultados.

Referencia visual aprobada: mockup estático del diálogo.

## Criterios de aceptación (US05)

| Criterio | Dónde se muestra |
|---|---|
| Origen | Columna izquierda del trayecto: IATA, ciudad y nombre del aeropuerto |
| Destino | Columna derecha del trayecto: IATA, ciudad y nombre del aeropuerto |
| Horario de partida | Hora grande sobre el origen |
| Horario de llegada | Hora grande sobre el destino |
| Fecha | Arriba del trayecto, completa: "Martes, 20 de octubre de 2026" |
| Clases disponibles | Tabla con una fila por clase (Economy y Primera) |
| Precio por clase | Columna "Precio por persona" de la tabla |
| Disponibilidad | Columnas "Asientos" (cantidad libre) y "Estado" (Disponible / Últimos asientos / Agotada) |

Extra (no lo piden los criterios): duración, número de vuelo, "Directo" y **modelo del avión** (`aviones.modelo`).

Tareas de la US y dónde quedan: definir la información (esta sección), crear la interfaz (card + diálogo), pruebas y correcciones (chequeos + revisión en el navegador), documentar (arquitectura y memoria).

## Fuera de alcance

- Mapa de asientos o elección de asiento.
- Escalas (todos los vuelos son directos).
- Ruta o URL propia para el detalle: recargar la página lo cierra.
- Backend (se hace después).

## Comportamiento

### Card de vuelo (`components/CardVuelo.tsx`, cambia)
- Al pie, al lado del precio, dos botones:
  - **Ver detalle**: secundario (borde marino, fondo blanco). Abre el diálogo.
  - **Elegir**: principal (relleno marino), igual que hoy.
- El aviso de asientos usa el mismo umbral que el estado de clase (5 o menos: "¡Quedan N asientos!" en naranja).

### Diálogo de detalle (`components/DetalleVuelo.tsx`, nuevo)
- `<dialog>` nativo abierto con `showModal()`: fondo oscurecido (velo marino con blur), foco dentro del diálogo, **Esc** lo cierra. También cierran la ✕ y "Cerrar".
- Ancho `min(44rem, 100% − 2rem)`, alto máximo 90vh con scroll interno, esquinas `rounded-3xl`.
- **Cabecera:** `public/logoA.svg` (40px de alto), número de vuelo (`FA 1010`, extrabold marino), badge "Directo", botón ✕ (`aria-label="Cerrar"`).
- **Cuerpo:**
  - Fecha completa (`fechaCompleta`).
  - Trayecto en 3 columnas (desde `sm`; apiladas debajo): origen (etiqueta "Origen", hora, `IATA · Ciudad`, nombre del aeropuerto) · duración + línea con ✈ + "Directo" · destino (igual, alineado a la derecha).
  - "Avión: Airbus A320", en texto chico debajo del aeropuerto de origen. Origen y destino alinean arriba; la duración queda centrada.
  - **Tabla de clases** (`<caption>` accesible "Clases, precios y disponibilidad"): Clase · Precio por persona · Asientos · Estado.
    - Estado con badge: **Disponible** (verde), **Últimos asientos** (naranja, 1 a 5), **Agotada** (gris, 0).
    - La fila de la clase buscada va resaltada y marcada "(tu búsqueda)".
- **Pie:** "Cerrar" y **"Elegir este vuelo"** (hace lo mismo que "Elegir" en la card y cierra el diálogo).
  - Deshabilitado, con el motivo debajo, si en la clase buscada no hay lugar para todos los pasajeros ("No hay lugar para 3 pasajeros en Primera") o si el vuelo fue cancelado ("Este vuelo fue cancelado").
- **Datos frescos:** al abrir, el diálogo muestra enseguida lo que ya trae la card y pide `getVuelo(id)`:
  - Cargando: trayecto y fecha con los datos de la card; skeleton en la tabla y en el avión.
  - OK: reemplaza todo con la respuesta (los asientos pueden haber cambiado desde la búsqueda).
  - Error: "No pudimos cargar el detalle. Probá de nuevo." + Reintentar (`role="alert"`); "Elegir este vuelo" queda deshabilitado.
- Lo abre y cierra `ListaVuelos` (estado local): la página `Vuelos` no cambia, salvo pasarle `pasajeros`. Elegir un vuelo navega (cambia la URL), la lista se remonta y el diálogo desaparece.

## Datos y contrato con el backend (`lib/vuelos.ts`)

```ts
interface Avion { matricula: string; modelo: string }
interface VueloDetalle extends Vuelo { avion: Avion }
type EstadoClase = 'disponible' | 'ultimos' | 'agotada'
```

| Función | Mock | Reemplazo futuro |
|---|---|---|
| `getVuelo(id): Promise<VueloDetalle>` | regenera el vuelo a partir del id; id desconocido → rechaza con `Error('Vuelo no encontrado')` | `api('/vuelos/<id>/')` (404 → error) |
| `estadoClase(asientos): EstadoClase` | 0 → `agotada`; 1–5 → `ultimos`; más → `disponible` | se queda en el front (es presentación) |

Contrato de `GET /vuelos/<id>/`: el mismo `Vuelo` que devuelve la búsqueda (origen y destino anidados) más `avion: { matricula, modelo }`. Incluye vuelos cancelados (con `estado: 'cancelado'`): el detalle informa la cancelación en vez de dar 404.

### Ajuste del mock: números de vuelo únicos
Hoy el número de vuelo sale de un cálculo con 90 valores para 110 rutas, así que **dos rutas pueden repetir número el mismo día**, lo que viola el índice único (`numero_vuelo`, `fecha_operacion`) del modelo y puede hacer que el explorador muestre dos vuelos con el mismo id. Se corrige así:

- Cada ruta (par ordenado de aeropuertos, según su posición en la lista) tiene un bloque propio de 10 números: `FA {1000 + índiceRuta × 10 + n}` (n = 0 a 3).
- El id no cambia de forma (`FA1010-2026-10-20`): `getVuelo` recupera la ruta desde el número y la fecha desde el id, y regenera el vuelo.
- Avión: se elige de forma determinística por ruta de una flota mock de 4 modelos (Airbus A320, Boeing 737-800, Embraer E190, Airbus A330-200), cada uno con su matrícula `LV-…`.

Esto afecta solo al mock: con backend, el id es el UUID de la fila.

### Formato (`lib/formato.ts`)
- `fechaCompleta(iso)`: "Martes, 20 de octubre de 2026".

## Accesibilidad y responsive

- `<dialog>` con `aria-labelledby` apuntando al título ("Vuelo FA 1010"); tabla con `<caption>` (visualmente oculto) y `<th scope>`.
- Estados de carga `role="status"`, error `role="alert"`, motivo del botón deshabilitado enlazado con `aria-describedby`.
- 360px: el diálogo ocupa el ancho menos 1rem por lado, el trayecto se apila y la tabla entra sin scroll horizontal.

## Verificación

- `npm run check` (`scripts/check.ts`):
  - números de vuelo únicos por fecha en todas las rutas (en varias fechas);
  - `getVuelo(id)` devuelve el mismo vuelo que la búsqueda, con `avion`;
  - `getVuelo` de un id con formato inválido, de un número fuera de rango o de un número que no existe ese día → rechaza;
  - `getVuelo` de un vuelo cancelado lo devuelve con `estado: 'cancelado'`;
  - `estadoClase` en 0, 1, 5, 6;
  - `fechaCompleta` con TZ UTC−3 muestra el día correcto.
- `npm run build` y `npm run lint` sin errores.
- Navegador: abrir el detalle desde ida y desde vuelta, cerrar con Esc / ✕ / Cerrar, elegir desde el diálogo (sigue el flujo de pasos), clase agotada o sin lugar para todos (botón deshabilitado con motivo), error de `getVuelo` (forzado y revertido), vista de 360px.

## Documentación

- `docs/arquitectura.md`: `GET /api/vuelos/{id}/` con `avion` anidado.
- `docs/memoria.md`: estado (US05), decisión "detalle en diálogo, no ruta", y el arreglo de números de vuelo del mock.
