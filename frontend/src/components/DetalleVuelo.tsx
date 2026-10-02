import { useEffect, useRef, useState, type ReactNode } from 'react'
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

function Extremo({
  etiqueta,
  horario,
  aeropuerto,
  derecha,
  children,
}: {
  etiqueta: string
  horario: string
  aeropuerto: Aeropuerto
  derecha?: boolean
  children?: ReactNode
}) {
  return (
    <div className={derecha ? 'sm:text-right' : ''}>
      <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">{etiqueta}</p>
      <p className="text-4xl font-extrabold">{hora(horario)}</p>
      <p className="font-bold text-marino">
        {aeropuerto.codigo_iata} · {aeropuerto.ciudad}
      </p>
      <p className="text-sm text-slate-500">{aeropuerto.nombre}</p>
      {children}
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
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <img src="/logoA.svg" alt="" className="h-10" />
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

      <div className="px-4 py-6 sm:px-6">
        <p className="mb-5 text-sm font-semibold text-slate-500">{fechaCompleta(v.fecha_operacion)}</p>
        <div className="grid items-start gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <Extremo etiqueta="Origen" horario={v.hora_partida} aeropuerto={v.origen}>
            <p className="mt-1 text-xs text-slate-400">
              Avión:{' '}
              {detalle ? (
                <span className="font-semibold text-slate-500">{detalle.avion.modelo}</span>
              ) : (
                <span className="inline-block h-3 w-24 animate-pulse rounded bg-slate-200 align-middle" />
              )}
            </p>
          </Extremo>
          <div className="text-center text-xs text-slate-400 sm:self-center">
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
      </div>

      <div className="px-4 pb-6 sm:px-6">
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
                <th scope="col" className="px-1.5 pb-1 font-semibold sm:px-3">
                  Clase
                </th>
                <th scope="col" className="px-1.5 pb-1 font-semibold sm:px-3">
                  Precio por persona
                </th>
                {/* En mobile no entra: la cantidad va debajo del estado. */}
                <th scope="col" className="hidden px-1.5 pb-1 font-semibold sm:table-cell sm:px-3">
                  Asientos
                </th>
                <th scope="col" className="px-1.5 pb-1 text-right font-semibold sm:px-3">
                  Estado
                </th>
              </tr>
            </thead>
            <tbody>
              {CLASES.map((c) => {
                const asientos = asientosDe(detalle, c)
                const [texto, colores] = BADGE[estadoClase(asientos)]
                const celda = `px-1.5 py-3 sm:px-3 ${c === clase ? 'bg-cielo/5' : ''}`
                return (
                  <tr key={c}>
                    <th scope="row" className={`${celda} rounded-l-xl font-bold text-marino`}>
                      {NOMBRE_CLASE[c]}
                      {c === clase && <span className="block text-xs font-semibold text-cielo">(tu búsqueda)</span>}
                    </th>
                    <td className={`${celda} text-base font-extrabold whitespace-nowrap text-marino sm:text-lg`}>
                      {precio(precioDe(detalle, c))}
                    </td>
                    <td className={`${celda} hidden font-semibold sm:table-cell`}>{asientos}</td>
                    <td className={`${celda} rounded-r-xl text-right`}>
                      <span className={`rounded-full px-2 py-1 text-[11px] font-bold whitespace-nowrap sm:px-2.5 sm:text-xs ${colores}`}>
                        {texto}
                      </span>
                      <span className="mt-1 block text-xs font-semibold text-slate-500 sm:hidden">
                        {asientos} {asientos === 1 ? 'asiento' : 'asientos'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-end gap-3 rounded-b-3xl bg-slate-50 px-4 py-4 sm:px-6">
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
