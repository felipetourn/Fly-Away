import { useState } from 'react'
import type { Clase } from '../lib/busqueda'
import type { EstadoBusqueda } from '../lib/useVuelos'
import type { Vuelo } from '../lib/vuelos'
import CardVuelo from './CardVuelo'
import DetalleVuelo from './DetalleVuelo'

interface Props {
  titulo: string
  subtitulo: string
  estado: EstadoBusqueda
  vuelos: Vuelo[]
  clase: Clase
  pasajeros: number
  /** Consejo que acompaña al "no hay resultados". */
  sugerencia: string
  onElegir: (v: Vuelo) => void
  onReintentar: () => void
}

const POR_PAGINA = 12

const grilla = 'grid gap-4 md:grid-cols-2 lg:grid-cols-3'

/** Muestra los vuelos de a 12. Se resetea con una `key` distinta por búsqueda. */
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
  const encontrados =
    estado === 'ok' ? `, ${vuelos.length} ${vuelos.length === 1 ? 'vuelo encontrado' : 'vuelos encontrados'}` : ''
  return (
    <section>
      <h2 className="mb-1 text-2xl font-extrabold text-marino md:text-3xl">{titulo}</h2>
      {/* Solo el resumen se anuncia; no toda la grilla. */}
      <p className="mb-6 text-slate-500" aria-live="polite">
        {subtitulo}
        {encontrados}
      </p>

      {estado === 'cargando' && (
        <div className={grilla} role="status" aria-label="Buscando vuelos">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-56 animate-pulse rounded-3xl bg-slate-200/70" />
          ))}
        </div>
      )}

      {estado === 'error' && (
        <div role="alert" className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700">
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
              <CardVuelo
                key={v.id}
                vuelo={v}
                clase={clase}
                onElegir={() => onElegir(v)}
                onVerDetalle={() => setDetalle(v)}
              />
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
      {detalle && (
        <DetalleVuelo
          key={detalle.id}
          vuelo={detalle}
          clase={clase}
          pasajeros={pasajeros}
          onElegir={onElegir}
          onCerrar={() => setDetalle(null)}
        />
      )}
    </section>
  )
}
