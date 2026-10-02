# Interfaz de inicio (Vuelos) — diseño

Fecha: 2026-10-02 · Rama: `feat/interfaz-inicio` · Alcance: **solo frontend, datos mockeados**.

## Objetivo

Primera pantalla real del pasajero: header de la marca, hero con fotos de destinos y buscador de vuelos con resultados en cards. Todo funciona con datos mock que tienen **la misma forma que devolverá el backend** (ver `docs/modelo.dbml`), de modo que conectar la API sea reemplazar el cuerpo de unas pocas funciones sin tocar la UI.

Referencia visual aprobada: mockup estático (Despegar / TurismoCity como inspiración).

## Criterios de aceptación (user story de búsqueda)

| Criterio | Cómo se cumple |
|---|---|
| El pasajero puede ingresar un aeropuerto de origen, destino o ambos | En **Solo ida**, origen y destino son opcionales ("Cualquiera"), con al menos uno obligatorio. En **Ida y vuelta** se piden los dos. |
| El pasajero puede seleccionar una fecha o rango de las mismas | En **Solo ida**: "Desde" (obligatoria) y "Hasta" (opcional, rango de hasta 14 días). En **Ida y vuelta**: fecha de ida y de vuelta. |
| El pasajero puede seleccionar un rango de precio | Fila de filtro sobre los resultados: precio por persona mínimo y/o máximo, en la clase elegida. |
| Se muestran los vuelos correspondientes a los criterios ingresados | `buscarVuelos` filtra por ruta, fechas, lugar para todos los pasajeros y precio. |
| No se muestran vuelos cancelados como alternativas disponibles | `buscarVuelos` descarta `estado = 'cancelado'` (y los vuelos de hoy que ya salieron). |
| Cuando no existen resultados, se informa claramente al usuario | "No encontramos vuelos con esos criterios." + una sugerencia según la búsqueda. |

## Fuera de alcance

- Backend (modelos, endpoints, seed). Se hace después.
- Compra, pago, reservas reales, login/registro reales, perfil real.
- Autocompletado de aeropuertos, filtro por horario, multidestino, rango de fechas en ida y vuelta.

## Identidad visual

- Paleta del logo como tokens de Tailwind v4 (`@theme` en `src/index.css`):
  `marino #064D7D` · `cielo #068EC1` · `naranja #FF6F13` · `ambar #FF9F1B`. Fondo general `slate-50`.
- Tipografía: **Montserrat**, archivos locales en `src/fonts/` (`woff2`, subset latin, pesos 400–800) declarados con `@font-face` en `src/index.css` (`font-display: swap`). Sin dependencias externas.
- Logo del header: `public/titulo.svg`. Ícono de la pestaña y logo del header en mobile: `public/logoMain.svg` (el avión). Logo del detalle de vuelo: `public/logoA.svg`.
- Botón principal (Buscar): naranja. Acciones secundarias (Elegir, Registrarse, Aplicar): marino → cielo en hover.

## Rutas

| Ruta | Pantalla |
|---|---|
| `/` | **Vuelos** (default): hero + buscador + resultados. Filtros en la query string. |
| `/reservas` | Próximamente |
| `/perfil` | Próximamente + botón "Cerrar sesión" (borra la sesión mock) |
| `/login` | Próximamente + botón "Entrar (demo)" (crea la sesión mock y vuelve a `/`) |
| `/registro` | Próximamente |
| `/mostrador/*`, `/admin/*` | Sin cambios |

Todas las rutas del pasajero comparten el `Header`.

Query string de `/` (hay búsqueda si está `ida`):

| Parámetro | Valor |
|---|---|
| `origen`, `destino` | IATA; ausente = cualquiera (solo en solo ida) |
| `ida` | YYYY-MM-DD; en solo ida es el "desde" |
| `hasta` | YYYY-MM-DD, opcional, solo en solo ida |
| `vuelta` | YYYY-MM-DD; presente = ida y vuelta, ausente = solo ida |
| `pasajeros` | 1–9 |
| `clase` | `economy` \| `primera` |
| `precioMin`, `precioMax` | montos por persona, opcionales |
| `idaId` | id del vuelo de ida elegido, opcional |

Así el botón "atrás" del navegador y recargar la página funcionan. Las fechas que no existen en el calendario (`2027-02-30`) se descartan al leer la URL.

## Componentes

### Header (`components/Header.tsx`)
- Sticky, fondo blanco translúcido con blur, borde inferior sutil. Alto 80px, ancho completo (padding lateral 16px; 32px desde `md`): el logo pegado a la izquierda y la navegación a la derecha.
- Izquierda: título FLY AWAY (link a `/`), alto 32px en mobile y 40px desde `md`. El `viewBox` de `titulo.svg` está recortado a las letras (sin márgenes internos).
- Derecha, en orden: **Vuelos** (`/`), **Reservas** (`/reservas`), separador vertical, y:
  - sin sesión: `Iniciar sesión` (link) `|` `Registrarse` (botón marino);
  - con sesión: círculo de 40px con las **iniciales** (nombre + apellido) sobre gradiente naranja→ámbar, link a `/perfil`, `title="Mi perfil"`.
- El ítem activo lleva subrayado naranja (NavLink).
- Debajo de `sm` (640px): ícono del avión en lugar del título y, sin sesión, un solo link "Ingresar" (el login tiene el link a registro). Sin menú hamburguesa.

### HeroCarrusel (`components/HeroCarrusel.tsx`)
- Sección de `62vh` (mínimo 420px), fondo marino.
- Fotos de `public/destinos/` apiladas con `object-cover` (se ve el recorte central; no tiene que entrar la foto entera). Fundido de 1,6 s y zoom lento (de 1,06 a 1) cada **6 s**, en loop. Sin flechas ni puntos: es **decorativo** (`aria-hidden`, `alt=""`).
- Velo con gradiente marino (60% → 25% → 70%) para que se lea lo de adelante.
- Texto: kicker "VOLÁ POR TODA LA ARGENTINA" (ámbar) y título **"¿A dónde querés ir?"** (blanco, extrabold, una sola línea desde `md`). El texto usa el mismo contenedor que el buscador (`max-w-[88rem]`), así su borde izquierdo queda alineado con la card de filtros.
- Texto chico abajo a la derecha con el lugar de la foto actual (vacío si la foto no tiene).
- `prefers-reduced-motion`: queda fija la primera foto, sin animación.
- Orden y textos:

  | Archivo | Texto |
  |---|---|
  | `perito-moreno.jpg` | Glaciar Perito Moreno, El Calafate |
  | `ushuaia.jpg` | Faro Les Éclaireurs, Ushuaia |
  | `hornocal.jpg` | Serranía de Hornocal, Humahuaca, Jujuy |
  | `obelisco.jpg` | Obelisco, Buenos Aires |
  | `bariloche-1.jpg` | San Carlos de Bariloche, Río Negro |
  | `cafayate.jpg` | Cafayate, Salta |
  | `caminito.jpg` | Caminito, Buenos Aires |
  | `bariloche-2.jpg` | San Carlos de Bariloche, Río Negro |
  | `guanacos.jpg` | *(sin texto)* |
  | `casa-rosada.jpg` | Casa Rosada, Buenos Aires |
  | `floralis-generica.jpg` | Floralis Genérica, Buenos Aires |

- Imágenes ya comprimidas: 1920×1080 (16:9), JPEG calidad 70, progresivo, ~3,4 MB en total. La primera se pide con `fetchPriority="high"`, el resto con `low`.

### BuscadorVuelos (`components/BuscadorVuelos.tsx`)
- Card blanca `rounded-3xl`, sombra marcada, superpuesta al borde inferior del hero (`-mt-20`), ancho `max-w-[88rem]` (1408px), el mismo que el resto del contenido.
- Selector de tipo: píldoras `Ida y vuelta` / `Solo ida` (radio). Cada modo muestra sus campos:

  | Campo | Ida y vuelta | Solo ida (explorador) |
  |---|---|---|
  | Origen / Destino | obligatorios ("¿Desde dónde?" / "¿A dónde?") | opcionales ("Cualquiera"), al menos uno |
  | 3.º campo | **Ida** | **Desde** |
  | 4.º campo | **Vuelta** | **Hasta (opcional)** |

- Campos (una fila desde `lg`, apilados debajo), cada uno con etiqueta chica arriba:
  - **Origen** y **Destino**: `<select>` nativo con los aeropuertos ("Ciudad (IATA)"). Entre ambos, botón redondo ⇄ que los invierte.
  - Fechas: `<input type="date">` nativo (`min` = hoy / = la primera fecha).
  - **Pasajeros y clase**: dos `<select>` en el mismo bloque: 1–9 pasajeros y Economy / Primera.
  - Botón **Buscar** (naranja).
- Al cargar con query string, el formulario se completa con esos valores. Si la URL es inválida, los errores se marcan en cada campo (y el de precio en `FiltroPrecio`) hasta el primer envío.
- Validación (solo UX; el backend la repetirá), con mensaje bajo el campo:
  - ida y vuelta: origen y destino obligatorios; solo ida: al menos uno de los dos;
  - si están los dos, distintos y de ciudades distintas (AEP/EZE no);
  - códigos IATA que no están en la lista de aeropuertos → "No conocemos ese aeropuerto" (se valida recién con los aeropuertos cargados);
  - `clase` desconocida en la URL → error (no se cambia en silencio);
  - ida / desde obligatoria y ≥ hoy;
  - hasta ≥ desde y rango de hasta **14 días** (contando ambos extremos);
  - vuelta obligatoria en "Ida y vuelta" y ≥ ida;
  - pasajeros entre 1 y 9;
  - precio: montos ≥ 0 y mínimo ≤ máximo.
- La validación vive en una función pura `validarBusqueda(filtros, hoy)` que devuelve errores por campo.
- Al enviar sin errores, se escribe la query string (sin `idaId`, conservando el rango de precio). La búsqueda la dispara la página, no el formulario.

### FiltroPrecio (`components/FiltroPrecio.tsx`)
- Fila blanca sobre los resultados: "Precio por persona · {clase}", dos campos numéricos con `$` (Mínimo / Máximo), botón **Aplicar** y, si hay un rango aplicado, **Limpiar**.
- Al aplicar se valida con `validarPrecio(min, max)`; si está bien, se actualizan `precioMin` / `precioMax` en la URL y se vuelve a buscar.
- Se muestra siempre que haya búsqueda, aunque la URL sea inválida (así se puede corregir un rango mal cargado).

### CardVuelo (`components/CardVuelo.tsx`)
- Cabecera: título chico + `numero_vuelo`, badge "Directo".
- Cuerpo: hora de partida e IATA de origen · duración, línea con ✈ y fecha corta · hora de llegada e IATA de destino.
- Pie (fondo `slate-50`): "Por persona · {clase}", precio de la clase elegida en formato `es-AR` (`$ 175.512`), y asientos disponibles de esa clase. Con 5 o menos: "¡Quedan N asientos!" en naranja.
- Botón **Elegir** → `onElegir(vuelo)`. Hover: leve elevación y borde cielo.

### ListaVuelos (`components/ListaVuelos.tsx`)
- Título, subtítulo y los estados de una búsqueda.
- Grilla de 1 / 2 / 3 columnas (mobile / md / lg), contenedor `max-w-[88rem]`, el mismo que el buscador y el texto del hero: todo el contenido queda alineado en el mismo borde izquierdo y derecho.
- Muestra **12 cards** y un botón "Ver más vuelos (N)" que suma 12 más.
- Estados:
  - **Cargando**: 3 cards skeleton (`animate-pulse`).
  - **Sin resultados**: "No encontramos vuelos con esos criterios." + sugerencia: "Probá ampliar el rango de precio." si hay rango de precio; "Probá con un rango de fechas." si es solo ida de un día; "Probá con otras fechas." en el resto.
  - **Error**: "No pudimos buscar vuelos. Probá de nuevo." y botón Reintentar.

### Página Vuelos (`pages/Vuelos.tsx`)
Compone Hero + Buscador + FiltroPrecio + resultados y maneja el flujo por pasos según la query string:

1. Sin búsqueda: solo hero y buscador.
2. Con búsqueda y sin `idaId`: **Paso 1, Vuelo de ida.** `buscarVuelos(origen → destino, desde/hasta, precio)`.
3. Ida y vuelta con `idaId`: **Paso 2, Vuelo de vuelta.** `buscarVuelos(destino → origen, vuelta, precio)`, con un resumen del vuelo de ida elegido y un link "Cambiar" que quita `idaId`. Si la vuelta es el mismo día, solo se ofrecen las que salen después de que aterriza la ida.
4. Selección completa (solo ida con el vuelo elegido, o ida y vuelta con ambos): resumen de los vuelos y total = Σ precio × pasajeros, con el botón **Continuar** deshabilitado ("La compra llega pronto") y "Cambiar vuelos". La vuelta elegida se guarda en estado local, no en la URL, y se **limpia** con cada búsqueda, cambio de precio o cambio de ida.

Encabezado de resultados:
- Indicador de pasos (1 Vuelo de ida → 2 Vuelo de vuelta; en solo ida, solo el 1).
- Título: "Ciudad → Ciudad", "Desde Ciudad" (sin destino) o "Hacia Ciudad" (sin origen).
- Subtítulo: "fecha larga" o "Del 20 de octubre al 26 de octubre" · N pasajeros · Clase · N vuelos encontrados.

### Próximamente (`pages/Proximamente.tsx`)
Una sola página que recibe `titulo` y, opcionalmente, una acción (los botones demo de login y perfil).

## Datos y contrato con el backend (`lib/vuelos.ts`, `lib/auth.ts`, `lib/sesion.tsx`)

Tipos con los nombres del DBML. Los decimales llegan como `string` (DRF serializa `DecimalField` así); se formatean con `Number()` solo para mostrar.

```ts
type Clase = 'economy' | 'primera'
interface Aeropuerto { id: string; codigo_iata: string; nombre: string; ciudad: string; pais: string }
interface Vuelo {
  id: string; numero_vuelo: string
  origen: Aeropuerto; destino: Aeropuerto          // anidados en la respuesta de búsqueda
  fecha_operacion: string; hora_partida: string; hora_llegada: string  // 'YYYY-MM-DD', 'HH:MM:SS'
  precio_economy: string; precio_primera: string
  asientos_disponibles_economy: number; asientos_disponibles_primera: number
  estado: 'activo' | 'cancelado'
}
interface ParamsBusqueda {
  origen: string; destino: string                   // '' = cualquiera
  desde: string; hasta: string                      // hasta '' = solo el día desde
  pasajeros: number; clase: Clase
  precioMin: number | null; precioMax: number | null // por persona, en la clase
}
interface Usuario { id: string; email: string; nombre: string; apellido: string; rol: 'administrador' | 'empleado_mostrador' | 'pasajero' }
```

Funciones (las de datos son `async`, con una demora mock de ~400 ms):

| Función mock | Reemplazo futuro |
|---|---|
| `getAeropuertos(): Aeropuerto[]` | `api('/aeropuertos/')` |
| `buscarVuelos(params): Vuelo[]` | `api('/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=')` |
| `usuarioActual(): Usuario \| null` (sincrónica en el mock) | `api('/auth/yo/')` (endpoint nuevo, a sumar a `arquitectura.md`) |
| `loginDemo()` / `logout()` | `POST /auth/token/` / borrar tokens |

**Regla de búsqueda** (la cumple el mock y la deberá cumplir `GET /vuelos/buscar/`): vuelos `activo`, de la ruta pedida (origen y/o destino), con `fecha_operacion` dentro del rango, con `asientos_disponibles_<clase> >= pasajeros`, con `precio_<clase>` dentro del rango de precio y que **todavía no salieron** (si son de hoy, `hora_partida` posterior a la hora actual), ordenados por fecha y hora de partida.

Mock:
- 11 aeropuertos argentinos: AEP, EZE, BHI, BRC, COR, MDZ, IGR, USH, FTE, SLA, JUJ.
- Genera de forma **determinística** (semilla = ruta + fecha) entre 0 y 4 vuelos para cada par de ciudades distintas y cada fecha, con horarios, duración, precios y asientos verosímiles; alguna combinación devuelve 0 para poder ver el estado vacío. Sin origen o sin destino, combina todos los aeropuertos.
- `buscarVuelos(params, ahora = new Date())`: `ahora` se inyecta para poder probar "ya salió".
- Sesión: `loginDemo()` guarda un token falso en `localStorage.access` (la clave que ya usa `api.ts`). `usuarioActual()` devuelve un pasajero de prueba (Felipe Tourn) si hay token y `null` si no. El header se actualiza al loguearse o desloguearse: `SesionProvider` (contexto de React en `lib/sesion.tsx`) expone `{ usuario, loginDemo, logout }` y envuelve la app en `main.tsx`.

Si `getAeropuertos` falla: "No pudimos cargar los aeropuertos. Probá de nuevo." con Reintentar, y no se busca.

## Accesibilidad y responsive

- Cada campo con `<label>`, foco visible, botón ⇄ con `aria-label="Invertir origen y destino"`, avatar con `aria-label="Mi perfil"`, montos con `aria-label`.
- Se anuncia solo el resumen de resultados (`aria-live` en el subtítulo), la carga es `role="status"`, los errores `role="alert"`, el paso actual lleva `aria-current="step"` y cada control con error tiene `aria-invalid` + `aria-describedby`.
- Contraste: texto sobre el hero siempre sobre el velo marino.
- Responsive desde 360px: el buscador apila los campos, la fila de precio se acomoda y las cards van en una columna.

## Verificación

- `npm run build` (tipos) y `npm run lint` sin errores.
- `npm run check`: chequeos con `assert` (`scripts/check.ts`, corrido con `node --experimental-strip-types`) de `validarBusqueda`, `leerFiltros`/`aParams`, formato y `buscarVuelos` (cada criterio de aceptación, fechas inexistentes, vuelos que ya salieron, misma búsqueda → mismos resultados).
- Revisión manual en el navegador: ida y vuelta completa, explorador (solo origen, solo destino, rango), rango de precio, "Ver más", estados vacío y error, validaciones, login y logout demo, recarga con query string, botón atrás, vista mobile.

## Documentación

- Restaurar `CLAUDE.md` y `README.md` (borrados en `bd7e4a8`).
- `docs/modelo.dbml` actualizado con la versión de dbdiagram (`vendido_por`, `contacto_*`, índice único, CHECKs).
- Al cerrar: `docs/memoria.md` (estado, decisiones, pendientes resueltos por el DBML nuevo) y `docs/arquitectura.md` (`GET /auth/yo/` y el contrato completo de `GET /vuelos/buscar/`).
