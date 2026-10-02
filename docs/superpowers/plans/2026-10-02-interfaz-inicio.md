# Interfaz de inicio (Vuelos) — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pantalla de inicio del pasajero: header de marca, hero con carrusel de fondo, buscador de vuelos que cumple los criterios de aceptación de la user story (origen y/o destino, fecha o rango, rango de precio, sin cancelados, aviso claro sin resultados) y resultados en cards, con flujo en dos pasos para ida y vuelta. Todo con datos mock que tienen la forma de la futura API.

**Architecture:** SPA React con react-router. La lógica pura (filtros de búsqueda, formato, generación y filtrado de vuelos mock) vive en `src/lib/*.ts` y se verifica con un script de `assert` que corre Node. Los componentes de UI la consumen. El estado de búsqueda vive en la query string; la sesión mock en un contexto de React respaldado por `localStorage`.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS v4 (`@theme`), react-router-dom 7, Node 22.14 (`--experimental-strip-types` para los chequeos).

**Spec:** [docs/superpowers/specs/2026-10-02-interfaz-inicio-design.md](../specs/2026-10-02-interfaz-inicio-design.md)

## Global Constraints

- Textos de UI, nombres y commits en **español** (voseo rioplatense: "Elegí", "Probá").
- Campos de datos con los **mismos nombres que `docs/modelo.dbml`** (`codigo_iata`, `fecha_operacion`, `precio_economy`, `asientos_disponibles_primera`, …).
- **Sin dependencias nuevas.** Fuente Montserrat local (`src/fonts/*.woff2`), sin Google Fonts.
- Commits **sin** `Co-Authored-By` ni firmas: el único autor es el usuario.
- Archivos en `src/lib/` que importan otros de `src/lib/` lo hacen **con extensión `.ts` explícita** (Node los corre en `scripts/check.ts`).
- Paleta: `marino #064D7D`, `cielo #068EC1`, `naranja #FF6F13`, `ambar #FF9F1B`.
- Texto del hero, buscador, filtro de precio y resultados usan el mismo contenedor: `mx-auto max-w-[88rem] px-4`.
- Header: alto 80px (`h-20`), ancho completo, `px-4 md:px-8`; título 32px (`h-8`) y 40px desde `md` (`md:h-10`).
- Pasajeros: entre 1 y 9. Clases: `economy` | `primera`. Rango de fechas del explorador: hasta 14 días.
- Ningún componente hace `fetch` directo; los mocks de `src/lib/` se reemplazan después por `api(...)` de `src/lib/api.ts`.

## Review Focus

1. **Fechas que se corren un día o no existen:** `new Date('2026-10-26')` es medianoche UTC (el 25 en Argentina) y `2027-02-30` "existe" para `Date`. Esperado: siempre se muestra el día elegido y una fecha inexistente en la URL se rechaza. → chequeos en Task 1 con `TZ=America/Argentina/Buenos_Aires`.
2. **URL editada o vieja** (fecha pasada, `pasajeros=50`, rango de precio invertido, sin origen ni destino): no se busca, no se rompe, se pide revisar los datos y el filtro de precio sigue visible para corregirlo. → chequeos de `leerFiltros` + `validarBusqueda` en Task 1; la página no busca si no valida (Tasks 4 y 5).
3. **Nueva búsqueda o "Cambiar vuelos" después de elegir:** tiene que empezar de cero, sin arrastrar la ida ni la vuelta elegidas. → chequeo de que `aParams` no incluye `idaId` (Task 1) y verificación manual en Task 5 (elegir ida y vuelta → "Cambiar vuelos" → misma ida → debe aparecer el paso 2).
4. **Vuelos que no se pueden tomar:** cancelados, sin lugar para todos, fuera del rango de precio o que ya salieron hoy. Nunca aparecen. → chequeos de `buscarVuelos` en Task 2 (con `ahora` inyectado).
5. **Vuelta el mismo día que la ida:** no se ofrece una vuelta que sale antes de que aterrice la ida. → `vueltasPosibles` con chequeo en Task 2.

---

## Mapa de archivos

| Archivo | Responsabilidad |
|---|---|
| `frontend/scripts/check.ts` (nuevo) | Chequeos con `assert` de la lógica pura. `npm run check`. |
| `frontend/src/lib/busqueda.ts` (nuevo) | Tipo `Filtros`, validación, lectura/escritura de la query string. |
| `frontend/src/lib/formato.ts` (nuevo) | Formato de fechas, rangos, horas, precios y duración (es-AR). |
| `frontend/src/lib/vuelos.ts` (nuevo) | Tipos `Aeropuerto`/`Vuelo`/`ParamsBusqueda`, mock, `buscarVuelos` (regla del endpoint), helpers. |
| `frontend/src/lib/useVuelos.ts` (nuevo) | Hook que corre `buscarVuelos` y expone estado cargando/ok/error. |
| `frontend/src/lib/auth.ts` (nuevo) | Tipo `Usuario`, usuario demo, `iniciales`. |
| `frontend/src/lib/sesion.tsx` (nuevo) | `SesionProvider` + `useSesion` (contexto). |
| `frontend/src/fonts/*.woff2` (nuevos) | Montserrat 400–800. |
| `frontend/src/components/Header.tsx` (nuevo) | Header con navegación y sesión. |
| `frontend/src/components/HeroCarrusel.tsx` (nuevo) | Hero con fotos en fundido. |
| `frontend/src/components/BuscadorVuelos.tsx` (nuevo) | Formulario de búsqueda (ida y vuelta / explorador). |
| `frontend/src/components/FiltroPrecio.tsx` (nuevo) | Rango de precio por persona. |
| `frontend/src/components/CardVuelo.tsx` (nuevo) | Card de un vuelo. |
| `frontend/src/components/ListaVuelos.tsx` (nuevo) | Título + estados (cargando, vacío, error) + grilla con "Ver más". |
| `frontend/src/pages/Vuelos.tsx` (nuevo) | Página `/`: compone todo y maneja los pasos. |
| `frontend/src/pages/Proximamente.tsx`, `Login.tsx`, `Perfil.tsx` (nuevos) | Páginas mínimas. |
| `frontend/src/App.tsx`, `main.tsx`, `index.css`, `index.html`, `package.json` | Rutas, provider, tema, fuente, ícono, script `check`. |
| `frontend/public/título.svg` → `titulo.svg` | Renombrado (sin tilde en la URL). |
| `frontend/public/favicon.svg` | Se borra: el ícono de la pestaña pasa a ser `logo.svg`. |

---

### Task 1: Lógica de búsqueda y formato

**Files:**
- Create: `frontend/src/lib/busqueda.ts`
- Create: `frontend/src/lib/formato.ts`
- Create: `frontend/scripts/check.ts`
- Modify: `frontend/package.json` (script `check`)

**Interfaces:**
- Produces:
  - `type Clase = 'economy' | 'primera'`, `NOMBRE_CLASE: Record<Clase, string>`, `MAX_PASAJEROS = 9`, `MAX_DIAS_RANGO = 14`
  - `interface Filtros { origen: string; destino: string; ida: string; hasta: string; vuelta: string | null; pasajeros: number; clase: Clase; precioMin: number | null; precioMax: number | null }` (`vuelta: null` = solo ida/explorador; `origen`/`destino` `''` = cualquiera; `hasta` `''` = un solo día)
  - `type ErroresBusqueda = Partial<Record<'origen' | 'destino' | 'ida' | 'hasta' | 'vuelta' | 'pasajeros' | 'precio', string>>`
  - `hoyISO(): string`, `diasEntre(a: string, b: string): number`
  - `validarPrecio(min: number | null, max: number | null): string | undefined`
  - `validarBusqueda(f: Filtros, hoy: string): ErroresBusqueda`
  - `leerFiltros(p: URLSearchParams): Filtros | null` (hay búsqueda si está `ida`)
  - `aParams(f: Filtros): URLSearchParams`
  - `fechaLarga(iso)`, `fechaCorta(iso)`, `rangoFechas(desde, hasta)`, `hora(t)`, `precio(n)`, `duracion(min)` → `string`

- [ ] **Step 1: Agregar el script `check` a `frontend/package.json`**

En `"scripts"`, después de `"lint"`:

```json
    "lint": "oxlint",
    "check": "node --experimental-strip-types scripts/check.ts",
```

- [ ] **Step 2: Escribir los chequeos (fallan porque los módulos no existen)**

Crear `frontend/scripts/check.ts` (la Task 2 le agrega los chequeos de vuelos):

```ts
// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../src/lib/formato.ts'

const hoy = '2026-10-02'
const base: Filtros = {
  origen: 'BHI',
  destino: 'AEP',
  ida: '2026-10-26',
  hasta: '',
  vuelta: '2026-10-31',
  pasajeros: 2,
  clase: 'economy',
  precioMin: null,
  precioMax: null,
}
const soloIda: Filtros = { ...base, vuelta: null }

// validarBusqueda: ida y vuelta
assert.deepEqual(validarBusqueda(base, hoy), {})
assert.ok(validarBusqueda({ ...base, origen: '' }, hoy).origen, 'ida y vuelta pide origen')
assert.ok(validarBusqueda({ ...base, destino: '' }, hoy).destino, 'ida y vuelta pide destino')
assert.ok(validarBusqueda({ ...base, destino: 'BHI' }, hoy).destino, 'origen = destino')
assert.ok(validarBusqueda({ ...base, ida: '2026-10-01' }, hoy).ida, 'ida en el pasado')
assert.deepEqual(validarBusqueda({ ...base, ida: hoy, vuelta: hoy }, hoy), {}, 'ida hoy y vuelta el mismo día valen')
assert.ok(validarBusqueda({ ...base, vuelta: '' }, hoy).vuelta, 'ida y vuelta sin fecha de vuelta')
assert.ok(validarBusqueda({ ...base, vuelta: '2026-10-25' }, hoy).vuelta, 'vuelta antes que la ida')
assert.ok(validarBusqueda({ ...base, pasajeros: 0 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: 10 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: Number.NaN }, hoy).pasajeros)

// validarBusqueda: solo ida (explorador)
assert.deepEqual(validarBusqueda(soloIda, hoy), {})
assert.deepEqual(validarBusqueda({ ...soloIda, destino: '' }, hoy), {}, 'solo origen alcanza')
assert.deepEqual(validarBusqueda({ ...soloIda, origen: '' }, hoy), {}, 'solo destino alcanza')
assert.ok(validarBusqueda({ ...soloIda, origen: '', destino: '' }, hoy).origen, 'al menos uno de los dos')
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2026-11-08' }, hoy), {}, 'rango de 14 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-11-09' }, hoy).hasta, 'rango de 15 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-10-25' }, hoy).hasta, 'hasta antes que desde')

// validarBusqueda: precio
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000, precioMax: 200000 }, hoy), {})
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000 }, hoy), {}, 'solo mínimo')
assert.ok(validarBusqueda({ ...base, precioMin: 200000, precioMax: 100000 }, hoy).precio, 'mínimo > máximo')
assert.ok(validarBusqueda({ ...base, precioMin: -1 }, hoy).precio, 'precio negativo')
assert.ok(validarBusqueda({ ...base, precioMax: Number.NaN }, hoy).precio, 'precio no numérico')

// leerFiltros / aParams
assert.equal(leerFiltros(new URLSearchParams('')), null, 'sin búsqueda')
assert.deepEqual(leerFiltros(aParams(base)), base, 'ida y vuelta por la URL')
const explorador: Filtros = { ...soloIda, origen: '', hasta: '2026-10-30', precioMin: 50000, precioMax: 150000 }
assert.deepEqual(leerFiltros(aParams(explorador)), explorador, 'explorador por la URL')
assert.equal(aParams(base).has('idaId'), false, 'una búsqueda nueva no arrastra el vuelo elegido')
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&vuelta=2026-10-31&hasta=2026-10-28'))!.hasta, '', 'hasta solo en solo ida')
const basura = leerFiltros(new URLSearchParams('origen=bhi&destino=AEP&ida=mañana&vuelta=2026-13&pasajeros=50&clase=xx'))!
assert.equal(basura.origen, 'BHI')
assert.equal(basura.ida, '', 'fecha mal formada se descarta')
assert.equal(basura.clase, 'economy', 'clase desconocida → economy')
assert.ok(validarBusqueda(basura, hoy).ida && validarBusqueda(basura, hoy).vuelta && validarBusqueda(basura, hoy).pasajeros)
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2027-02-30'))!.ida, '', 'fecha inexistente se descarta')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-13-45'))!.ida, '', 'mes inexistente se descarta')

// formato
assert.ok(fechaLarga('2026-10-26').startsWith('Lunes') && fechaLarga('2026-10-26').includes('26'), fechaLarga('2026-10-26'))
assert.ok(fechaCorta('2026-10-26').startsWith('Lun') && fechaCorta('2026-10-26').includes('26'), fechaCorta('2026-10-26'))
assert.equal(rangoFechas('2026-10-20', '2026-10-25'), 'Del 20 de octubre al 25 de octubre')
assert.equal(hora('06:40:00'), '06:40')
assert.equal(precio(175512), '$ 175.512')
assert.equal(precio(149990.4), '$ 149.990')
assert.equal(duracion(85), '1 h 25 m')
assert.equal(duracion(120), '2 h')

console.log('busqueda + formato: OK')
```

- [ ] **Step 3: Correr y verificar que falla**

Run (desde `frontend/`): `npm run check`
Expected: FAIL con `ERR_MODULE_NOT_FOUND` (no existe `src/lib/busqueda.ts`).

- [ ] **Step 4: Implementar `frontend/src/lib/busqueda.ts`**

```ts
export type Clase = 'economy' | 'primera'

export const NOMBRE_CLASE: Record<Clase, string> = { economy: 'Economy', primera: 'Primera' }

export const MAX_PASAJEROS = 9

/** Máximo de días del rango "desde–hasta" del explorador (incluye ambos extremos). */
export const MAX_DIAS_RANGO = 14

/**
 * Filtros de búsqueda. Fechas en YYYY-MM-DD.
 * - `vuelta: null` = solo ida (explorador): origen o destino pueden ser '' (cualquiera) y `hasta` arma un rango.
 * - `vuelta: string` = ida y vuelta: origen y destino obligatorios, `hasta` siempre ''.
 * - `precioMin` / `precioMax`: por persona en la clase elegida; `null` = sin límite.
 */
export interface Filtros {
  origen: string
  destino: string
  ida: string
  hasta: string
  vuelta: string | null
  pasajeros: number
  clase: Clase
  precioMin: number | null
  precioMax: number | null
}

export type ErroresBusqueda = Partial<
  Record<'origen' | 'destino' | 'ida' | 'hasta' | 'vuelta' | 'pasajeros' | 'precio', string>
>

const FECHA = /^\d{4}-\d{2}-\d{2}$/

/** YYYY-MM-DD que además existe en el calendario (descarta 2027-02-30). */
function fechaValida(v: string): boolean {
  return FECHA.test(v) && new Date(`${v}T00:00:00`).toLocaleDateString('sv-SE') === v
}

/** Fecha local de hoy en YYYY-MM-DD (sv-SE formatea así). */
export function hoyISO(): string {
  return new Date().toLocaleDateString('sv-SE')
}

/** Días entre dos fechas ISO (b − a). */
export function diasEntre(a: string, b: string): number {
  return (Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000
}

/** Error del rango de precio, o undefined si está bien. */
export function validarPrecio(min: number | null, max: number | null): string | undefined {
  const mal = (n: number | null) => n !== null && (!Number.isFinite(n) || n < 0)
  if (mal(min) || mal(max)) return 'Ingresá montos válidos'
  if (min !== null && max !== null && min > max) return 'El mínimo no puede ser mayor que el máximo'
  return undefined
}

/** Solo UX: el backend repite estas reglas. Las fechas ISO se comparan como texto. */
export function validarBusqueda(f: Filtros, hoy: string): ErroresBusqueda {
  const e: ErroresBusqueda = {}
  if (f.vuelta === null) {
    if (!f.origen && !f.destino) e.origen = 'Elegí un origen, un destino o ambos'
  } else {
    if (!f.origen) e.origen = 'Elegí un origen'
    if (!f.destino) e.destino = 'Elegí un destino'
  }
  if (f.origen && f.destino === f.origen) e.destino = 'El destino tiene que ser distinto del origen'
  if (!f.ida) e.ida = 'Elegí la fecha'
  else if (f.ida < hoy) e.ida = 'La fecha no puede ser en el pasado'
  if (f.hasta && f.ida) {
    if (f.hasta < f.ida) e.hasta = 'No puede ser antes de "Desde"'
    else if (diasEntre(f.ida, f.hasta) + 1 > MAX_DIAS_RANGO) e.hasta = `El rango puede ser de hasta ${MAX_DIAS_RANGO} días`
  }
  if (f.vuelta !== null) {
    if (!f.vuelta) e.vuelta = 'Elegí la fecha de vuelta'
    else if (f.ida && f.vuelta < f.ida) e.vuelta = 'La vuelta no puede ser antes de la ida'
  }
  if (!Number.isInteger(f.pasajeros) || f.pasajeros < 1 || f.pasajeros > MAX_PASAJEROS) {
    e.pasajeros = `Entre 1 y ${MAX_PASAJEROS} pasajeros`
  }
  const precio = validarPrecio(f.precioMin, f.precioMax)
  if (precio) e.precio = precio
  return e
}

/** Lee la búsqueda de la URL. `null` si no hay búsqueda. No valida: eso lo hace `validarBusqueda`. */
export function leerFiltros(p: URLSearchParams): Filtros | null {
  if (!p.has('ida')) return null
  const fecha = (clave: string) => {
    const v = p.get(clave) ?? ''
    return fechaValida(v) ? v : ''
  }
  const monto = (clave: string) => {
    const v = p.get(clave)
    return v === null || v === '' ? null : Number(v)
  }
  const idaYVuelta = p.has('vuelta')
  return {
    origen: (p.get('origen') ?? '').toUpperCase(),
    destino: (p.get('destino') ?? '').toUpperCase(),
    ida: fecha('ida'),
    hasta: idaYVuelta ? '' : fecha('hasta'),
    vuelta: idaYVuelta ? fecha('vuelta') : null,
    pasajeros: Number(p.get('pasajeros') ?? 1),
    clase: p.get('clase') === 'primera' ? 'primera' : 'economy',
    precioMin: monto('precioMin'),
    precioMax: monto('precioMax'),
  }
}

/** Filtros → query string. Nunca incluye `idaId`: una búsqueda nueva empieza de cero. */
export function aParams(f: Filtros): URLSearchParams {
  const p = new URLSearchParams()
  if (f.origen) p.set('origen', f.origen)
  if (f.destino) p.set('destino', f.destino)
  p.set('ida', f.ida)
  if (f.vuelta !== null) p.set('vuelta', f.vuelta)
  else if (f.hasta) p.set('hasta', f.hasta)
  p.set('pasajeros', String(f.pasajeros))
  p.set('clase', f.clase)
  if (f.precioMin !== null) p.set('precioMin', String(f.precioMin))
  if (f.precioMax !== null) p.set('precioMax', String(f.precioMax))
  return p
}
```

- [ ] **Step 5: Implementar `frontend/src/lib/formato.ts`**

```ts
// Hora local, no UTC: new Date('2026-10-26') sería el 25 en Argentina.
const aFecha = (iso: string) => new Date(`${iso}T00:00:00`)
const mayuscula = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/** "Lunes, 26 de octubre" */
export function fechaLarga(iso: string): string {
  return mayuscula(aFecha(iso).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }))
}

/** "Lun, 26 oct" */
export function fechaCorta(iso: string): string {
  return mayuscula(aFecha(iso).toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' }))
}

/** "Del 20 de octubre al 25 de octubre" */
export function rangoFechas(desde: string, hasta: string): string {
  const diaMes = (iso: string) => aFecha(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long' })
  return `Del ${diaMes(desde)} al ${diaMes(hasta)}`
}

/** "06:40:00" → "06:40" */
export function hora(t: string): string {
  return t.slice(0, 5)
}

/** 175512 → "$ 175.512" */
export function precio(n: number): string {
  return `$ ${Math.round(n).toLocaleString('es-AR')}`
}

/** 85 → "1 h 25 m" */
export function duracion(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h} h ${m} m` : `${h} h`
}
```

- [ ] **Step 6: Correr y verificar que pasa**

Run: `npm run check`
Expected: `busqueda + formato: OK` (puede aparecer un `ExperimentalWarning` de Node: es normal).

- [ ] **Step 7: Verificar tipos y lint**

Run: `npm run build` y `npm run lint`
Expected: ambos sin errores.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/scripts/check.ts frontend/src/lib/busqueda.ts frontend/src/lib/formato.ts
git commit -m "feat(frontend): lógica de filtros de búsqueda y formato es-AR"
```

---

### Task 2: Datos mock y regla de búsqueda

**Files:**
- Create: `frontend/src/lib/vuelos.ts`
- Modify: `frontend/scripts/check.ts` (chequeos de vuelos)

**Interfaces:**
- Consumes: `Clase` de `busqueda.ts`.
- Produces:
  - `interface Aeropuerto { id; codigo_iata; nombre; ciudad; pais }`
  - `interface Vuelo { id; numero_vuelo; origen: Aeropuerto; destino: Aeropuerto; fecha_operacion; hora_partida; hora_llegada; precio_economy: string; precio_primera: string; asientos_disponibles_economy: number; asientos_disponibles_primera: number; estado: 'activo' | 'cancelado' }`
  - `interface ParamsBusqueda { origen: string; destino: string; desde: string; hasta: string; pasajeros: number; clase: Clase; precioMin: number | null; precioMax: number | null }`
  - `getAeropuertos(): Promise<Aeropuerto[]>`
  - `buscarVuelos(p: ParamsBusqueda, ahora?: Date): Promise<Vuelo[]>`
  - `generarVuelos(origen: string, destino: string, fecha: string): Vuelo[]` (exportado solo para los chequeos)
  - `precioDe(v, clase): number`, `asientosDe(v, clase): number`, `duracionDe(v): number` (minutos)
  - `vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[]`

- [ ] **Step 1: Reemplazar `frontend/scripts/check.ts` por la versión completa**

Suma el import de `vuelos.ts` y, al final, los chequeos de cada criterio de aceptación:

```ts
// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../src/lib/formato.ts'
import {
  asientosDe,
  buscarVuelos,
  duracionDe,
  generarVuelos,
  getAeropuertos,
  precioDe,
  vueltasPosibles,
  type ParamsBusqueda,
  type Vuelo,
} from '../src/lib/vuelos.ts'

const hoy = '2026-10-02'
const base: Filtros = {
  origen: 'BHI',
  destino: 'AEP',
  ida: '2026-10-26',
  hasta: '',
  vuelta: '2026-10-31',
  pasajeros: 2,
  clase: 'economy',
  precioMin: null,
  precioMax: null,
}
const soloIda: Filtros = { ...base, vuelta: null }

// validarBusqueda: ida y vuelta
assert.deepEqual(validarBusqueda(base, hoy), {})
assert.ok(validarBusqueda({ ...base, origen: '' }, hoy).origen, 'ida y vuelta pide origen')
assert.ok(validarBusqueda({ ...base, destino: '' }, hoy).destino, 'ida y vuelta pide destino')
assert.ok(validarBusqueda({ ...base, destino: 'BHI' }, hoy).destino, 'origen = destino')
assert.ok(validarBusqueda({ ...base, ida: '2026-10-01' }, hoy).ida, 'ida en el pasado')
assert.deepEqual(validarBusqueda({ ...base, ida: hoy, vuelta: hoy }, hoy), {}, 'ida hoy y vuelta el mismo día valen')
assert.ok(validarBusqueda({ ...base, vuelta: '' }, hoy).vuelta, 'ida y vuelta sin fecha de vuelta')
assert.ok(validarBusqueda({ ...base, vuelta: '2026-10-25' }, hoy).vuelta, 'vuelta antes que la ida')
assert.ok(validarBusqueda({ ...base, pasajeros: 0 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: 10 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: Number.NaN }, hoy).pasajeros)

// validarBusqueda: solo ida (explorador)
assert.deepEqual(validarBusqueda(soloIda, hoy), {})
assert.deepEqual(validarBusqueda({ ...soloIda, destino: '' }, hoy), {}, 'solo origen alcanza')
assert.deepEqual(validarBusqueda({ ...soloIda, origen: '' }, hoy), {}, 'solo destino alcanza')
assert.ok(validarBusqueda({ ...soloIda, origen: '', destino: '' }, hoy).origen, 'al menos uno de los dos')
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2026-11-08' }, hoy), {}, 'rango de 14 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-11-09' }, hoy).hasta, 'rango de 15 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-10-25' }, hoy).hasta, 'hasta antes que desde')

// validarBusqueda: precio
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000, precioMax: 200000 }, hoy), {})
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000 }, hoy), {}, 'solo mínimo')
assert.ok(validarBusqueda({ ...base, precioMin: 200000, precioMax: 100000 }, hoy).precio, 'mínimo > máximo')
assert.ok(validarBusqueda({ ...base, precioMin: -1 }, hoy).precio, 'precio negativo')
assert.ok(validarBusqueda({ ...base, precioMax: Number.NaN }, hoy).precio, 'precio no numérico')

// leerFiltros / aParams
assert.equal(leerFiltros(new URLSearchParams('')), null, 'sin búsqueda')
assert.deepEqual(leerFiltros(aParams(base)), base, 'ida y vuelta por la URL')
const explorador: Filtros = { ...soloIda, origen: '', hasta: '2026-10-30', precioMin: 50000, precioMax: 150000 }
assert.deepEqual(leerFiltros(aParams(explorador)), explorador, 'explorador por la URL')
assert.equal(aParams(base).has('idaId'), false, 'una búsqueda nueva no arrastra el vuelo elegido')
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&vuelta=2026-10-31&hasta=2026-10-28'))!.hasta, '', 'hasta solo en solo ida')
const basura = leerFiltros(new URLSearchParams('origen=bhi&destino=AEP&ida=mañana&vuelta=2026-13&pasajeros=50&clase=xx'))!
assert.equal(basura.origen, 'BHI')
assert.equal(basura.ida, '', 'fecha mal formada se descarta')
assert.equal(basura.clase, 'economy', 'clase desconocida → economy')
assert.ok(validarBusqueda(basura, hoy).ida && validarBusqueda(basura, hoy).vuelta && validarBusqueda(basura, hoy).pasajeros)
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2027-02-30'))!.ida, '', 'fecha inexistente se descarta')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-13-45'))!.ida, '', 'mes inexistente se descarta')

// formato
assert.ok(fechaLarga('2026-10-26').startsWith('Lunes') && fechaLarga('2026-10-26').includes('26'), fechaLarga('2026-10-26'))
assert.ok(fechaCorta('2026-10-26').startsWith('Lun') && fechaCorta('2026-10-26').includes('26'), fechaCorta('2026-10-26'))
assert.equal(rangoFechas('2026-10-20', '2026-10-25'), 'Del 20 de octubre al 25 de octubre')
assert.equal(hora('06:40:00'), '06:40')
assert.equal(precio(175512), '$ 175.512')
assert.equal(precio(149990.4), '$ 149.990')
assert.equal(duracion(85), '1 h 25 m')
assert.equal(duracion(120), '2 h')

console.log('busqueda + formato: OK')

// vuelos (mock)
const aeropuertos = await getAeropuertos()
assert.ok(aeropuertos.length >= 10)
assert.ok(aeropuertos.every((a) => /^[A-Z]{3}$/.test(a.codigo_iata)))

const ahora = new Date('2026-10-02T00:00:00') // medianoche local: nada del futuro "ya salió"
const p = (extra: Partial<ParamsBusqueda>): ParamsBusqueda => ({
  origen: 'BHI',
  destino: 'AEP',
  desde: '2026-10-20',
  hasta: '',
  pasajeros: 1,
  clase: 'economy',
  precioMin: null,
  precioMax: null,
  ...extra,
})

const dias = Array.from({ length: 60 }, (_, i) => new Date(Date.UTC(2026, 9, 3 + i)).toISOString().slice(0, 10))
const generados = dias.flatMap((d) => generarVuelos('BHI', 'AEP', d))
assert.ok(generados.some((v) => v.estado === 'cancelado'), 'el mock genera algún cancelado')
assert.ok(generados.every((v) => v.hora_llegada > v.hora_partida && duracionDe(v) > 0), 'llega el mismo día, después de salir')

for (const [pasajeros, clase] of [[1, 'economy'], [9, 'economy'], [3, 'primera']] as const) {
  const porDia = await Promise.all(dias.map((desde) => buscarVuelos(p({ desde, pasajeros, clase }), ahora)))
  for (const vuelos of porDia) {
    assert.ok(vuelos.every((v) => v.estado === 'activo'), 'nunca devuelve cancelados')
    assert.ok(vuelos.every((v) => asientosDe(v, clase) >= pasajeros), 'siempre hay lugar para todos')
    assert.deepEqual(vuelos.map((v) => v.hora_partida), vuelos.map((v) => v.hora_partida).toSorted(), 'ordenados por hora')
  }
  assert.ok(porDia.some((v) => v.length === 0), 'algún día sin vuelos (estado vacío)')
  assert.ok(porDia.some((v) => v.length > 0), 'algún día con vuelos')
}

const cor = p({ origen: 'COR', destino: 'BRC', desde: '2026-11-14' })
assert.deepEqual(await buscarVuelos(cor, ahora), await buscarVuelos(cor, ahora), 'misma búsqueda → mismos resultados')
assert.deepEqual(generarVuelos('AEP', 'AEP', '2026-11-14'), [], 'origen = destino')
assert.deepEqual(generarVuelos('ZZZ', 'AEP', '2026-11-14'), [], 'aeropuerto desconocido')

// explorador: solo origen, solo destino, rango de fechas
const desdeBHI = await buscarVuelos(p({ destino: '', hasta: '2026-10-26' }), ahora)
assert.ok(desdeBHI.every((v) => v.origen.codigo_iata === 'BHI'), 'solo origen: todos salen de BHI')
assert.ok(new Set(desdeBHI.map((v) => v.destino.codigo_iata)).size > 1, 'solo origen: varios destinos')
assert.ok(desdeBHI.every((v) => v.fecha_operacion >= '2026-10-20' && v.fecha_operacion <= '2026-10-26'), 'dentro del rango')
assert.ok(new Set(desdeBHI.map((v) => v.fecha_operacion)).size > 1, 'rango: varios días')
const orden = desdeBHI.map((v) => v.fecha_operacion + v.hora_partida)
assert.deepEqual(orden, orden.toSorted(), 'ordenados por fecha y hora')
const haciaUSH = await buscarVuelos(p({ origen: '', destino: 'USH', hasta: '2026-10-26' }), ahora)
assert.ok(haciaUSH.length > 0 && haciaUSH.every((v) => v.destino.codigo_iata === 'USH'), 'solo destino: todos llegan a USH')

// rango de precio (por persona, en la clase elegida)
const conPrecio = await buscarVuelos(p({ destino: '', hasta: '2026-10-26', precioMin: 120000, precioMax: 160000 }), ahora)
assert.ok(conPrecio.length > 0 && conPrecio.length < desdeBHI.length, 'el filtro de precio recorta')
assert.ok(conPrecio.every((v) => precioDe(v, 'economy') >= 120000 && precioDe(v, 'economy') <= 160000), 'dentro del rango de precio')

// vuelos de hoy que ya salieron no se ofrecen
const mediodia = new Date('2026-10-20T12:00:00')
const todosHoy = aeropuertos.flatMap((a) => generarVuelos('BHI', a.codigo_iata, '2026-10-20'))
assert.ok(todosHoy.some((v) => v.hora_partida < '12:00:00'), 'hay vuelos a la mañana para probar')
const hoyAlMediodia = await buscarVuelos(p({ destino: '' }), mediodia)
assert.ok(hoyAlMediodia.every((v) => v.hora_partida > '12:00:00'), 'solo vuelos que todavía no salieron')

// vueltasPosibles: misma fecha → solo las que salen después de que aterriza la ida
const ida = { fecha_operacion: '2026-11-14', hora_llegada: '12:00:00' } as Vuelo
const vueltas = [
  { id: 'a', fecha_operacion: '2026-11-14', hora_partida: '09:00:00' },
  { id: 'b', fecha_operacion: '2026-11-14', hora_partida: '15:00:00' },
] as Vuelo[]
assert.deepEqual(vueltasPosibles(vueltas, ida).map((v) => v.id), ['b'])
const otroDia = vueltas.map((v) => ({ ...v, fecha_operacion: '2026-11-15' }))
assert.equal(vueltasPosibles(otroDia, ida).length, 2, 'otro día: todas sirven')

console.log('vuelos: OK')
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `npm run check`
Expected: FAIL con `ERR_MODULE_NOT_FOUND` (no existe `src/lib/vuelos.ts`).

- [ ] **Step 3: Implementar `frontend/src/lib/vuelos.ts`**

```ts
import type { Clase } from './busqueda.ts'

// Tipos con la forma de la API (nombres de docs/modelo.dbml).
export interface Aeropuerto {
  id: string
  codigo_iata: string
  nombre: string
  ciudad: string
  pais: string
}

export interface Vuelo {
  id: string
  numero_vuelo: string
  origen: Aeropuerto
  destino: Aeropuerto
  fecha_operacion: string // YYYY-MM-DD
  hora_partida: string // HH:MM:SS
  hora_llegada: string
  precio_economy: string // decimal: DRF lo serializa como string
  precio_primera: string
  asientos_disponibles_economy: number
  asientos_disponibles_primera: number
  estado: 'activo' | 'cancelado'
}

/** `origen` / `destino` '' = cualquiera. `hasta` '' = solo el día `desde`. Precios por persona en `clase`. */
export interface ParamsBusqueda {
  origen: string
  destino: string
  desde: string
  hasta: string
  pasajeros: number
  clase: Clase
  precioMin: number | null
  precioMax: number | null
}

// ponytail: todo lo de abajo es mock. Al conectar el backend:
//   getAeropuertos → api('/aeropuertos/')
//   buscarVuelos   → api(`/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=`)
const aeropuerto = (codigo_iata: string, ciudad: string, nombre: string): Aeropuerto => ({
  id: codigo_iata,
  codigo_iata,
  nombre,
  ciudad,
  pais: 'Argentina',
})

const AEROPUERTOS: Aeropuerto[] = [
  aeropuerto('AEP', 'Buenos Aires', 'Aeroparque Jorge Newbery'),
  aeropuerto('EZE', 'Buenos Aires', 'Aeropuerto Internacional Ministro Pistarini'),
  aeropuerto('BHI', 'Bahía Blanca', 'Aeropuerto Comandante Espora'),
  aeropuerto('BRC', 'San Carlos de Bariloche', 'Aeropuerto Teniente Luis Candelaria'),
  aeropuerto('COR', 'Córdoba', 'Aeropuerto Ingeniero Ambrosio Taravella'),
  aeropuerto('MDZ', 'Mendoza', 'Aeropuerto El Plumerillo'),
  aeropuerto('IGR', 'Puerto Iguazú', 'Aeropuerto Cataratas del Iguazú'),
  aeropuerto('USH', 'Ushuaia', 'Aeropuerto Malvinas Argentinas'),
  aeropuerto('FTE', 'El Calafate', 'Aeropuerto Comandante Armando Tola'),
  aeropuerto('SLA', 'Salta', 'Aeropuerto Martín Miguel de Güemes'),
  aeropuerto('JUJ', 'San Salvador de Jujuy', 'Aeropuerto Horacio Guzmán'),
]

const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** FNV-1a: mismo texto → mismo número. */
function semilla(texto: string): number {
  let h = 2166136261
  for (let i = 0; i < texto.length; i++) h = Math.imul(h ^ texto.charCodeAt(i), 16777619)
  return h >>> 0
}

/** mulberry32: números "al azar" pero repetibles a partir de una semilla. */
function azar(s: number): () => number {
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const dosDigitos = (n: number) => String(n).padStart(2, '0')
const aHora = (min: number) => `${dosDigitos(Math.floor(min / 60))}:${dosDigitos(min % 60)}:00`
const aMinutos = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))

/** Vuelos de una ruta y fecha, sin filtrar. Determinístico. Exportado para los chequeos. */
export function generarVuelos(origen: string, destino: string, fecha: string): Vuelo[] {
  const o = AEROPUERTOS.find((a) => a.codigo_iata === origen)
  const d = AEROPUERTOS.find((a) => a.codigo_iata === destino)
  if (!o || !d || o.ciudad === d.ciudad) return []
  const ruta = semilla(`${origen}-${destino}`)
  const r = azar(semilla(`${origen}-${destino}-${fecha}`))
  const duracionMin = 60 + (ruta % 30) * 5 // 1 h a 3 h 25 m, fija por ruta
  const cantidad = Math.floor(r() * 5) // 0 a 4 vuelos ese día
  return Array.from({ length: cantidad }, (_, i): Vuelo => {
    const partida = (6 + i * 4) * 60 + Math.floor(r() * 8) * 15 // de 06:00 a 19:45: siempre llega antes de medianoche
    const economy = Math.round((40000 + duracionMin * 900 + r() * 40000) / 10) * 10
    const numero = `FA ${1000 + (ruta % 90) * 10 + i}`
    return {
      id: `${numero.replace(' ', '')}-${fecha}`,
      numero_vuelo: numero,
      origen: o,
      destino: d,
      fecha_operacion: fecha,
      hora_partida: aHora(partida),
      hora_llegada: aHora(partida + duracionMin),
      precio_economy: economy.toFixed(2),
      precio_primera: (Math.round((economy * 2.2) / 10) * 10).toFixed(2),
      asientos_disponibles_economy: Math.floor(r() * 40),
      asientos_disponibles_primera: Math.floor(r() * 10),
      estado: r() < 0.1 ? 'cancelado' : 'activo',
    }
  })
}

export async function getAeropuertos(): Promise<Aeropuerto[]> {
  await esperar(150)
  return AEROPUERTOS
}

export const precioDe = (v: Vuelo, clase: Clase) => Number(clase === 'economy' ? v.precio_economy : v.precio_primera)

export const asientosDe = (v: Vuelo, clase: Clase) =>
  clase === 'economy' ? v.asientos_disponibles_economy : v.asientos_disponibles_primera

/** Duración en minutos. */
export const duracionDe = (v: Vuelo) => aMinutos(v.hora_llegada) - aMinutos(v.hora_partida)

/** Fechas de `desde` a `hasta` inclusive ('' = solo `desde`). */
function fechasDelRango(desde: string, hasta: string): string[] {
  const fechas = [desde]
  while (hasta && fechas[fechas.length - 1] < hasta) {
    const d = new Date(`${fechas[fechas.length - 1]}T00:00:00Z`)
    d.setUTCDate(d.getUTCDate() + 1)
    fechas.push(d.toISOString().slice(0, 10))
  }
  return fechas
}

/**
 * Regla que debe cumplir GET /vuelos/buscar/: vuelos activos, con lugar para todos, dentro del rango de precio,
 * que todavía no salieron, ordenados por fecha y hora. `ahora` se inyecta para poder probarlo.
 */
export async function buscarVuelos(p: ParamsBusqueda, ahora = new Date()): Promise<Vuelo[]> {
  await esperar(400)
  const codigos = AEROPUERTOS.map((a) => a.codigo_iata)
  const origenes = p.origen ? [p.origen] : codigos
  const destinos = p.destino ? [p.destino] : codigos
  const hoy = ahora.toLocaleDateString('sv-SE')
  const horaActual = ahora.toTimeString().slice(0, 8)
  return fechasDelRango(p.desde, p.hasta)
    .flatMap((fecha) => origenes.flatMap((o) => destinos.flatMap((d) => generarVuelos(o, d, fecha))))
    .filter((v) => {
      const precio = precioDe(v, p.clase)
      return (
        v.estado === 'activo' &&
        asientosDe(v, p.clase) >= p.pasajeros &&
        (p.precioMin === null || precio >= p.precioMin) &&
        (p.precioMax === null || precio <= p.precioMax) &&
        !(v.fecha_operacion === hoy && v.hora_partida <= horaActual)
      )
    })
    .sort((a, b) => (a.fecha_operacion + a.hora_partida).localeCompare(b.fecha_operacion + b.hora_partida))
}

/** Si la vuelta es el mismo día que la ida, solo sirven las que salen después de que la ida aterriza. */
export function vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[] {
  return vueltas.filter((v) => v.fecha_operacion !== ida.fecha_operacion || v.hora_partida > ida.hora_llegada)
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `npm run check`
Expected: `busqueda + formato: OK` y `vuelos: OK`.
Si falla "algún día sin vuelos" o "algún cancelado" para BHI→AEP, no tocar los chequeos: ampliar `dias` a 120 (la semilla es fija).

- [ ] **Step 5: Verificar tipos y lint**

Run: `npm run build` y `npm run lint`
Expected: sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/scripts/check.ts frontend/src/lib/vuelos.ts
git commit -m "feat(frontend): mock de aeropuertos y vuelos con la forma de la API"
```

---

### Task 3: Tema, sesión mock, header y rutas

**Files:**
- Rename: `frontend/public/título.svg` → `frontend/public/titulo.svg`
- Delete: `frontend/public/favicon.svg`
- Create: `frontend/src/fonts/montserrat-latin-{400,500,600,700,800}-normal.woff2` (los provee el equipo)
- Modify: `frontend/index.html`, `frontend/src/index.css`, `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/lib/auth.ts`, `frontend/src/lib/sesion.tsx`
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/pages/Proximamente.tsx`, `Login.tsx`, `Perfil.tsx`

**Interfaces:**
- Produces:
  - `interface Usuario { id; email; nombre; apellido; rol: 'administrador' | 'empleado_mostrador' | 'pasajero' }`
  - `usuarioActual(): Usuario | null` (sincrónico en el mock; con backend pasa a `api('/auth/yo/')` async), `iniciales(u): string`, `CLAVE_TOKEN = 'access'`
  - `SesionProvider`, `useSesion(): { usuario; loginDemo(): void; logout(): void }`
  - `Proximamente({ titulo: string; children?: ReactNode })`
  - Clases Tailwind `marino`, `cielo`, `naranja`, `ambar`; `font-sans` = Montserrat.

- [ ] **Step 1: Renombrar el título y borrar el favicon viejo**

```bash
git mv "frontend/public/título.svg" frontend/public/titulo.svg
git rm frontend/public/favicon.svg
```

- [ ] **Step 2: `frontend/index.html`: idioma e ícono de la pestaña**

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/logo.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Fly Away</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Fuentes y `frontend/src/index.css`**

Copiar los 5 `.woff2` de Montserrat a `frontend/src/fonts/` y reemplazar `src/index.css`:

```css
@import "tailwindcss";

/* Montserrat local (subset latin: alcanza para el español) */
@font-face {
  font-family: "Montserrat";
  font-style: normal;
  font-weight: 400;
  font-display: swap;
  src: url("./fonts/montserrat-latin-400-normal.woff2") format("woff2");
}
@font-face {
  font-family: "Montserrat";
  font-style: normal;
  font-weight: 500;
  font-display: swap;
  src: url("./fonts/montserrat-latin-500-normal.woff2") format("woff2");
}
@font-face {
  font-family: "Montserrat";
  font-style: normal;
  font-weight: 600;
  font-display: swap;
  src: url("./fonts/montserrat-latin-600-normal.woff2") format("woff2");
}
@font-face {
  font-family: "Montserrat";
  font-style: normal;
  font-weight: 700;
  font-display: swap;
  src: url("./fonts/montserrat-latin-700-normal.woff2") format("woff2");
}
@font-face {
  font-family: "Montserrat";
  font-style: normal;
  font-weight: 800;
  font-display: swap;
  src: url("./fonts/montserrat-latin-800-normal.woff2") format("woff2");
}

@theme {
  --font-sans: "Montserrat", ui-sans-serif, system-ui, sans-serif;
  --color-marino: #064d7d;
  --color-cielo: #068ec1;
  --color-naranja: #ff6f13;
  --color-ambar: #ff9f1b;
}

/* Carrusel del hero: fundido + zoom lento */
.slide {
  opacity: 0;
  transform: scale(1.06);
  transition: opacity 1.6s ease-in-out;
}
.slide.on {
  opacity: 1;
  animation: acercar 8s linear forwards;
}
@keyframes acercar {
  from { transform: scale(1.06); }
  to { transform: scale(1); }
}
@media (prefers-reduced-motion: reduce) {
  .slide,
  .slide.on {
    transition: none;
    animation: none;
    transform: none;
  }
}
```

- [ ] **Step 4: Crear `frontend/src/lib/auth.ts`**

```ts
export interface Usuario {
  id: string
  email: string
  nombre: string
  apellido: string
  rol: 'administrador' | 'empleado_mostrador' | 'pasajero'
}

// ponytail: sesión mock. Con backend: login = POST /auth/token/ y usuarioActual = api('/auth/yo/') (async).
const USUARIO_DEMO: Usuario = {
  id: 'demo',
  email: 'felipe@flyaway.com',
  nombre: 'Felipe',
  apellido: 'Tourn',
  rol: 'pasajero',
}

/** Misma clave que usa api.ts para el JWT. */
export const CLAVE_TOKEN = 'access'

export function usuarioActual(): Usuario | null {
  return localStorage.getItem(CLAVE_TOKEN) ? USUARIO_DEMO : null
}

export function iniciales(u: Usuario): string {
  return `${u.nombre.charAt(0)}${u.apellido.charAt(0)}`.toUpperCase()
}
```

- [ ] **Step 5: Crear `frontend/src/lib/sesion.tsx`**

```tsx
import { createContext, use, useState, type ReactNode } from 'react'
import { CLAVE_TOKEN, usuarioActual, type Usuario } from './auth.ts'

interface Sesion {
  usuario: Usuario | null
  loginDemo: () => void
  logout: () => void
}

const SesionContext = createContext<Sesion | null>(null)

export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState(usuarioActual)

  const loginDemo = () => {
    localStorage.setItem(CLAVE_TOKEN, 'demo')
    setUsuario(usuarioActual())
  }
  const logout = () => {
    localStorage.removeItem(CLAVE_TOKEN)
    localStorage.removeItem('refresh')
    setUsuario(null)
  }

  return <SesionContext value={{ usuario, loginDemo, logout }}>{children}</SesionContext>
}

export function useSesion(): Sesion {
  const sesion = use(SesionContext)
  if (!sesion) throw new Error('useSesion se usa dentro de <SesionProvider>')
  return sesion
}
```

- [ ] **Step 6: `frontend/src/main.tsx`: envolver con el provider**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.tsx'
import { SesionProvider } from './lib/sesion.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <SesionProvider>
        <App />
      </SesionProvider>
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 7: Crear `frontend/src/components/Header.tsx`**

En pantallas < `sm` (640px) no entra todo en una fila: se muestra el ícono del avión en lugar del título y, sin sesión, un único link "Ingresar" (la página de login tiene el link a registro).

```tsx
import { Link, NavLink } from 'react-router-dom'
import { iniciales } from '../lib/auth'
import { useSesion } from '../lib/sesion'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `relative rounded-full px-2 py-2 sm:px-3 ${
    isActive
      ? 'text-marino after:absolute after:inset-x-3 after:-bottom-[22px] after:h-[3px] after:rounded-full after:bg-naranja'
      : 'text-slate-500 hover:text-marino'
  }`

export default function Header() {
  const { usuario } = useSesion()
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/90 backdrop-blur">
      <div className="flex h-20 items-center justify-between gap-3 px-4 md:px-8">
        <Link to="/" aria-label="Fly Away, inicio" className="shrink-0">
          <img src="/logo.svg" alt="" className="h-9 sm:hidden" />
          <img src="/titulo.svg" alt="" className="hidden h-8 sm:block md:h-10" />
        </Link>
        <nav className="flex items-center gap-1 text-xs font-semibold sm:text-sm md:gap-2">
          <NavLink to="/" end className={navLink}>
            Vuelos
          </NavLink>
          <NavLink to="/reservas" className={navLink}>
            Reservas
          </NavLink>
          <span className="mx-1 h-6 w-px bg-slate-200" aria-hidden="true" />
          {usuario ? (
            <Link
              to="/perfil"
              title="Mi perfil"
              aria-label="Mi perfil"
              className="grid h-10 w-10 place-items-center rounded-full bg-linear-to-br from-naranja to-ambar text-sm font-bold text-white shadow ring-2 ring-white"
            >
              {iniciales(usuario)}
            </Link>
          ) : (
            <>
              <Link to="/login" className="rounded-full px-2 py-2 text-marino hover:bg-slate-100 sm:px-3">
                <span className="sm:hidden">Ingresar</span>
                <span className="hidden sm:inline">Iniciar sesión</span>
              </Link>
              <span className="hidden text-slate-300 sm:inline" aria-hidden="true">
                |
              </span>
              <Link
                to="/registro"
                className="ml-2 hidden rounded-full bg-marino px-4 py-2 text-white hover:bg-cielo sm:inline-block"
              >
                Registrarse
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
```

- [ ] **Step 8: Crear las páginas mínimas**

`frontend/src/pages/Proximamente.tsx`:

```tsx
import type { ReactNode } from 'react'

export default function Proximamente({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <main className="mx-auto max-w-[88rem] px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">{titulo}</h1>
      <p className="mt-2 text-slate-500">Próximamente.</p>
      {children && <div className="mt-6">{children}</div>}
    </main>
  )
}
```

`frontend/src/pages/Login.tsx`:

```tsx
import { Link, useNavigate } from 'react-router-dom'
import { useSesion } from '../lib/sesion'
import Proximamente from './Proximamente'

export default function Login() {
  const { loginDemo } = useSesion()
  const navigate = useNavigate()
  return (
    <Proximamente titulo="Iniciar sesión">
      <button
        type="button"
        onClick={() => {
          loginDemo()
          navigate('/')
        }}
        className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo"
      >
        Entrar (demo)
      </button>
      <p className="mt-4 text-sm text-slate-500">
        ¿No tenés cuenta?{' '}
        <Link to="/registro" className="font-semibold text-marino underline">
          Registrate
        </Link>
      </p>
    </Proximamente>
  )
}
```

`frontend/src/pages/Perfil.tsx`:

```tsx
import { Link, useNavigate } from 'react-router-dom'
import { useSesion } from '../lib/sesion'
import Proximamente from './Proximamente'

export default function Perfil() {
  const { usuario, logout } = useSesion()
  const navigate = useNavigate()

  if (!usuario) {
    return (
      <Proximamente titulo="Mi perfil">
        <Link to="/login" className="font-semibold text-marino underline">
          Iniciá sesión
        </Link>{' '}
        para ver tu perfil.
      </Proximamente>
    )
  }

  return (
    <Proximamente titulo={`${usuario.nombre} ${usuario.apellido}`}>
      <p className="mb-4 text-slate-500">{usuario.email}</p>
      <button
        type="button"
        onClick={() => {
          logout()
          navigate('/')
        }}
        className="rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-white"
      >
        Cerrar sesión
      </button>
    </Proximamente>
  )
}
```

- [ ] **Step 9: `frontend/src/App.tsx`: rutas con layout del pasajero**

La ruta `/` muestra temporalmente `Proximamente`; la Task 4 la reemplaza por `Vuelos`.

```tsx
import { Outlet, Route, Routes } from 'react-router-dom'
import Header from './components/Header'
import Login from './pages/Login'
import Perfil from './pages/Perfil'
import Proximamente from './pages/Proximamente'

function LayoutPasajero() {
  return (
    <>
      <Header />
      <Outlet />
    </>
  )
}

// Una ruta raíz por tipo de usuario (misma UI, distintas funcionalidades).
export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <Routes>
        <Route element={<LayoutPasajero />}>
          <Route index element={<Proximamente titulo="Vuelos" />} />
          <Route path="reservas" element={<Proximamente titulo="Mis reservas" />} />
          <Route path="perfil" element={<Perfil />} />
          <Route path="login" element={<Login />} />
          <Route path="registro" element={<Proximamente titulo="Registrarse" />} />
        </Route>
        <Route path="/mostrador/*" element={<h1 className="p-8 text-2xl">Mostrador</h1>} />
        <Route path="/admin/*" element={<h1 className="p-8 text-2xl">Administración</h1>} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 10: Verificar build, lint y chequeos**

Run: `npm run build`, `npm run lint`, `npm run check`
Expected: sin errores. `oxlint` advierte `only-export-components` en `sesion.tsx` (exporta un hook junto al provider): es una advertencia aceptada.

- [ ] **Step 11: Verificación manual**

Run: `npm run dev` y abrir http://localhost:5173
Expected:
- Pestaña con el ícono del avión. Texto en Montserrat.
- Header blanco de 80px, título FLY AWAY a 40px pegado a la izquierda; a la derecha Vuelos (subrayado naranja), Reservas, `|`, "Iniciar sesión | Registrarse".
- Click en Reservas: el subrayado pasa a Reservas.
- `/login` → "Entrar (demo)" → vuelve a `/` con el círculo "FT". Click en el círculo → `/perfil` con nombre, email y "Cerrar sesión" → vuelve a `/` sin sesión.
- Recargar con sesión iniciada: sigue el círculo "FT".
- 360px de ancho: ícono del avión, "Vuelos Reservas | Ingresar" en una fila, sin scroll horizontal.

- [ ] **Step 12: Commit**

```bash
git add -A frontend/public frontend/index.html frontend/src
git commit -m "feat(frontend): tema de marca, header con sesión mock y rutas del pasajero"
```

---

### Task 4: Hero con carrusel y buscador

**Files:**
- Create: `frontend/src/components/HeroCarrusel.tsx`
- Create: `frontend/src/components/BuscadorVuelos.tsx`
- Create: `frontend/src/pages/Vuelos.tsx`
- Modify: `frontend/src/App.tsx` (ruta index → `Vuelos`)

**Interfaces:**
- Consumes: `Filtros`, `Clase`, `ErroresBusqueda`, `MAX_PASAJEROS`, `hoyISO`, `validarBusqueda`, `leerFiltros`, `aParams` (Task 1); `Aeropuerto`, `getAeropuertos` (Task 2).
- Produces:
  - `HeroCarrusel()` sin props.
  - `BuscadorVuelos({ aeropuertos: Aeropuerto[]; inicial: Filtros | null; onBuscar: (f: Filtros) => void })`. Lee `inicial` solo al montar: el que lo usa le pasa una `key` que cambia con la búsqueda. Conserva `precioMin`/`precioMax` de `inicial`.
  - `Vuelos()` página (Task 5 le agrega los resultados).

- [ ] **Step 1: Crear `frontend/src/components/HeroCarrusel.tsx`**

```tsx
import { useEffect, useState } from 'react'

// Orden de aparición y texto de la esquina ('' = sin texto).
const FOTOS: [archivo: string, lugar: string][] = [
  ['perito-moreno.jpg', 'Glaciar Perito Moreno, El Calafate'],
  ['ushuaia.jpg', 'Faro Les Éclaireurs, Ushuaia'],
  ['hornocal.jpg', 'Serranía de Hornocal, Humahuaca, Jujuy'],
  ['obelisco.jpg', 'Obelisco, Buenos Aires'],
  ['bariloche-1.jpg', 'San Carlos de Bariloche, Río Negro'],
  ['cafayate.jpg', 'Cafayate, Salta'],
  ['caminito.jpg', 'Caminito, Buenos Aires'],
  ['bariloche-2.jpg', 'San Carlos de Bariloche, Río Negro'],
  ['guanacos.jpg', ''],
  ['casa-rosada.jpg', 'Casa Rosada, Buenos Aires'],
  ['floralis-generica.jpg', 'Floralis Genérica, Buenos Aires'],
]

export default function HeroCarrusel() {
  const [actual, setActual] = useState(0)

  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setActual((i) => (i + 1) % FOTOS.length), 6000)
    return () => clearInterval(id)
  }, [])

  return (
    <section className="relative h-[62vh] min-h-[420px] overflow-hidden bg-marino">
      <div aria-hidden="true">
        {FOTOS.map(([archivo], i) => (
          <img
            key={archivo}
            src={`/destinos/${archivo}`}
            alt=""
            fetchPriority={i === 0 ? 'high' : 'low'}
            className={`slide absolute inset-0 h-full w-full object-cover ${i === actual ? 'on' : ''}`}
          />
        ))}
      </div>
      <div className="absolute inset-0 bg-linear-to-b from-marino/60 via-marino/25 to-marino/70" />
      <div className="relative mx-auto flex h-full max-w-[88rem] flex-col justify-center px-4 pb-24">
        <p className="mb-3 text-sm font-semibold tracking-[0.2em] text-ambar uppercase">Volá por toda la Argentina</p>
        <h1 className="text-4xl leading-tight font-extrabold text-white md:text-6xl md:whitespace-nowrap">
          ¿A dónde querés ir?
        </h1>
      </div>
      <p aria-hidden="true" className="absolute right-4 bottom-24 text-xs font-medium text-white/80 md:right-8">
        {FOTOS[actual][1]}
      </p>
    </section>
  )
}
```

- [ ] **Step 2: Crear `frontend/src/components/BuscadorVuelos.tsx`**

Debajo de `lg` (1024px) los campos se apilan; desde `lg` van en una fila. "Solo ida" es el explorador: origen/destino con "Cualquiera" y fechas "Desde" / "Hasta (opcional)".

```tsx
import { useState, type FormEvent } from 'react'
import {
  MAX_PASAJEROS,
  hoyISO,
  validarBusqueda,
  type Clase,
  type ErroresBusqueda,
  type Filtros,
} from '../lib/busqueda'
import type { Aeropuerto } from '../lib/vuelos'

interface Props {
  aeropuertos: Aeropuerto[]
  inicial: Filtros | null
  onBuscar: (f: Filtros) => void
}

const caja = 'rounded-2xl border border-slate-200 px-4 py-2.5 focus-within:border-cielo'
const etiqueta = 'block text-xs font-semibold text-slate-500'
const control = 'w-full bg-transparent font-semibold outline-none'
const pildora = (activa: boolean) =>
  `cursor-pointer rounded-full px-4 py-1.5 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-cielo ${
    activa ? 'bg-marino text-white' : 'text-slate-500 hover:bg-slate-100'
  }`

function MensajeError({ id, texto }: { id: string; texto?: string }) {
  return texto ? (
    <p id={id} className="mt-1 px-1 text-xs font-medium text-red-600">
      {texto}
    </p>
  ) : null
}

export default function BuscadorVuelos({ aeropuertos, inicial, onBuscar }: Props) {
  const pasajerosIniciales = inicial?.pasajeros ?? 1
  const [soloIda, setSoloIda] = useState(inicial?.vuelta === null)
  const [origen, setOrigen] = useState(inicial?.origen ?? '')
  const [destino, setDestino] = useState(inicial?.destino ?? '')
  const [ida, setIda] = useState(inicial?.ida ?? '')
  const [hasta, setHasta] = useState(inicial?.hasta ?? '')
  const [vuelta, setVuelta] = useState(inicial?.vuelta ?? '')
  const [pasajeros, setPasajeros] = useState(
    Number.isInteger(pasajerosIniciales) && pasajerosIniciales >= 1 && pasajerosIniciales <= MAX_PASAJEROS
      ? pasajerosIniciales
      : 1,
  )
  const [clase, setClase] = useState<Clase>(inicial?.clase ?? 'economy')
  const [errores, setErrores] = useState<ErroresBusqueda>({})
  const hoy = hoyISO()

  function enviar(e: FormEvent) {
    e.preventDefault()
    const filtros: Filtros = {
      origen,
      destino,
      ida,
      hasta: soloIda ? hasta : '',
      vuelta: soloIda ? null : vuelta,
      pasajeros,
      clase,
      // El rango de precio se edita sobre los resultados; una búsqueda nueva lo conserva.
      precioMin: inicial?.precioMin ?? null,
      precioMax: inicial?.precioMax ?? null,
    }
    const nuevos = validarBusqueda(filtros, hoy)
    setErrores(nuevos)
    if (Object.keys(nuevos).length === 0) onBuscar(filtros)
  }

  function invertir() {
    setOrigen(destino)
    setDestino(origen)
  }

  const opciones = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <form onSubmit={enviar} noValidate className="rounded-3xl bg-white p-4 shadow-2xl shadow-marino/20 md:p-6">
      <fieldset className="mb-4 flex gap-2 text-sm font-semibold">
        <legend className="sr-only">Tipo de viaje</legend>
        <label className={pildora(!soloIda)}>
          <input type="radio" name="tipo" className="sr-only" checked={!soloIda} onChange={() => setSoloIda(false)} />
          Ida y vuelta
        </label>
        <label className={pildora(soloIda)}>
          <input type="radio" name="tipo" className="sr-only" checked={soloIda} onChange={() => setSoloIda(true)} />
          Solo ida
        </label>
      </fieldset>

      <div className="grid gap-2 lg:grid-cols-[1fr_auto_1fr_1fr_1fr_1.3fr_auto] lg:items-start">
        <div>
          <div className={caja}>
            <label htmlFor="origen" className={etiqueta}>
              Origen
            </label>
            <select
              id="origen"
              value={origen}
              onChange={(e) => setOrigen(e.target.value)}
              aria-invalid={!!errores.origen}
              aria-describedby="error-origen"
              className={control}
            >
              {/* En solo ida el origen es opcional: "Cualquiera". */}
              <option value="" disabled={!soloIda}>
                {soloIda ? 'Cualquiera' : '¿Desde dónde?'}
              </option>
              {opciones}
            </select>
          </div>
          <MensajeError id="error-origen" texto={errores.origen} />
        </div>

        <button
          type="button"
          onClick={invertir}
          aria-label="Invertir origen y destino"
          className="z-10 mx-auto -my-3 grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white text-marino shadow-sm hover:bg-slate-50 lg:-mx-4 lg:my-0 lg:mt-3.5"
        >
          ⇄
        </button>

        <div>
          <div className={caja}>
            <label htmlFor="destino" className={etiqueta}>
              Destino
            </label>
            <select
              id="destino"
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              aria-invalid={!!errores.destino}
              aria-describedby="error-destino"
              className={control}
            >
              <option value="" disabled={!soloIda}>
                {soloIda ? 'Cualquiera' : '¿A dónde?'}
              </option>
              {opciones}
            </select>
          </div>
          <MensajeError id="error-destino" texto={errores.destino} />
        </div>

        <div>
          <div className={caja}>
            <label htmlFor="ida" className={etiqueta}>
              {soloIda ? 'Desde' : 'Ida'}
            </label>
            <input
              id="ida"
              type="date"
              min={hoy}
              value={ida}
              onChange={(e) => setIda(e.target.value)}
              aria-invalid={!!errores.ida}
              aria-describedby="error-ida"
              className={control}
            />
          </div>
          <MensajeError id="error-ida" texto={errores.ida} />
        </div>

        {soloIda ? (
          <div>
            <div className={caja}>
              <label htmlFor="hasta" className={etiqueta}>
                Hasta <span className="font-normal">(opcional)</span>
              </label>
              <input
                id="hasta"
                type="date"
                min={ida || hoy}
                value={hasta}
                onChange={(e) => setHasta(e.target.value)}
                aria-invalid={!!errores.hasta}
                aria-describedby="error-hasta"
                className={control}
              />
            </div>
            <MensajeError id="error-hasta" texto={errores.hasta} />
          </div>
        ) : (
          <div>
            <div className={caja}>
              <label htmlFor="vuelta" className={etiqueta}>
                Vuelta
              </label>
              <input
                id="vuelta"
                type="date"
                min={ida || hoy}
                value={vuelta}
                onChange={(e) => setVuelta(e.target.value)}
                aria-invalid={!!errores.vuelta}
                aria-describedby="error-vuelta"
                className={control}
              />
            </div>
            <MensajeError id="error-vuelta" texto={errores.vuelta} />
          </div>
        )}

        <div>
          <div className={caja}>
            <span className={etiqueta}>Pasajeros y clase</span>
            <div className="flex gap-2">
              <select
                aria-label="Pasajeros"
                value={pasajeros}
                onChange={(e) => setPasajeros(Number(e.target.value))}
                className={control}
              >
                {Array.from({ length: MAX_PASAJEROS }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    {n} {n === 1 ? 'pasajero' : 'pasajeros'}
                  </option>
                ))}
              </select>
              <select
                aria-label="Clase"
                value={clase}
                onChange={(e) => setClase(e.target.value as Clase)}
                className={control}
              >
                <option value="economy">Economy</option>
                <option value="primera">Primera</option>
              </select>
            </div>
          </div>
          <MensajeError id="error-pasajeros" texto={errores.pasajeros} />
        </div>

        <button
          type="submit"
          className="min-h-[62px] rounded-2xl bg-naranja px-7 text-base font-bold text-white shadow-lg shadow-naranja/30 hover:bg-[#f0600a]"
        >
          Buscar
        </button>
      </div>
    </form>
  )
}
```

- [ ] **Step 3: Crear `frontend/src/pages/Vuelos.tsx` (sin resultados todavía)**

```tsx
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import BuscadorVuelos from '../components/BuscadorVuelos'
import HeroCarrusel from '../components/HeroCarrusel'
import { aParams, hoyISO, leerFiltros, validarBusqueda, type Filtros } from '../lib/busqueda'
import { getAeropuertos, type Aeropuerto } from '../lib/vuelos'

export default function Vuelos() {
  const [params, setParams] = useSearchParams()
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])

  useEffect(() => {
    getAeropuertos().then(setAeropuertos)
  }, [])

  const filtros = leerFiltros(params)
  // Solo se busca con filtros válidos: la URL puede venir editada o ser de otro día.
  const f = filtros && Object.keys(validarBusqueda(filtros, hoyISO())).length === 0 ? filtros : null
  // Cambia con cada búsqueda (sin idaId): remonta el buscador con los valores de la URL.
  const claveFiltros = filtros ? aParams(filtros).toString() : ''

  function buscar(nuevos: Filtros) {
    setParams(aParams(nuevos))
  }

  return (
    <>
      <HeroCarrusel />
      <section className="relative z-10 mx-auto -mt-20 max-w-[88rem] px-4">
        <BuscadorVuelos key={claveFiltros} aeropuertos={aeropuertos} inicial={filtros} onBuscar={buscar} />
      </section>
      <main className="mx-auto max-w-[88rem] px-4 py-10">
        {filtros && !f && <p className="text-slate-500">Revisá los datos de la búsqueda y volvé a buscar.</p>}
      </main>
    </>
  )
}
```

- [ ] **Step 4: `frontend/src/App.tsx`: usar `Vuelos` en `/`**

```tsx
import { Outlet, Route, Routes } from 'react-router-dom'
import Header from './components/Header'
import Login from './pages/Login'
import Perfil from './pages/Perfil'
import Proximamente from './pages/Proximamente'
import Vuelos from './pages/Vuelos'

function LayoutPasajero() {
  return (
    <>
      <Header />
      <Outlet />
    </>
  )
}

// Una ruta raíz por tipo de usuario (misma UI, distintas funcionalidades).
export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <Routes>
        <Route element={<LayoutPasajero />}>
          <Route index element={<Vuelos />} />
          <Route path="reservas" element={<Proximamente titulo="Mis reservas" />} />
          <Route path="perfil" element={<Perfil />} />
          <Route path="login" element={<Login />} />
          <Route path="registro" element={<Proximamente titulo="Registrarse" />} />
        </Route>
        <Route path="/mostrador/*" element={<h1 className="p-8 text-2xl">Mostrador</h1>} />
        <Route path="/admin/*" element={<h1 className="p-8 text-2xl">Administración</h1>} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 5: Verificar build, lint y chequeos**

Run: `npm run build`, `npm run lint`, `npm run check`
Expected: sin errores.

- [ ] **Step 6: Verificación manual**

Run: `npm run dev`, abrir http://localhost:5173
Expected:
- Hero de ~62% de la pantalla con las fotos en fundido cada 6 s y el lugar abajo a la derecha (vacío en la de los guanacos).
- "Volá por toda la Argentina" / "¿A dónde querés ir?" en una línea, alineado a la izquierda con el borde de la card del buscador.
- Ida y vuelta, buscar vacío: errores debajo de origen, destino, ida y vuelta. Origen = destino: error en Destino. ⇄ invierte origen y destino.
- Solo ida: los selects ofrecen "Cualquiera", las fechas pasan a "Desde" / "Hasta (opcional)". Sin origen ni destino: "Elegí un origen, un destino o ambos". Rango de 15 días: error en Hasta.
- Búsqueda válida: la URL refleja los filtros. Recargar: el formulario se completa igual.
- `/?origen=BHI&destino=AEP&ida=2020-01-01&pasajeros=1&clase=economy` y `/?origen=BHI&ida=2027-02-30&pasajeros=1&clase=economy` muestran "Revisá los datos de la búsqueda…".
- DevTools > Rendering > "prefers-reduced-motion: reduce": queda fija la primera foto.
- 360px de ancho: campos apilados, sin scroll horizontal.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): hero con carrusel de destinos y buscador de vuelos"
```

---

### Task 5: Resultados, filtro de precio y pasos

**Files:**
- Create: `frontend/src/lib/useVuelos.ts`
- Create: `frontend/src/components/CardVuelo.tsx`
- Create: `frontend/src/components/ListaVuelos.tsx`
- Create: `frontend/src/components/FiltroPrecio.tsx`
- Modify: `frontend/src/pages/Vuelos.tsx`

**Interfaces:**
- Consumes: `buscarVuelos`, `ParamsBusqueda`, `Vuelo`, `precioDe`, `asientosDe`, `duracionDe`, `vueltasPosibles` (Task 2); `Clase`, `NOMBRE_CLASE`, `validarPrecio`, `aParams` (Task 1); `fechaLarga`, `fechaCorta`, `rangoFechas`, `hora`, `precio`, `duracion` (Task 1).
- Produces:
  - `type EstadoBusqueda = 'inactivo' | 'cargando' | 'ok' | 'error'`
  - `useVuelos(params: ParamsBusqueda | null): { estado; vuelos: Vuelo[]; reintentar(): void }`
  - `CardVuelo({ vuelo; clase; onElegir })`
  - `ListaVuelos({ titulo; subtitulo; estado; vuelos; clase; sugerencia; onElegir; onReintentar })` (se resetea con `key`)
  - `FiltroPrecio({ min; max; clase; onAplicar(min, max) })` (se resetea con `key`)

- [ ] **Step 1: Crear `frontend/src/lib/useVuelos.ts`**

El resultado guarda la clave de la búsqueda que lo produjo: si la clave actual es otra, el estado es "cargando" y nunca se ven resultados de la búsqueda anterior.

```ts
import { useEffect, useState } from 'react'
import { buscarVuelos, type ParamsBusqueda, type Vuelo } from './vuelos.ts'

export type EstadoBusqueda = 'inactivo' | 'cargando' | 'ok' | 'error'

/** Corre buscarVuelos cada vez que cambian los parámetros. `null` = no buscar. */
export function useVuelos(params: ParamsBusqueda | null) {
  const clave = params ? JSON.stringify(params) : ''
  const [intento, setIntento] = useState(0)
  const [resultado, setResultado] = useState({ clave: '', vuelos: [] as Vuelo[], error: false })

  useEffect(() => {
    if (!clave) return
    let vigente = true
    buscarVuelos(JSON.parse(clave) as ParamsBusqueda).then(
      (vuelos) => {
        if (vigente) setResultado({ clave, vuelos, error: false })
      },
      () => {
        if (vigente) setResultado({ clave, vuelos: [], error: true })
      },
    )
    return () => {
      vigente = false
    }
  }, [clave, intento])

  const estado: EstadoBusqueda = !clave
    ? 'inactivo'
    : resultado.clave !== clave
      ? 'cargando'
      : resultado.error
        ? 'error'
        : 'ok'

  return {
    estado,
    vuelos: estado === 'ok' ? resultado.vuelos : [],
    reintentar: () => {
      setResultado((r) => ({ ...r, clave: '' }))
      setIntento((n) => n + 1)
    },
  }
}
```

- [ ] **Step 2: Crear `frontend/src/components/CardVuelo.tsx`**

```tsx
import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { duracion, fechaCorta, hora, precio } from '../lib/formato'
import { asientosDe, duracionDe, precioDe, type Vuelo } from '../lib/vuelos'

interface Props {
  vuelo: Vuelo
  clase: Clase
  onElegir: () => void
}

export default function CardVuelo({ vuelo, clase, onElegir }: Props) {
  const quedan = asientosDe(vuelo, clase)
  return (
    <article className="group flex flex-col rounded-3xl border border-slate-200 bg-white transition hover:-translate-y-0.5 hover:border-cielo hover:shadow-xl hover:shadow-marino/10">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-marino">
          <img src="/titulo.svg" alt="Fly Away" className="h-3" />
          {vuelo.numero_vuelo}
        </span>
        <span className="rounded-full bg-cielo/10 px-2.5 py-0.5 text-xs font-bold text-cielo">Directo</span>
      </div>

      <div className="flex items-center gap-3 px-5 py-5">
        <div>
          <p className="text-2xl font-extrabold">{hora(vuelo.hora_partida)}</p>
          <p className="text-sm font-semibold text-slate-500">{vuelo.origen.codigo_iata}</p>
        </div>
        <div className="flex-1 text-center text-xs text-slate-400">
          {duracion(duracionDe(vuelo))}
          <div className="relative my-1 h-px bg-slate-300">
            <span aria-hidden="true" className="absolute -top-2 left-1/2 -translate-x-1/2 bg-white px-1 text-naranja">
              ✈
            </span>
          </div>
          {fechaCorta(vuelo.fecha_operacion)}
        </div>
        <div className="text-right">
          <p className="text-2xl font-extrabold">{hora(vuelo.hora_llegada)}</p>
          <p className="text-sm font-semibold text-slate-500">{vuelo.destino.codigo_iata}</p>
        </div>
      </div>

      <div className="mt-auto flex items-end justify-between rounded-b-3xl bg-slate-50 px-5 py-4">
        <div>
          <p className="text-xs text-slate-500">Por persona - {NOMBRE_CLASE[clase]}</p>
          <p className="text-2xl font-extrabold text-marino">{precio(precioDe(vuelo, clase))}</p>
          <p className={`text-xs font-semibold ${quedan <= 5 ? 'text-naranja' : 'text-slate-400'}`}>
            {quedan <= 5
              ? `¡Quedan ${quedan} ${quedan === 1 ? 'asiento' : 'asientos'}!`
              : `${quedan} asientos disponibles`}
          </p>
        </div>
        <button
          type="button"
          onClick={onElegir}
          className="rounded-xl bg-marino px-4 py-2 text-sm font-bold text-white group-hover:bg-cielo hover:bg-cielo"
        >
          Elegir
        </button>
      </div>
    </article>
  )
}
```

- [ ] **Step 3: Crear `frontend/src/components/ListaVuelos.tsx`**

```tsx
import { useState } from 'react'
import type { Clase } from '../lib/busqueda'
import type { EstadoBusqueda } from '../lib/useVuelos'
import type { Vuelo } from '../lib/vuelos'
import CardVuelo from './CardVuelo'

interface Props {
  titulo: string
  subtitulo: string
  estado: EstadoBusqueda
  vuelos: Vuelo[]
  clase: Clase
  /** Consejo que acompaña al "no hay resultados". */
  sugerencia: string
  onElegir: (v: Vuelo) => void
  onReintentar: () => void
}

const POR_PAGINA = 12

const grilla = 'grid gap-4 md:grid-cols-2 lg:grid-cols-3'

/** Muestra los vuelos de a 12. Se resetea con una `key` distinta por búsqueda. */
export default function ListaVuelos({ titulo, subtitulo, estado, vuelos, clase, sugerencia, onElegir, onReintentar }: Props) {
  const [visibles, setVisibles] = useState(POR_PAGINA)
  const encontrados =
    estado === 'ok' ? `, ${vuelos.length} ${vuelos.length === 1 ? 'vuelo encontrado' : 'vuelos encontrados'}` : ''
  return (
    <section aria-live="polite">
      <h2 className="mb-1 text-2xl font-extrabold text-marino md:text-3xl">{titulo}</h2>
      <p className="mb-6 text-slate-500">
        {subtitulo}
        {encontrados}
      </p>

      {estado === 'cargando' && (
        <div className={grilla} aria-label="Buscando vuelos">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-56 animate-pulse rounded-3xl bg-slate-200/70" />
          ))}
        </div>
      )}

      {estado === 'error' && (
        <div className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700">
          <p className="font-semibold">No pudimos buscar vuelos. Probá de nuevo.</p>
          <button
            type="button"
            onClick={onReintentar}
            className="mt-3 rounded-xl bg-white px-4 py-2 text-sm font-bold ring-1 ring-red-200 hover:bg-red-100"
          >
            Reintentar
          </button>
        </div>
      )}

      {estado === 'ok' && vuelos.length === 0 && (
        <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          <p className="font-semibold text-slate-700">No encontramos vuelos con esos criterios.</p>
          <p className="mt-1">{sugerencia}</p>
        </div>
      )}

      {estado === 'ok' && vuelos.length > 0 && (
        <>
          <div className={grilla}>
            {vuelos.slice(0, visibles).map((v) => (
              <CardVuelo key={v.id} vuelo={v} clase={clase} onElegir={() => onElegir(v)} />
            ))}
          </div>
          {vuelos.length > visibles && (
            <div className="mt-8 text-center">
              <button
                type="button"
                onClick={() => setVisibles((n) => n + POR_PAGINA)}
                className="rounded-xl border border-slate-300 bg-white px-6 py-3 font-bold text-marino hover:border-cielo"
              >
                Ver más vuelos ({vuelos.length - visibles})
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}
```

- [ ] **Step 4: Crear `frontend/src/components/FiltroPrecio.tsx`**

```tsx
import { useState, type FormEvent } from 'react'
import { NOMBRE_CLASE, validarPrecio, type Clase } from '../lib/busqueda'

interface Props {
  min: number | null
  max: number | null
  clase: Clase
  onAplicar: (min: number | null, max: number | null) => void
}

const aMonto = (texto: string) => (texto.trim() === '' ? null : Number(texto))
const campo =
  'flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 focus-within:border-cielo'

/** Rango de precio por persona. Lee `min`/`max` al montar: el que lo usa le pasa una `key` que cambia con ellos. */
export default function FiltroPrecio({ min, max, clase, onAplicar }: Props) {
  const [desde, setDesde] = useState(min === null ? '' : String(min))
  const [hasta, setHasta] = useState(max === null ? '' : String(max))
  const [error, setError] = useState<string>()

  function aplicar(e: FormEvent) {
    e.preventDefault()
    const nuevoMin = aMonto(desde)
    const nuevoMax = aMonto(hasta)
    const mensaje = validarPrecio(nuevoMin, nuevoMax)
    setError(mensaje)
    if (!mensaje) onAplicar(nuevoMin, nuevoMax)
  }

  return (
    <form
      onSubmit={aplicar}
      noValidate
      className="mb-8 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm"
    >
      <span className="font-semibold text-marino">Precio por persona - {NOMBRE_CLASE[clase]}</span>
      <label className={campo}>
        <span className="text-slate-400">$</span>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          step={1000}
          placeholder="Mínimo"
          aria-label="Precio mínimo"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
          className="w-28 bg-transparent font-semibold outline-none"
        />
      </label>
      <span className="text-slate-400" aria-hidden="true">
        –
      </span>
      <label className={campo}>
        <span className="text-slate-400">$</span>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          step={1000}
          placeholder="Máximo"
          aria-label="Precio máximo"
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
          className="w-28 bg-transparent font-semibold outline-none"
        />
      </label>
      <button type="submit" className="rounded-xl bg-marino px-4 py-2 font-bold text-white hover:bg-cielo">
        Aplicar
      </button>
      {(min !== null || max !== null) && (
        <button
          type="button"
          onClick={() => onAplicar(null, null)}
          className="font-bold text-cielo hover:underline"
        >
          Limpiar
        </button>
      )}
      {error && <p className="w-full text-xs font-medium text-red-600">{error}</p>}
    </form>
  )
}
```

- [ ] **Step 5: Reemplazar `frontend/src/pages/Vuelos.tsx` por la versión completa**

Toda navegación (buscar, filtrar precio, elegir o cambiar la ida) pasa por `irA`, que limpia la vuelta elegida.

```tsx
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import BuscadorVuelos from '../components/BuscadorVuelos'
import FiltroPrecio from '../components/FiltroPrecio'
import HeroCarrusel from '../components/HeroCarrusel'
import ListaVuelos from '../components/ListaVuelos'
import { NOMBRE_CLASE, aParams, hoyISO, leerFiltros, validarBusqueda, type Clase, type Filtros } from '../lib/busqueda'
import { fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../lib/formato'
import { useVuelos } from '../lib/useVuelos'
import { getAeropuertos, precioDe, vueltasPosibles, type Aeropuerto, type Vuelo } from '../lib/vuelos'

function Pasos({ actual, total }: { actual: 1 | 2; total: 1 | 2 }) {
  const paso = (n: 1 | 2, texto: string) => (
    <li className={`flex items-center gap-2 ${n <= actual ? 'text-marino' : 'text-slate-400'}`}>
      <span
        className={`grid h-6 w-6 place-items-center rounded-full text-xs ${
          n <= actual ? 'bg-marino text-white' : 'bg-slate-200'
        }`}
      >
        {n}
      </span>
      {texto}
    </li>
  )
  return (
    <ol className="mb-6 flex items-center gap-3 text-sm font-semibold">
      {paso(1, 'Vuelo de ida')}
      {total === 2 && <li className="h-px w-10 bg-slate-300" aria-hidden="true" />}
      {total === 2 && paso(2, 'Vuelo de vuelta')}
    </ol>
  )
}

function LineaVuelo({ etiqueta, vuelo, clase }: { etiqueta: string; vuelo: Vuelo; clase: Clase }) {
  return (
    <p className="text-slate-700">
      <span className="font-bold text-marino">{etiqueta}</span> - {vuelo.numero_vuelo},{' '}
      {fechaCorta(vuelo.fecha_operacion)}, {hora(vuelo.hora_partida)} → {hora(vuelo.hora_llegada)},{' '}
      {vuelo.origen.codigo_iata} → {vuelo.destino.codigo_iata}, {precio(precioDe(vuelo, clase))} por persona
    </p>
  )
}

export default function Vuelos() {
  const [params, setParams] = useSearchParams()
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  // Vuelta elegida, atada a la búsqueda (e ida) en la que se eligió. Se limpia al cambiar de búsqueda o de ida.
  const [vuelta, setVuelta] = useState<{ busqueda: string; vuelo: Vuelo } | null>(null)

  useEffect(() => {
    getAeropuertos().then(setAeropuertos)
  }, [])

  const filtros = leerFiltros(params)
  // Solo se busca con filtros válidos: la URL puede venir editada o ser de otro día.
  const f = filtros && Object.keys(validarBusqueda(filtros, hoyISO())).length === 0 ? filtros : null
  // Cambia con cada búsqueda (sin idaId): remonta el buscador con los valores de la URL.
  const claveFiltros = filtros ? aParams(filtros).toString() : ''

  const busquedaIda = useVuelos(
    f && {
      origen: f.origen,
      destino: f.destino,
      desde: f.ida,
      hasta: f.hasta,
      pasajeros: f.pasajeros,
      clase: f.clase,
      precioMin: f.precioMin,
      precioMax: f.precioMax,
    },
  )
  // Si el idaId de la URL no está en los resultados (URL vieja o editada), se vuelve al paso 1.
  const idaElegida = busquedaIda.vuelos.find((v) => v.id === params.get('idaId')) ?? null
  const busquedaVuelta = useVuelos(
    f?.vuelta && idaElegida
      ? {
          origen: f.destino,
          destino: f.origen,
          desde: f.vuelta,
          hasta: '',
          pasajeros: f.pasajeros,
          clase: f.clase,
          precioMin: f.precioMin,
          precioMax: f.precioMax,
        }
      : null,
  )
  const vueltaElegida = vuelta?.busqueda === params.toString() ? vuelta.vuelo : null

  const ciudad = (iata: string) => aeropuertos.find((a) => a.codigo_iata === iata)?.ciudad ?? iata

  function irA(p: URLSearchParams) {
    setVuelta(null)
    setParams(p)
  }
  function buscar(nuevos: Filtros) {
    irA(aParams(nuevos))
  }
  function filtrarPrecio(min: number | null, max: number | null) {
    if (filtros) irA(aParams({ ...filtros, precioMin: min, precioMax: max }))
  }
  function elegirIda(v: Vuelo) {
    const p = new URLSearchParams(params)
    p.set('idaId', v.id)
    irA(p)
  }
  function cambiarIda() {
    const p = new URLSearchParams(params)
    p.delete('idaId')
    irA(p)
  }

  let contenido = null
  if (filtros && !f) {
    contenido = <p className="text-slate-500">Revisá los datos de la búsqueda y volvé a buscar.</p>
  } else if (f) {
    const total = f.vuelta === null ? 1 : 2
    const detalle = `${f.pasajeros} ${f.pasajeros === 1 ? 'pasajero' : 'pasajeros'}, ${NOMBRE_CLASE[f.clase]}`
    const sugerencia =
      f.precioMin !== null || f.precioMax !== null
        ? 'Probá ampliar el rango de precio.'
        : f.vuelta === null && !f.hasta
          ? 'Probá con un rango de fechas.'
          : 'Probá con otras fechas.'
    const tituloIda =
      f.origen && f.destino
        ? `${ciudad(f.origen)} → ${ciudad(f.destino)}`
        : f.origen
          ? `Desde ${ciudad(f.origen)}`
          : `Hacia ${ciudad(f.destino)}`

    if (!idaElegida) {
      contenido = (
        <>
          <Pasos actual={1} total={total} />
          <ListaVuelos
            key={claveFiltros}
            titulo={tituloIda}
            subtitulo={`${f.hasta ? rangoFechas(f.ida, f.hasta) : fechaLarga(f.ida)} - ${detalle}`}
            estado={busquedaIda.estado}
            vuelos={busquedaIda.vuelos}
            clase={f.clase}
            sugerencia={sugerencia}
            onElegir={elegirIda}
            onReintentar={busquedaIda.reintentar}
          />
        </>
      )
    } else if (f.vuelta !== null && !vueltaElegida) {
      contenido = (
        <>
          <Pasos actual={2} total={2} />
          <div className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4">
            <LineaVuelo etiqueta="Ida elegida" vuelo={idaElegida} clase={f.clase} />
            <button type="button" onClick={cambiarIda} className="text-sm font-bold text-cielo hover:underline">
              Cambiar
            </button>
          </div>
          <ListaVuelos
            key={`${claveFiltros}-${idaElegida.id}`}
            titulo={`${ciudad(f.destino)} → ${ciudad(f.origen)}`}
            subtitulo={`${fechaLarga(f.vuelta)} - ${detalle}`}
            estado={busquedaVuelta.estado}
            vuelos={vueltasPosibles(busquedaVuelta.vuelos, idaElegida)}
            clase={f.clase}
            sugerencia={sugerencia}
            onElegir={(v) => setVuelta({ busqueda: params.toString(), vuelo: v })}
            onReintentar={busquedaVuelta.reintentar}
          />
        </>
      )
    } else {
      const elegidos = vueltaElegida ? [idaElegida, vueltaElegida] : [idaElegida]
      const totalPrecio = elegidos.reduce((suma, v) => suma + precioDe(v, f.clase), 0) * f.pasajeros
      contenido = (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8">
          <h2 className="mb-4 text-2xl font-extrabold text-marino">Tu viaje</h2>
          <div className="space-y-2">
            <LineaVuelo etiqueta="Ida" vuelo={idaElegida} clase={f.clase} />
            {vueltaElegida && <LineaVuelo etiqueta="Vuelta" vuelo={vueltaElegida} clase={f.clase} />}
          </div>
          <div className="mt-6 flex flex-wrap items-end justify-between gap-4 border-t border-slate-100 pt-6">
            <div>
              <p className="text-sm text-slate-500">Total - {detalle}</p>
              <p className="text-3xl font-extrabold text-marino">{precio(totalPrecio)}</p>
            </div>
            <div className="text-right">
              <button
                type="button"
                disabled
                className="cursor-not-allowed rounded-xl bg-slate-300 px-6 py-3 font-bold text-white"
              >
                Continuar
              </button>
              <p className="mt-1 text-xs text-slate-500">La compra llega pronto</p>
            </div>
          </div>
          <button type="button" onClick={cambiarIda} className="mt-4 text-sm font-bold text-cielo hover:underline">
            Cambiar vuelos
          </button>
        </section>
      )
    }

  }

  return (
    <>
      <HeroCarrusel />
      <section className="relative z-10 mx-auto -mt-20 max-w-[88rem] px-4">
        <BuscadorVuelos key={claveFiltros} aeropuertos={aeropuertos} inicial={filtros} onBuscar={buscar} />
      </section>
      <main className="mx-auto max-w-[88rem] px-4 py-10">
        {/* Visible aunque la URL sea inválida: así se puede corregir un rango de precio mal cargado. */}
        {filtros && (
          <FiltroPrecio
            key={`${filtros.precioMin}-${filtros.precioMax}`}
            min={filtros.precioMin}
            max={filtros.precioMax}
            clase={filtros.clase}
            onAplicar={filtrarPrecio}
          />
        )}
        {contenido}
      </main>
    </>
  )
}
```

- [ ] **Step 6: Verificar build, lint y chequeos**

Run: `npm run build`, `npm run lint`, `npm run check`
Expected: sin errores.

- [ ] **Step 7: Verificación manual**

Run: `npm run dev`
Expected:
- Ida y vuelta BHI → AEP: 3 skeletons y después las cards de ida, con "Bahía Blanca → Buenos Aires" y la fecha larga correcta (el mismo día elegido).
- Elegir una ida: la URL suma `idaId`; se ve "Ida elegida" con "Cambiar" y las cards de vuelta "Buenos Aires → Bahía Blanca". Elegir una vuelta: "Tu viaje" con total = (ida + vuelta) × pasajeros y "Continuar" deshabilitado.
- "Cambiar vuelos" y volver a elegir **la misma ida**: aparece el paso 2 (no el resumen con la vuelta anterior).
- Atrás del navegador: vuelve al paso anterior. Recargar en el paso 2: sigue en el paso 2.
- Ida y vuelta el mismo día: ninguna vuelta sale antes de la llegada de la ida.
- Solo ida con origen BHI, sin destino, rango de 7 días: "Desde Bahía Blanca", "Del … al …", varias rutas y días; 12 cards y "Ver más vuelos (N)".
- Solo destino USH: "Hacia Ushuaia", todas las cards llegan a USH.
- Precio 120000–160000 → Aplicar: la URL suma `precioMin`/`precioMax` y todas las cards están en el rango. Mínimo > máximo: error y no cambia la URL. "Limpiar" quita el rango.
- Sin resultados: "No encontramos vuelos con esos criterios." + la sugerencia que corresponde (precio / rango de fechas / otras fechas).
- 9 pasajeros en Primera: ninguna card con menos asientos que pasajeros.
- Error: poner temporalmente `throw new Error('x')` al principio de `buscarVuelos`, comprobar el mensaje y "Reintentar", y **deshacer el cambio**.
- 360px: cards en una columna, fila de precio acomodada, sin scroll horizontal.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): resultados con filtro de precio y pasos de ida y vuelta"
```

---

### Task 6: Documentación

**Files:**
- Modify: `docs/memoria.md`
- Modify: `docs/arquitectura.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: `docs/memoria.md`**

En **Estado actual**, agregar arriba de todo:

```markdown
**2026-10-02 — Interfaz de inicio (rama `feat/interfaz-inicio`)**
- Pantalla `/` del pasajero: header con sesión, hero con carrusel de destinos, buscador y resultados.
- Búsqueda según los criterios de la US: en **Solo ida** origen y/o destino y fecha o rango (≤ 14 días); en **Ida y vuelta**, flujo en dos pasos (ida → vuelta). Filtro de rango de precio sobre los resultados.
- **Todo mockeado** en `frontend/src/lib/vuelos.ts` y `lib/auth.ts`, con la forma de la API. Conectar el back = reemplazar el cuerpo de `getAeropuertos`, `buscarVuelos` y `usuarioActual` por `api(...)`.
- Páginas `/reservas`, `/perfil`, `/login`, `/registro` vacías ("Próximamente"); `/login` tiene "Entrar (demo)".
- Chequeos de lógica pura: `npm run check` (Node + assert, sin framework).
```

En la tabla de **Decisiones**, agregar arriba:

```markdown
| 2026-10-02 | Front de búsqueda con datos mock que respetan el contrato del back | Avanzar la UI sin bloquearse con el modelo; cambiar a la API toca solo `src/lib/` |
| 2026-10-02 | Avatar con iniciales (sin foto) | `usuarios` no tiene campo de foto; evita subir archivos |
| 2026-10-02 | Ida y vuelta = dos pasos (elegir ida, después vuelta) | Cada fila de `vuelos` es un tramo; coincide con el endpoint de búsqueda |
| 2026-10-02 | Estado de búsqueda en la query string | Funcionan "atrás" y recargar |
| 2026-10-02 | "Solo ida" funciona como explorador (origen/destino opcionales, rango de fechas); "Ida y vuelta" pide ruta y fechas exactas | Cumple los criterios de la US sin perder el flujo de ida y vuelta; una vuelta sin los dos extremos no tiene sentido |
| 2026-10-02 | El rango de precio y "ya salió" los filtra el backend (`precio_min`, `precio_max` en `/vuelos/buscar/`) | El front no filtra resultados por su cuenta: el mock aplica la misma regla que el endpoint |
| 2026-10-02 | `modelo.dbml` actualizado: `reservas.vendido_por`, `contacto_email`, `contacto_nombre`, `pasajero_id` opcional, índice único (`numero_vuelo`, `fecha_operacion`), CHECKs | Resuelve la venta en mostrador a alguien sin cuenta |
```

En **Pendientes**, borrar "Venta en mostrador a alguien sin cuenta" y "Sugerencias al modelo" (quedaron resueltos por el DBML nuevo) y agregar:

```markdown
- [ ] **Ida y vuelta en la compra:** el front ya permite elegir ida + vuelta; al implementar la compra definir si son 2 reservas con un pago cada una o un pago para ambas (`pagos.reserva_id` hoy apunta a una sola).
```

- [ ] **Step 2: `docs/arquitectura.md`: API y estructura**

En **API (propuesta)**, reemplazar las líneas de registro, aeropuertos y búsqueda por:

```
POST /api/auth/registro/         alta de pasajero
GET  /api/auth/yo/               usuario logueado {id, email, nombre, apellido, rol} (header del front)
GET  /api/aeropuertos/
GET  /api/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=
                                 origen y/o destino (al menos uno), hasta opcional (rango ≤ 14 días);
                                 devuelve vuelos activos, con asientos_disponibles_<clase> >= pasajeros,
                                 precio_<clase> dentro del rango, que todavía no salieron, por fecha y hora;
                                 origen/destino anidados (codigo_iata, ciudad…)
```

Y en la estructura de carpetas del frontend, reemplazar el bloque `src/` por:

```
    └── src/
        ├── lib/              api.ts (fetch + JWT), mocks con la forma de la API, lógica pura
        ├── components/       Header, HeroCarrusel, BuscadorVuelos, CardVuelo, ListaVuelos
        ├── pages/            pantallas
        └── App.tsx           rutas: / (pasajero), /mostrador, /admin
```

- [ ] **Step 3: `CLAUDE.md`: comando de chequeos**

En el bloque de comandos del frontend, agregar después de `npm run lint`:

```bash
npm run check    # chequeos de la lógica pura (scripts/check.ts)
```

- [ ] **Step 4: Verificación final**

Run (desde `frontend/`): `npm run check`, `npm run build`, `npm run lint`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add docs CLAUDE.md
git commit -m "docs: memoria y arquitectura de la interfaz de inicio"
```
