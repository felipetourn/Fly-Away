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
