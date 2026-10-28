import { api } from './api.ts'
import type { Clase } from './busqueda.ts'
import type { Pagina } from './adminVuelos.ts'
import type { Vuelo, VueloDetalle } from './vuelos.ts'

// Ocupación de los vuelos (US12, US13). Vendidos = solo compras confirmadas; lo calcula el backend.

export interface Cupo {
  capacidad: number
  vendidos: number
  disponibles: number
}

export interface OcupacionClase extends Cupo {
  clase: Clase
}

/** Lo que muestra `OcupacionVuelo`: una fila por clase y el total. */
export interface Ocupacion {
  clases: OcupacionClase[]
  total: Cupo
}

export interface OcupacionDeVuelo extends Ocupacion {
  vuelo: VueloDetalle
}

/** Porcentaje vendido, entero de 0 a 100. Una clase sin capacidad cuenta como 0 %. */
export function porcentaje(vendidos: number, capacidad: number): number {
  return capacidad > 0 ? Math.round((vendidos / capacidad) * 100) : 0
}

export const getOcupacion = (id: string) => api<OcupacionDeVuelo>(`/reportes/ocupacion/${encodeURIComponent(id)}/`)

/** Filtros del reporte (US13). '' = sin filtrar. `vuelo` = id de la instancia o parte del número; origen y destino, código IATA. */
export interface FiltrosReporte {
  vuelo: string
  desde: string
  hasta: string
  origen: string
  destino: string
  clase: '' | Clase
  page: number
}

export interface FilaReporte extends Ocupacion {
  vuelo: Vuelo
}

/** Una página de filas y los totales de todo el filtro. */
export interface Reporte extends Pagina<FilaReporte> {
  totales: Ocupacion
}

export const FALTA_CRITERIO = 'Elegí al menos un criterio: vuelo, fechas, origen o destino.'

/** La clase sola no alcanza: hace falta un vuelo, una fecha, el origen o el destino (la misma regla que el backend). */
export const faltaCriterio = (f: FiltrosReporte) => !f.vuelo.trim() && !f.desde && !f.hasta && !f.origen && !f.destino

export function queryReporte(f: FiltrosReporte): URLSearchParams {
  const params = new URLSearchParams()
  for (const clave of ['vuelo', 'desde', 'hasta', 'origen', 'destino', 'clase'] as const) {
    const valor = f[clave].trim()
    if (valor) params.set(clave, valor)
  }
  if (f.page > 1) params.set('page', String(f.page))
  return params
}

export const getReporte = (f: FiltrosReporte) => api<Reporte>(`/reportes/ocupacion/?${queryReporte(f)}`)
