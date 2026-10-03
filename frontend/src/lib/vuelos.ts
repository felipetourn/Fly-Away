import { api } from './api.ts'
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
  fecha_llegada: string // la del día siguiente si el vuelo cruza medianoche
  hora_partida: string // HH:MM:SS
  hora_llegada: string
  precio_economy: string // decimal: DRF lo serializa como string
  precio_primera: string
  asientos_disponibles_economy: number
  asientos_disponibles_primera: number
  estado: 'activo' | 'cancelado'
}

/** Parámetros de GET /vuelos/buscar/. `origen` / `destino` '' = cualquiera. `hasta` '' = solo el día `desde`. Precios por persona en `clase`. */
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

export const llegaAlDiaSiguiente = (v: Vuelo) => v.fecha_llegada > v.fecha_operacion

/** Duración en minutos. */
export const duracionDe = (v: Vuelo) =>
  aMinutos(v.hora_llegada) - aMinutos(v.hora_partida) + (llegaAlDiaSiguiente(v) ? 24 * 60 : 0)

/** Solo sirven las vueltas que salen después de que aterriza la ida (la vuelta puede ser un rango que se superpone). */
export function vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[] {
  const aterriza = ida.fecha_llegada + ida.hora_llegada
  return vueltas.filter((v) => v.fecha_operacion + v.hora_partida > aterriza)
}

/** Estado de una clase según sus asientos libres. */
export function estadoClase(asientos: number): EstadoClase {
  if (asientos <= 0) return 'agotada'
  return asientos <= UMBRAL_ULTIMOS ? 'ultimos' : 'disponible'
}
