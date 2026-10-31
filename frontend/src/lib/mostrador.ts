import { api } from './api.ts'
import { queryListado, type FiltrosAdmin, type Pagina } from './adminVuelos.ts'
import type { OcupacionDeVuelo } from './ocupacion.ts'
import type { VueloDetalle } from './vuelos.ts'

// Consultas operativas de vuelos desde mostrador (US14).

export type FiltrosMostrador = FiltrosAdmin
export type EstadoVueloMostrador = OcupacionDeVuelo

export function leerFiltrosMostrador(params: URLSearchParams): FiltrosMostrador {
  const texto = (clave: string) => params.get(clave) ?? ''
  return {
    q: texto('q'),
    origen: texto('origen'),
    destino: texto('destino'),
    desde: texto('desde'),
    hasta: texto('hasta'),
    estado: texto('estado'),
    page: Math.max(1, Number(params.get('page')) || 1),
  }
}

export const listarVuelosMostrador = (f: FiltrosMostrador) =>
  api<Pagina<VueloDetalle>>(`/mostrador/vuelos/?${queryListado(f)}`)

export const getEstadoVueloMostrador = (id: string) =>
  api<EstadoVueloMostrador>(`/mostrador/vuelos/${encodeURIComponent(id)}/`)

