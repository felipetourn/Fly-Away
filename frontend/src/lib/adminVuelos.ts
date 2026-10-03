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

/** Cuerpo de un 400 de DRF: { campo: ["mensaje"], periodos: { "0": { campo: ["mensaje"] } }, non_field_errors: ["mensaje"] } */
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

/** Vuelos por página del listado: el `page_size` del backend (Paginacion en vuelos/views.py). */
export const POR_PAGINA = 50

/** Números a mostrar en la paginación: primera, última y las vecinas de `actual`. null = puntos suspensivos. */
export function paginasVisibles(actual: number, total: number): (number | null)[] {
  const ultima = Math.max(1, total)
  const elegidas = [1, actual - 1, actual, actual + 1, ultima].filter((n) => n >= 1 && n <= ultima)
  const paginas: (number | null)[] = []
  for (const n of [...new Set(elegidas)].sort((a, b) => a - b)) {
    const anterior = paginas.at(-1)
    if (typeof anterior === 'number' && n - anterior === 2) paginas.push(n - 1)
    else if (typeof anterior === 'number' && n - anterior > 2) paginas.push(null)
    paginas.push(n)
  }
  return paginas
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

/** Error de `campo` en el período `i`. DRF indexa los errores de una lista por posición: { periodos: { "1": { campo: ["mensaje"] } } }. */
export function errorDePeriodo(errores: ErroresApi, i: number, campo: keyof Periodo): string {
  const lista = errores.periodos
  const item: unknown = lista !== null && typeof lista === 'object' ? (lista as Record<number, unknown>)[i] : null
  return item !== null && typeof item === 'object' ? primero((item as ErroresApi)[campo]) : ''
}

export const listarVuelos = (f: FiltrosAdmin) => api<Pagina<VueloDetalle>>(`/vuelos/?${queryListado(f)}`)

export const getAviones = () => api<Avion[]>('/aviones/')

export const crearVuelos = (alta: AltaVuelo) =>
  api<{ numero_vuelo: string; cantidad: number }>('/vuelos/', { method: 'POST', body: JSON.stringify(alta) })

export const editarVuelo = (id: string, cambios: Partial<EdicionVuelo>) =>
  api<VueloDetalle>(`/vuelos/${encodeURIComponent(id)}/`, { method: 'PATCH', body: JSON.stringify(cambios) })

export const cancelarVuelo = (id: string) =>
  api<VueloDetalle>(`/vuelos/${encodeURIComponent(id)}/cancelar/`, { method: 'POST' })
