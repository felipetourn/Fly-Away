import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EsqueletoPagina } from '../components/Esqueleto'
import OcupacionVuelo from '../components/OcupacionVuelo'
import { ApiError } from '../lib/api'
import { NOMBRE_CLASE } from '../lib/busqueda'
import { duracion, fechaCompleta, fechaCorta, hora, precio } from '../lib/formato'
import { getEstadoVueloMostrador, type EstadoVueloMostrador } from '../lib/mostrador'
import { duracionDe, estadoClase, llegaAlDiaSiguiente, precioDe, type EstadoClase } from '../lib/vuelos'

const BADGE_DISPONIBILIDAD: Record<EstadoClase, [texto: string, colores: string]> = {
  disponible: ['Disponible', 'bg-emerald-50 text-emerald-700'],
  ultimos: ['Últimos asientos', 'bg-orange-50 text-naranja'],
  agotada: ['Agotada', 'bg-slate-100 text-slate-500'],
}

/** Estado operativo de una instancia de vuelo desde mostrador (US14). Solo lectura. */
export default function EmpleadoEstadoVuelo() {
  const { id = '' } = useParams()
  const [pedido, setPedido] = useState(0)
  const [resultado, setResultado] = useState<{
    id: string
    pedido: number
    datos: EstadoVueloMostrador | null
    error: string
    noExiste: boolean
  } | null>(null)

  useEffect(() => {
    let vigente = true
    getEstadoVueloMostrador(id).then(
      (datos) => {
        if (vigente) setResultado({ id, pedido, datos, error: '', noExiste: false })
      },
      (e) => {
        if (!vigente) return
        const noExiste = e instanceof ApiError && e.status === 404
        setResultado({ id, pedido, datos: null, error: e instanceof Error ? e.message : 'No pudimos cargar el estado del vuelo.', noExiste })
      },
    )
    return () => {
      vigente = false
    }
  }, [id, pedido])

  if (!resultado || resultado.id !== id) return <EsqueletoPagina />

  const actualizando = resultado.pedido !== pedido

  const volver = (
    <Link to="/empleado/vuelos" className="font-bold text-cielo hover:underline">
      ← Estado de vuelos
    </Link>
  )
  const { datos, error, noExiste } = resultado
  if (!datos)
    return (
      <main className="mx-auto max-w-4xl px-4 py-8">
        {volver}
        <h1 className="mt-4 text-3xl font-extrabold text-marino">{noExiste ? 'No encontramos el vuelo' : 'Estado del vuelo'}</h1>
        {!noExiste && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      </main>
    )

  const { vuelo, clases } = datos
  const cruzaMedianoche = llegaAlDiaSiguiente(vuelo)

  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {volver}
        <button
          type="button"
          onClick={() => setPedido((n) => n + 1)}
          disabled={actualizando}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-marino hover:border-cielo disabled:opacity-50"
        >
          {actualizando ? 'Actualizando…' : 'Actualizar estado'}
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-extrabold text-marino">Estado del vuelo {vuelo.numero_vuelo}</h1>
        <span className={`rounded-full px-3 py-1 text-xs font-bold ${vuelo.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          {vuelo.estado === 'activo' ? 'Activo' : 'Cancelado'}
        </span>
      </div>
      <p className="mt-1 font-mono text-xs break-all text-slate-500">ID de instancia: {vuelo.id}</p>

      <section aria-label="Información operativa" className="mt-6 rounded-2xl border border-slate-200 bg-white p-5">
        <p className="text-sm font-semibold text-slate-500">
          {fechaCompleta(vuelo.fecha_operacion)} · Avión {vuelo.avion.matricula} ({vuelo.avion.modelo})
        </p>
        <div className="mt-4 grid items-start gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <div>
            <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Origen</p>
            <p className="text-3xl font-extrabold text-marino">{hora(vuelo.hora_partida)}</p>
            <p className="font-bold text-marino">
              {vuelo.origen.codigo_iata} - {vuelo.origen.ciudad}
            </p>
            <p className="text-sm text-slate-500">{vuelo.origen.nombre}</p>
            <p className="mt-1 text-xs text-slate-500">Partida: {fechaCorta(vuelo.fecha_operacion)}</p>
          </div>
          <div className="text-center text-xs text-slate-400 sm:self-center">
            {duracion(duracionDe(vuelo))}
            <div className="relative mx-auto my-2.5 h-px w-28 bg-slate-300 sm:w-32">
              <span aria-hidden="true" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-1 text-xl leading-none text-naranja">
                ✈
              </span>
            </div>
            Directo
          </div>
          <div className="sm:text-right">
            <p className="text-xs font-semibold tracking-wider text-slate-400 uppercase">Destino</p>
            <p className="text-3xl font-extrabold text-marino">
              {hora(vuelo.hora_llegada)}
              {cruzaMedianoche && <sup className="ml-0.5 text-sm font-bold text-naranja" title="Llega al día siguiente">+1</sup>}
            </p>
            <p className="font-bold text-marino">
              {vuelo.destino.codigo_iata} - {vuelo.destino.ciudad}
            </p>
            <p className="text-sm text-slate-500">{vuelo.destino.nombre}</p>
            <p className="mt-1 text-xs text-slate-500">Llegada: {fechaCorta(vuelo.fecha_llegada)}</p>
          </div>
        </div>
      </section>

      <div className="mt-6">
        <h2 className="mb-3 text-lg font-extrabold text-marino">Ocupación del vuelo</h2>
        <OcupacionVuelo ocupacion={datos} />
        <p className="mt-2 text-xs text-slate-500">Vendidos cuenta únicamente las compras confirmadas (pago aprobado).</p>
      </div>

      <section aria-label="Disponibilidad por clase" className="mt-6">
        <h2 className="mb-3 text-lg font-extrabold text-marino">Disponibilidad por clase</h2>
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <caption className="sr-only">Disponibilidad correspondiente a cada clase</caption>
            <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
              <tr>
                {['Clase', 'Capacidad', 'Vendidos', 'Disponibles', 'Precio', 'Disponibilidad'].map((t) => (
                  <th key={t} scope="col" className="px-4 py-3 font-semibold">{t}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {clases.map((c) => {
                const [textoBadge, colorBadge] =
                  vuelo.estado === 'cancelado'
                    ? ['No disponible (vuelo cancelado)', 'bg-red-50 text-red-700']
                    : BADGE_DISPONIBILIDAD[estadoClase(c.disponibles)]
                return (
                  <tr key={c.clase} className="border-b border-slate-100 last:border-0">
                    <th scope="row" className="px-4 py-3 font-bold text-marino">{NOMBRE_CLASE[c.clase]}</th>
                    <td className="px-4 py-3">{c.capacidad}</td>
                    <td className="px-4 py-3">{c.vendidos}</td>
                    <td className="px-4 py-3 font-bold text-marino">{c.disponibles}</td>
                    <td className="px-4 py-3">{precio(precioDe(vuelo, c.clase))}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${colorBadge}`}>
                        {textoBadge}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}
