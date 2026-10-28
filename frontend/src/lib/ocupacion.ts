import { api } from './api.ts'
import type { Clase } from './busqueda.ts'
import type { VueloDetalle } from './vuelos.ts'

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
