# US05 — Detalle de vuelo — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Desde cada card de resultados, "Ver detalle" abre un diálogo con origen, destino, horarios, fecha, clases, precio por clase, disponibilidad y avión, y permite elegir el vuelo desde ahí.

**Architecture:** El mock (`src/lib/vuelos.ts`) suma `getVuelo(id)` (futuro `GET /vuelos/<id>/`), el avión y números de vuelo únicos por ruta. Un componente `DetalleVuelo` usa el `<dialog>` nativo y pide los datos frescos al abrirse. `ListaVuelos` maneja qué vuelo está abierto; la página `Vuelos` solo le pasa la cantidad de pasajeros.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS v4, Node 22.14 (`--experimental-strip-types` para `npm run check`).

**Spec:** [docs/superpowers/specs/2026-10-02-detalle-vuelo-design.md](../specs/2026-10-02-detalle-vuelo-design.md)

## Global Constraints

- Textos de UI y commits en **español** (voseo rioplatense). Commits **sin** `Co-Authored-By` ni firmas.
- Campos con los nombres de `docs/modelo.dbml` (`avion.modelo`, `avion.matricula`, `asientos_disponibles_*`, `precio_*`).
- **Sin dependencias nuevas.** Diálogo con `<dialog>` nativo.
- Imports entre archivos de `src/lib/` con extensión `.ts` explícita (los corre `scripts/check.ts`).
- Umbral de "últimos asientos": **5** (1 a 5). 0 = agotada.
- Logo del diálogo: `public/logoA.svg`, 32px de alto (`h-8`).
- Ningún componente hace `fetch` directo: los datos salen de funciones de `src/lib/` que después se reemplazan por `api(...)`.

## Review Focus

1. **`StrictMode` monta dos veces el diálogo en desarrollo:** `showModal()` sobre un `<dialog>` ya abierto no puede romper la página. Esperado: abre una sola vez, sin errores en consola. → guarda `if (!d.open)` en Task 2 y verificación en consola.
2. **Los datos cambiaron desde la búsqueda** (vuelo cancelado o sin lugar para todos en la clase buscada): "Elegir este vuelo" deshabilitado y con el motivo. → verificación forzando el caso en Task 2.
3. **`getVuelo` falla o el id no existe:** mensaje con "Reintentar", sin botón de elegir activo. → chequeos de rechazo en Task 1 y verificación forzando el error en Task 2.
4. **Pantalla de 360px:** la tabla de clases y el pie de la card (precio + dos botones) entran sin scroll horizontal. → verificación en Task 2.
5. **Elegir desde el diálogo en el paso de vuelta:** tiene que seguir el flujo igual que el botón de la card (resumen "Tu viaje" con la vuelta elegida). → verificación en Task 2.

---

## Mapa de archivos

| Archivo | Cambio |
|---|---|
| `frontend/src/lib/vuelos.ts` | `Avion`, `VueloDetalle`, `EstadoClase`, `UMBRAL_ULTIMOS`, flota mock, números de vuelo por ruta, `getVuelo`, `estadoClase`. |
| `frontend/src/lib/formato.ts` | `fechaCompleta`. |
| `frontend/scripts/check.ts` | Chequeos de lo anterior. |
| `frontend/src/components/DetalleVuelo.tsx` (nuevo) | Diálogo de detalle. |
| `frontend/src/components/CardVuelo.tsx` | Botones "Ver detalle" + "Elegir"; aviso de asientos con `estadoClase`. |
| `frontend/src/components/ListaVuelos.tsx` | Abre/cierra el diálogo; recibe `pasajeros`. |
| `frontend/src/pages/Vuelos.tsx` | Pasa `pasajeros` a las dos `ListaVuelos`. |
| `docs/arquitectura.md`, `docs/memoria.md` | Endpoint y decisiones. |

---

### Task 1: Mock del detalle (números únicos, avión, `getVuelo`)

**Files:**
- Modify: `frontend/src/lib/vuelos.ts`
- Modify: `frontend/src/lib/formato.ts`
- Modify: `frontend/scripts/check.ts`

**Interfaces:**
- Produces:
  - `interface Avion { matricula: string; modelo: string }`
  - `interface VueloDetalle extends Vuelo { avion: Avion }`
  - `type EstadoClase = 'disponible' | 'ultimos' | 'agotada'`, `UMBRAL_ULTIMOS = 5`
  - `getVuelo(id: string): Promise<VueloDetalle>` (rechaza con `Error('Vuelo no encontrado')`)
  - `estadoClase(asientos: number): EstadoClase`
  - `generarVuelos(...)` ahora devuelve `VueloDetalle[]` (y `buscarVuelos` sigue tipado como `Vuelo[]`)
  - `fechaCompleta(iso: string): string` → "Martes, 20 de octubre de 2026"

- [ ] **Step 1: Escribir los chequeos (fallan)**

En `frontend/scripts/check.ts`, reemplazar los imports de formato y vuelos por:

```ts
import { duracion, fechaCompleta, fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../src/lib/formato.ts'
import {
  asientosDe,
  buscarVuelos,
  duracionDe,
  estadoClase,
  generarVuelos,
  getAeropuertos,
  getVuelo,
  precioDe,
  vueltasPosibles,
  type ParamsBusqueda,
  type Vuelo,
} from '../src/lib/vuelos.ts'
```

Debajo de `assert.equal(rangoFechas('2026-10-20', '2026-10-25'), 'Del 20 de octubre al 25 de octubre')` agregar:

```ts
assert.equal(fechaCompleta('2026-10-20'), 'Martes, 20 de octubre de 2026')
```

Y antes del `console.log('vuelos: OK')` final agregar:

```ts
// números de vuelo únicos por fecha (índice único numero_vuelo + fecha_operacion del modelo)
for (const fecha of ['2026-10-20', '2026-11-14', '2026-12-24']) {
  const delDia = aeropuertos.flatMap((o) => aeropuertos.flatMap((d) => generarVuelos(o.codigo_iata, d.codigo_iata, fecha)))
  assert.ok(delDia.length > 50, 'hay muchos vuelos ese día')
  assert.equal(new Set(delDia.map((v) => v.numero_vuelo)).size, delDia.length, `números únicos el ${fecha}`)
}

// getVuelo: el mismo vuelo que la búsqueda, con el avión
const encontrados = (await buscarVuelos(p({ destino: '', hasta: '2026-10-22' }), ahora)).slice(0, 5)
assert.ok(encontrados.length === 5)
for (const v of encontrados) {
  const detalle = await getVuelo(v.id)
  assert.deepEqual(detalle, v, `getVuelo(${v.id}) = vuelo de la búsqueda`)
  assert.ok(detalle.avion.modelo && detalle.avion.matricula.startsWith('LV-'), 'trae el avión')
}

// getVuelo: ids que no existen
const rechaza = (id: string) => assert.rejects(getVuelo(id), /Vuelo no encontrado/, `rechaza ${id}`)
await rechaza('cualquiera')
await rechaza('FA999-2026-10-20') // antes del primer número
await rechaza('FA9999-2026-10-20') // después del último bloque de rutas
const conVuelos = dias.find((d) => generarVuelos('BHI', 'AEP', d).length > 0)!
const primero = Number(generarVuelos('BHI', 'AEP', conVuelos)[0].numero_vuelo.slice(3))
const incompleto = dias.find((d) => generarVuelos('BHI', 'AEP', d).length < 4)!
await rechaza(`FA${primero + generarVuelos('BHI', 'AEP', incompleto).length}-${incompleto}`) // número de la ruta que ese día no existe

// getVuelo: un cancelado se devuelve (el detalle informa la cancelación)
const cancelado = generados.find((v) => v.estado === 'cancelado')!
assert.equal((await getVuelo(cancelado.id)).estado, 'cancelado')

// estadoClase
assert.equal(estadoClase(0), 'agotada')
assert.equal(estadoClase(1), 'ultimos')
assert.equal(estadoClase(5), 'ultimos')
assert.equal(estadoClase(6), 'disponible')
```

- [ ] **Step 2: Correr y verificar que falla**

Run (desde `frontend/`): `npm run check`
Expected: FAIL con `SyntaxError: The requested module '../src/lib/formato.ts' does not provide an export named 'fechaCompleta'`.

- [ ] **Step 3: `fechaCompleta` en `frontend/src/lib/formato.ts`**

Debajo de `fechaCorta`:

```ts
/** "Martes, 20 de octubre de 2026" */
export function fechaCompleta(iso: string): string {
  return mayuscula(
    aFecha(iso).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
  )
}
```

- [ ] **Step 4: Tipos nuevos en `frontend/src/lib/vuelos.ts`**

Debajo de `interface ParamsBusqueda { … }`:

```ts
export interface Avion {
  matricula: string
  modelo: string
}

/** Respuesta de GET /vuelos/<id>/: el vuelo de la búsqueda más el avión. */
export interface VueloDetalle extends Vuelo {
  avion: Avion
}

export type EstadoClase = 'disponible' | 'ultimos' | 'agotada'

/** Con esta cantidad de asientos o menos, la clase está en "últimos asientos". */
export const UMBRAL_ULTIMOS = 5
```

Y actualizar el comentario del mock:

```ts
// ponytail: todo lo de abajo es mock. Al conectar el backend:
//   getAeropuertos → api('/aeropuertos/')
//   buscarVuelos   → api(`/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=`)
//   getVuelo       → api(`/vuelos/${id}/`)
```

- [ ] **Step 5: Flota y números de vuelo por ruta**

Debajo de la lista `AEROPUERTOS`:

```ts
const FLOTA: Avion[] = [
  { matricula: 'LV-FAA', modelo: 'Airbus A320' },
  { matricula: 'LV-FAB', modelo: 'Boeing 737-800' },
  { matricula: 'LV-FAC', modelo: 'Embraer E190' },
  { matricula: 'LV-FAD', modelo: 'Airbus A330-200' },
]

// Cada ruta (par ordenado de aeropuertos) tiene su bloque de números: FA 1000 + índice × 10 + n.
// Así no se repite (numero_vuelo, fecha_operacion), como exige el modelo, y el número dice de qué ruta es.
const PRIMER_NUMERO = 1000
const NUMEROS_POR_RUTA = 10
const indiceRuta = (o: Aeropuerto, d: Aeropuerto) => AEROPUERTOS.indexOf(o) * AEROPUERTOS.length + AEROPUERTOS.indexOf(d)
```

- [ ] **Step 6: `generarVuelos` con número por ruta y avión**

Reemplazar la firma, el cálculo del número y agregar el avión:

```ts
/** Vuelos de una ruta y fecha, sin filtrar. Determinístico. Exportado para los chequeos. */
export function generarVuelos(origen: string, destino: string, fecha: string): VueloDetalle[] {
  const o = AEROPUERTOS.find((a) => a.codigo_iata === origen)
  const d = AEROPUERTOS.find((a) => a.codigo_iata === destino)
  if (!o || !d || o.ciudad === d.ciudad) return []
  const ruta = semilla(`${origen}-${destino}`)
  const r = azar(semilla(`${origen}-${destino}-${fecha}`))
  const duracionMin = 60 + (ruta % 30) * 5 // 1 h a 3 h 25 m, fija por ruta
  const avion = FLOTA[ruta % FLOTA.length]
  const cantidad = Math.floor(r() * 5) // 0 a 4 vuelos ese día
  return Array.from({ length: cantidad }, (_, i): VueloDetalle => {
    const partida = (6 + i * 4) * 60 + Math.floor(r() * 8) * 15 // de 06:00 a 19:45: siempre llega antes de medianoche
    const economy = Math.round((40000 + duracionMin * 900 + r() * 40000) / 10) * 10
    const numero = `FA ${PRIMER_NUMERO + indiceRuta(o, d) * NUMEROS_POR_RUTA + i}`
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
      avion,
    }
  })
}
```

(El orden de las llamadas a `r()` no cambia: horarios, precios, asientos y cancelaciones siguen saliendo iguales que antes.)

- [ ] **Step 7: `getVuelo` y `estadoClase`**

Al final de `vuelos.ts`:

```ts
const ID_VUELO = /^FA(\d+)-(\d{4}-\d{2}-\d{2})$/

/** Detalle de un vuelo. El mock reconstruye la ruta desde el número y regenera el vuelo. */
export async function getVuelo(id: string): Promise<VueloDetalle> {
  await esperar(300)
  const m = ID_VUELO.exec(id)
  if (m) {
    const n = Number(m[1]) - PRIMER_NUMERO
    const indice = Math.floor(n / NUMEROS_POR_RUTA)
    const o = AEROPUERTOS[Math.floor(indice / AEROPUERTOS.length)]
    const d = AEROPUERTOS[indice % AEROPUERTOS.length]
    const vuelo = n >= 0 && o && d ? generarVuelos(o.codigo_iata, d.codigo_iata, m[2]).find((v) => v.id === id) : undefined
    if (vuelo) return vuelo
  }
  throw new Error('Vuelo no encontrado')
}

/** Estado de una clase según sus asientos libres. */
export function estadoClase(asientos: number): EstadoClase {
  if (asientos <= 0) return 'agotada'
  return asientos <= UMBRAL_ULTIMOS ? 'ultimos' : 'disponible'
}
```

- [ ] **Step 8: Correr y verificar que pasa**

Run: `npm run check`
Expected: `busqueda + formato: OK` y `vuelos: OK`.

- [ ] **Step 9: Verificar tipos y lint**

Run: `npm run build` y `npm run lint`
Expected: sin errores (sigue la advertencia conocida de `sesion.tsx`).

- [ ] **Step 10: Commit**

```bash
git add frontend/scripts/check.ts frontend/src/lib/vuelos.ts frontend/src/lib/formato.ts
git commit -m "feat(frontend): detalle de vuelo en el mock (getVuelo, avión y números únicos por ruta)"
```

---

### Task 2: Diálogo de detalle y botones de la card

**Files:**
- Create: `frontend/src/components/DetalleVuelo.tsx`
- Modify: `frontend/src/components/CardVuelo.tsx`
- Modify: `frontend/src/components/ListaVuelos.tsx`
- Modify: `frontend/src/pages/Vuelos.tsx`

**Interfaces:**
- Consumes: `getVuelo`, `estadoClase`, `UMBRAL_ULTIMOS`, `VueloDetalle`, `EstadoClase`, `asientosDe`, `precioDe`, `duracionDe` (Task 1); `fechaCompleta`, `hora`, `precio`, `duracion` (formato); `NOMBRE_CLASE`, `Clase` (busqueda).
- Produces:
  - `DetalleVuelo({ vuelo: Vuelo; clase: Clase; pasajeros: number; onElegir: (v: Vuelo) => void; onCerrar: () => void })`
  - `CardVuelo({ vuelo; clase; onElegir: () => void; onVerDetalle: () => void })`
  - `ListaVuelos` suma la prop `pasajeros: number`.

- [ ] **Step 1: Crear `frontend/src/components/DetalleVuelo.tsx`**

```tsx
import { useEffect, useRef, useState } from 'react'
import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { duracion, fechaCompleta, hora, precio } from '../lib/formato'
import {
  asientosDe,
  duracionDe,
  estadoClase,
  getVuelo,
  precioDe,
  type Aeropuerto,
  type EstadoClase,
  type Vuelo,
  type VueloDetalle,
} from '../lib/vuelos'

interface Props {
  /** El vuelo de la card: se muestra mientras llega el detalle. */
  vuelo: Vuelo
  clase: Clase
  pasajeros: number
  onElegir: (v: Vuelo) => void
  onCerrar: () => void
}

const CLASES: Clase[] = ['economy', 'primera']

const BADGE: Record<EstadoClase, [texto: string, colores: string]> = {
  disponible: ['Disponible', 'bg-emerald-50 text-emerald-700'],
  ultimos: ['Últimos asientos', 'bg-orange-50 text-naranja'],
  agotada: ['Agotada', 'bg-slate-100 text-slate-500'],
}

function Extremo({ etiqueta, horario, aeropuerto, derecha }: { etiqueta: string; horario: string; aeropuerto: Aeropuerto; derecha?: boolean }) {
  return (
    <div className={derecha ? 'sm:text-right' : ''}>
      <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{etiqueta}</p>
      <p className="text-4xl font-extrabold">{hora(horario)}</p>
      <p className="font-bold text-marino">
        {aeropuerto.codigo_iata} - {aeropuerto.ciudad}
      </p>
      <p className="text-sm text-slate-500">{aeropuerto.nombre}</p>
    </div>
  )
}

/** Diálogo modal con el detalle de un vuelo. Se abre al montarse; al cerrarse avisa con `onCerrar`. */
export default function DetalleVuelo({ vuelo, clase, pasajeros, onElegir, onCerrar }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const [intento, setIntento] = useState(0)
  const [resultado, setResultado] = useState<{ detalle: VueloDetalle | null; error: boolean }>({
    detalle: null,
    error: false,
  })

  useEffect(() => {
    // StrictMode monta dos veces en desarrollo: no volver a abrir un diálogo abierto.
    const d = dialogo.current
    if (d && !d.open) d.showModal()
  }, [])

  useEffect(() => {
    let vigente = true
    getVuelo(vuelo.id).then(
      (detalle) => {
        if (vigente) setResultado({ detalle, error: false })
      },
      () => {
        if (vigente) setResultado({ detalle: null, error: true })
      },
    )
    return () => {
      vigente = false
    }
  }, [vuelo.id, intento])

  const { detalle, error } = resultado
  const v = detalle ?? vuelo
  const titulo = `titulo-${vuelo.id}`
  const idMotivo = `motivo-${vuelo.id}`
  const motivo = !detalle
    ? null
    : detalle.estado === 'cancelado'
      ? 'Este vuelo fue cancelado'
      : asientosDe(detalle, clase) < pasajeros
        ? `No hay lugar para ${pasajeros} ${pasajeros === 1 ? 'pasajero' : 'pasajeros'} en ${NOMBRE_CLASE[clase]}`
        : null
  const puedeElegir = detalle !== null && motivo === null

  const cerrar = () => dialogo.current?.close()
  function elegir() {
    if (!detalle) return
    cerrar()
    onElegir(detalle)
  }
  function reintentar() {
    setResultado({ detalle: null, error: false })
    setIntento((n) => n + 1)
  }

  return (
    <dialog
      ref={dialogo}
      onClose={onCerrar}
      aria-labelledby={titulo}
      className="m-auto max-h-[90vh] w-[min(44rem,calc(100%-2rem))] overflow-y-auto rounded-3xl p-0 text-slate-900 shadow-2xl backdrop:bg-marino/45 backdrop:backdrop-blur-sm"
    >
      <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
        <div className="flex items-center gap-3">
          <img src="/logoA.svg" alt="" className="h-8" />
          <h2 id={titulo} className="text-lg font-extrabold text-marino">
            <span className="sr-only">Vuelo </span>
            {v.numero_vuelo}
          </h2>
          <span className="rounded-full bg-cielo/10 px-2.5 py-0.5 text-xs font-bold text-cielo">Directo</span>
        </div>
        <button
          type="button"
          onClick={cerrar}
          aria-label="Cerrar"
          className="grid h-9 w-9 place-items-center rounded-full text-xl text-slate-500 hover:bg-slate-100"
        >
          ✕
        </button>
      </div>

      <div className="px-6 py-6">
        <p className="mb-5 text-sm font-semibold text-slate-500">{fechaCompleta(v.fecha_operacion)}</p>
        <div className="grid items-center gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <Extremo etiqueta="Origen" horario={v.hora_partida} aeropuerto={v.origen} />
          <div className="text-center text-xs text-slate-400">
            {duracion(duracionDe(v))}
            <div className="relative mx-auto my-1 h-px w-28 bg-slate-300 sm:w-32">
              <span aria-hidden="true" className="absolute -top-2 left-1/2 -translate-x-1/2 bg-white px-1 text-naranja">
                ✈
              </span>
            </div>
            Directo
          </div>
          <Extremo etiqueta="Destino" horario={v.hora_llegada} aeropuerto={v.destino} derecha />
        </div>
        <p className="mt-5 text-sm text-slate-500">
          Avión:{' '}
          {detalle ? (
            <span className="font-semibold text-slate-700">{detalle.avion.modelo}</span>
          ) : (
            <span className="inline-block h-4 w-32 animate-pulse rounded bg-slate-200 align-middle" />
          )}
        </p>
      </div>

      <div className="px-6 pb-6">
        <h3 className="mb-3 text-sm font-bold tracking-wider text-slate-400 uppercase">Clases</h3>
        {error ? (
          <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <p className="font-semibold">No pudimos cargar el detalle. Probá de nuevo.</p>
            <button
              type="button"
              onClick={reintentar}
              className="mt-3 rounded-xl bg-white px-4 py-2 font-bold ring-1 ring-red-200 hover:bg-red-100"
            >
              Reintentar
            </button>
          </div>
        ) : !detalle ? (
          <div role="status" aria-label="Cargando detalle" className="space-y-2">
            {[0, 1].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-xl bg-slate-200/70" />
            ))}
          </div>
        ) : (
          <table className="w-full border-separate border-spacing-y-1 text-left text-sm">
            <caption className="sr-only">Clases, precios y disponibilidad</caption>
            <thead className="text-xs text-slate-400">
              <tr>
                <th scope="col" className="px-2 pb-1 font-semibold sm:px-3">
                  Clase
                </th>
                <th scope="col" className="px-2 pb-1 font-semibold sm:px-3">
                  Precio x persona
                </th>
                <th scope="col" className="px-2 pb-1 font-semibold sm:px-3">
                  Asientos
                </th>
                <th scope="col" className="px-2 pb-1 text-right font-semibold sm:px-3">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody>
              {CLASES.map((c) => {
                const asientos = asientosDe(detalle, c)
                const [texto, colores] = BADGE[estadoClase(asientos)]
                const celda = `px-2 py-3 sm:px-3 ${c === clase ? 'bg-cielo/5' : ''}`
                return (
                  <tr key={c}>
                    <th scope="row" className={`${celda} rounded-l-xl font-bold text-marino`}>
                      {NOMBRE_CLASE[c]}
                      {c === clase && <span className="block text-xs font-semibold text-cielo">(tu búsqueda)</span>}
                    </th>
                    <td className={`${celda} text-base font-extrabold text-marino sm:text-lg`}>
                      {precio(precioDe(detalle, c))}
                    </td>
                    <td className={`${celda} font-semibold`}>{asientos}</td>
                    <td className={`${celda} rounded-r-xl text-right`}>
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold whitespace-nowrap sm:text-xs ${colores}`}>
                        {texto}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 rounded-b-3xl bg-slate-50 px-6 py-4">
        {motivo && (
          <p id={idMotivo} className="mr-auto text-xs font-semibold text-naranja">
            {motivo}
          </p>
        )}
        <button
          type="button"
          onClick={cerrar}
          className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-marino hover:border-cielo"
        >
          Cerrar
        </button>
        <button
          type="button"
          onClick={elegir}
          disabled={!puedeElegir}
          aria-describedby={motivo ? idMotivo : undefined}
          className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Elegir este vuelo
        </button>
      </div>
    </dialog>
  )
}
```

- [ ] **Step 2: `frontend/src/components/CardVuelo.tsx`: dos botones y `estadoClase`**

Reemplazar el import de `vuelos` por:

```tsx
import { asientosDe, duracionDe, estadoClase, precioDe, type Vuelo } from '../lib/vuelos'
```

Sumar `onVerDetalle` a las props:

```tsx
interface Props {
  vuelo: Vuelo
  clase: Clase
  onElegir: () => void
  onVerDetalle: () => void
}

export default function CardVuelo({ vuelo, clase, onElegir, onVerDetalle }: Props) {
  const quedan = asientosDe(vuelo, clase)
  const pocos = estadoClase(quedan) !== 'disponible'
```

Reemplazar el pie completo (el `<div className="mt-auto …">` hasta su cierre) por:

```tsx
      <div className="mt-auto flex flex-wrap items-end justify-between gap-3 rounded-b-3xl bg-slate-50 px-5 py-4">
        <div>
          <p className="text-xs text-slate-500">Por persona - {NOMBRE_CLASE[clase]}</p>
          <p className="text-2xl font-extrabold text-marino">{precio(precioDe(vuelo, clase))}</p>
          <p className={`text-xs font-semibold ${pocos ? 'text-naranja' : 'text-slate-400'}`}>
            {pocos ? `¡Quedan ${quedan} ${quedan === 1 ? 'asiento' : 'asientos'}!` : `${quedan} asientos disponibles`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onVerDetalle}
            className="rounded-xl border border-marino bg-white px-3 py-2 text-sm font-bold text-marino hover:border-cielo hover:text-cielo"
          >
            Ver detalle
          </button>
          <button
            type="button"
            onClick={onElegir}
            className="rounded-xl bg-marino px-4 py-2 text-sm font-bold text-white hover:bg-cielo"
          >
            Elegir
          </button>
        </div>
      </div>
```

(Se saca `group-hover:bg-cielo` de "Elegir": con dos botones, resaltar uno al pasar por la card confunde.)

- [ ] **Step 3: `frontend/src/components/ListaVuelos.tsx`: abrir el diálogo**

Agregar el import:

```tsx
import DetalleVuelo from './DetalleVuelo'
```

Sumar `pasajeros` a las props (debajo de `clase: Clase`):

```tsx
  clase: Clase
  pasajeros: number
```

Cambiar la firma y sumar el estado del diálogo:

```tsx
export default function ListaVuelos({
  titulo,
  subtitulo,
  estado,
  vuelos,
  clase,
  pasajeros,
  sugerencia,
  onElegir,
  onReintentar,
}: Props) {
  const [visibles, setVisibles] = useState(POR_PAGINA)
  // Vuelo cuyo detalle está abierto (null = diálogo cerrado).
  const [detalle, setDetalle] = useState<Vuelo | null>(null)
```

Reemplazar el render de cada card:

```tsx
              <CardVuelo
                key={v.id}
                vuelo={v}
                clase={clase}
                onElegir={() => onElegir(v)}
                onVerDetalle={() => setDetalle(v)}
              />
```

Y justo antes del `</section>` final agregar:

```tsx
      {detalle && (
        <DetalleVuelo
          vuelo={detalle}
          clase={clase}
          pasajeros={pasajeros}
          onElegir={onElegir}
          onCerrar={() => setDetalle(null)}
        />
      )}
```

- [ ] **Step 4: `frontend/src/pages/Vuelos.tsx`: pasar `pasajeros`**

En las dos `<ListaVuelos …>` (paso de ida y paso de vuelta), debajo de `clase={f.clase}` agregar:

```tsx
            pasajeros={f.pasajeros}
```

- [ ] **Step 5: Verificar build, lint y chequeos**

Run (desde `frontend/`): `npm run build`, `npm run lint`, `npm run check`
Expected: sin errores (sigue la advertencia conocida de `sesion.tsx`).

- [ ] **Step 6: Verificación manual**

Run: `npm run dev` y buscar ida y vuelta BHI → AEP con 2 pasajeros.
Expected:
- Cada card tiene "Ver detalle" (borde) y "Elegir" (relleno). A 360px el pie se acomoda en dos líneas, sin scroll horizontal.
- "Ver detalle": se abre el diálogo con fondo oscurecido. Al principio muestra trayecto y fecha, con skeleton en avión y clases; ~300 ms después, la tabla. La consola no muestra errores (StrictMode).
- Se ven: logoA, número de vuelo, "Directo", fecha completa, origen y destino (hora, IATA - ciudad, aeropuerto), duración, avión, tabla Economy/Primera con precio, asientos y estado; la fila de la clase buscada resaltada con "(tu búsqueda)".
- Esc, ✕ y "Cerrar" cierran el diálogo; se puede volver a abrir otro.
- "Elegir este vuelo" en el paso de ida → paso de vuelta; en el paso de vuelta → "Tu viaje" con esa vuelta.
- Motivo de bloqueo: poner temporalmente en `getVuelo` `if (vuelo) return { ...vuelo, asientos_disponibles_economy: 1 }` → con 2 pasajeros en Economy, "Elegir este vuelo" deshabilitado y "No hay lugar para 2 pasajeros en Economy"; luego `{ ...vuelo, estado: 'cancelado' }` → "Este vuelo fue cancelado". **Deshacer el cambio.**
- Error: poner temporalmente `throw new Error('x')` al principio de `getVuelo` → "No pudimos cargar el detalle. Probá de nuevo." con Reintentar y el botón de elegir deshabilitado. **Deshacer el cambio.**
- 360px: el diálogo ocupa casi todo el ancho, el trayecto se apila y la tabla entra sin scroll horizontal.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): diálogo de detalle de vuelo desde los resultados"
```

---

### Task 3: Documentación

**Files:**
- Modify: `docs/arquitectura.md`
- Modify: `docs/memoria.md`

- [ ] **Step 1: `docs/arquitectura.md`**

En **API (propuesta)**, debajo del bloque de `GET /api/vuelos/buscar/…`, agregar:

```
GET  /api/vuelos/{id}/           detalle (US05): el mismo vuelo de la búsqueda + avion {matricula, modelo};
                                 incluye cancelados (estado = cancelado) en vez de 404
```

Y en la estructura de carpetas del frontend, en la línea de `components/`, sumar `DetalleVuelo`:

```
        ├── components/       Header, HeroCarrusel, BuscadorVuelos, FiltroPrecio, CardVuelo, ListaVuelos, DetalleVuelo
```

- [ ] **Step 2: `docs/memoria.md`**

En **Estado actual**, arriba de todo:

```markdown
**2026-10-02 — Detalle de vuelo, US05 (rama `feat/detalle-vuelo`)**
- Cada card de resultados tiene "Ver detalle" y "Elegir". El detalle es un diálogo (`<dialog>` nativo) con origen, destino, horarios, fecha, clases, precio por clase, disponibilidad y avión; se puede elegir el vuelo desde ahí.
- Mock: `getVuelo(id)` (futuro `GET /vuelos/{id}/`), avión por ruta y números de vuelo únicos por ruta y fecha.
```

En la tabla de **Decisiones**, arriba:

```markdown
| 2026-10-02 | Detalle de vuelo en un diálogo sobre los resultados, sin ruta propia | Solo se llega a un vuelo buscándolo; el diálogo no saca al pasajero del flujo de ida y vuelta |
| 2026-10-02 | El detalle pide los datos de nuevo (`getVuelo`) al abrirse | Los asientos pueden cambiar desde la búsqueda y el detalle trae el avión |
| 2026-10-02 | Mock: bloque de números de vuelo por ruta | Respeta el índice único (`numero_vuelo`, `fecha_operacion`) y permite reconstruir el vuelo desde su id |
```

- [ ] **Step 3: Verificación final**

Run (desde `frontend/`): `npm run check`, `npm run build`, `npm run lint`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add docs/arquitectura.md docs/memoria.md
git commit -m "docs: memoria y arquitectura del detalle de vuelo"
```
