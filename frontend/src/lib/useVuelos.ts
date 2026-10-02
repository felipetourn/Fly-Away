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
