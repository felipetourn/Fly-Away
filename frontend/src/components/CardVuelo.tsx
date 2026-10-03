import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { duracion, fechaCorta, hora, precio } from '../lib/formato'
import { asientosDe, duracionDe, estadoClase, llegaAlDiaSiguiente, precioDe, type Vuelo } from '../lib/vuelos'

interface Props {
  vuelo: Vuelo
  clase: Clase
  onElegir: () => void
  onVerDetalle: () => void
}

export default function CardVuelo({ vuelo, clase, onElegir, onVerDetalle }: Props) {
  const quedan = asientosDe(vuelo, clase)
  const pocos = estadoClase(quedan) !== 'disponible'
  return (
    <article className="group flex flex-col rounded-3xl border border-slate-200 bg-white transition hover:-translate-y-0.5 hover:border-cielo hover:shadow-xl hover:shadow-marino/10">
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
        <span className="flex items-center gap-2 text-sm font-semibold text-marino">
          <img src="/logoA.svg" alt="Fly Away" className="h-6" />
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
          <div className="relative my-2.5 h-px bg-slate-300">
            <span aria-hidden="true" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-1 text-xl leading-none text-naranja">
              ✈
            </span>
          </div>
          {fechaCorta(vuelo.fecha_operacion)}
        </div>
        <div className="text-right">
          <p className="text-2xl font-extrabold">
            {hora(vuelo.hora_llegada)}
            {llegaAlDiaSiguiente(vuelo) && (
              <sup className="ml-0.5 text-xs font-bold text-naranja" title="Llega al día siguiente">+1</sup>
            )}
          </p>
          <p className="text-sm font-semibold text-slate-500">{vuelo.destino.codigo_iata}</p>
        </div>
      </div>

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
    </article>
  )
}
