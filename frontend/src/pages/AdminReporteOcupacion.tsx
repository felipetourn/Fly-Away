import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Esqueleto } from '../components/Esqueleto'
import OcupacionVuelo, { BarraOcupacion } from '../components/OcupacionVuelo'
import { POR_PAGINA, erroresDe, paginasVisibles, primero } from '../lib/adminVuelos'
import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { fechaCorta, hora } from '../lib/formato'
import { FALTA_CRITERIO, faltaCriterio, getReporte, porcentaje, type FiltrosReporte, type Reporte } from '../lib/ocupacion'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20'
const PAGINA = 'grid h-10 min-w-10 place-items-center rounded-xl border border-slate-300 bg-white px-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40'
const CLASES: Clase[] = ['economy', 'primera']

function leerFiltros(params: URLSearchParams): FiltrosReporte {
  const clase = params.get('clase')
  return {
    vuelo: params.get('vuelo') ?? '',
    desde: params.get('desde') ?? '',
    hasta: params.get('hasta') ?? '',
    clase: clase === 'economy' || clase === 'primera' ? clase : '',
    page: Math.max(1, Number(params.get('page')) || 1),
  }
}

/** El primer error del backend: de un campo del formulario o general. */
function mensajeDe(e: unknown): string {
  const errores = erroresDe(e)
  for (const campo of ['non_field_errors', 'vuelo', 'desde', 'hasta', 'clase']) {
    const mensaje = primero(errores[campo])
    if (mensaje) return mensaje
  }
  return e instanceof Error ? e.message : 'No pudimos generar el reporte.'
}

function Flecha({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  )
}

/** Reporte de ocupación (US13): filtros por vuelo, fechas y clase; los filtros viven en la URL. */
export default function AdminReporteOcupacion() {
  const [params, setParams] = useSearchParams()
  const clave = params.toString()
  const filtros = leerFiltros(params)
  const sinCriterio = faltaCriterio(filtros)
  const [resultado, setResultado] = useState<{ clave: string | null; reporte: Reporte | null; error: string }>({
    clave: null,
    reporte: null,
    error: '',
  })
  // El aviso es de la URL en la que se pidió: al navegar (atrás, adelante) desaparece.
  const [aviso, setAviso] = useState({ clave: '', texto: '' })
  const textoAviso = aviso.clave === clave ? aviso.texto : ''
  // Generar de nuevo con los mismos filtros vuelve a pedir el reporte (pudo haber ventas nuevas).
  const [pedido, setPedido] = useState(0)

  useEffect(() => {
    const f = leerFiltros(new URLSearchParams(clave))
    if (faltaCriterio(f)) return // sin criterios no se pide nada
    let vigente = true
    getReporte(f).then(
      (reporte) => {
        if (vigente) setResultado({ clave, reporte, error: '' })
      },
      (e) => {
        if (vigente) setResultado({ clave, reporte: null, error: mensajeDe(e) })
      },
    )
    return () => {
      vigente = false
    }
  }, [clave, pedido])

  const cargando = !sinCriterio && resultado.clave !== clave
  const { reporte, error } = resultado.clave === clave ? resultado : { reporte: null, error: '' }
  const clases = filtros.clase ? [filtros.clase] : CLASES

  function generar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nuevos = new URLSearchParams()
    for (const [campo, valor] of new FormData(event.currentTarget)) {
      if (typeof valor === 'string' && valor.trim()) nuevos.set(campo, valor.trim())
    }
    if (faltaCriterio(leerFiltros(nuevos))) {
      setAviso({ clave, texto: FALTA_CRITERIO })
      return
    }
    setAviso({ clave: '', texto: '' })
    if (nuevos.toString() === clave) setPedido((n) => n + 1)
    else setParams(nuevos) // sin `page`: un reporte nuevo vuelve a la primera página
  }

  function irAPagina(page: number) {
    const nuevos = new URLSearchParams(params)
    if (page > 1) nuevos.set('page', String(page))
    else nuevos.delete('page')
    setParams(nuevos)
  }

  return (
    <main className="mx-auto max-w-[88rem] px-4 py-8">
      <h1 className="text-3xl font-extrabold text-marino">Reporte de ocupación</h1>

      {/* key: al cambiar la URL (atrás, adelante) el formulario toma los valores de la URL. */}
      <form key={clave} onSubmit={generar} noValidate className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-sm font-semibold text-slate-700 sm:col-span-2">
          ID o número de vuelo
          <input name="vuelo" defaultValue={filtros.vuelo} placeholder="FA 1020" className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Desde
          <input type="date" name="desde" defaultValue={filtros.desde} className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Hasta
          <input type="date" name="hasta" defaultValue={filtros.hasta} className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Clase
          <select name="clase" defaultValue={filtros.clase} className={CAMPO}>
            <option value="">Todas</option>
            <option value="economy">Economy</option>
            <option value="primera">Primera</option>
          </select>
        </label>
        <div className="flex flex-wrap items-center gap-3 sm:col-span-2 lg:col-span-5">
          <button type="submit" className="rounded-xl bg-marino px-5 py-2 text-sm font-bold text-white hover:bg-cielo">
            Generar reporte
          </button>
          <Link to="/admin/ocupacion" onClick={() => setAviso({ clave: '', texto: '' })} className="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-marino hover:border-cielo">
            Limpiar
          </Link>
          {textoAviso && <p role="alert" className="text-sm font-semibold text-red-700">{textoAviso}</p>}
        </div>
      </form>

      {sinCriterio && !textoAviso && <p className="mt-6 text-sm text-slate-500">Elegí un vuelo o un rango de fechas para generar el reporte.</p>}
      {error && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      {cargando && (
        <div role="status" aria-label="Generando reporte" className="mt-6">
          <Esqueleto className="h-24 w-full rounded-2xl" />
          <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {Array.from({ length: 6 }, (_, i) => (
              <div key={i} className="flex items-center gap-4 border-b border-slate-100 px-3 py-3 last:border-0">
                <Esqueleto className="h-4 w-24" />
                <Esqueleto className="h-4 w-20" />
                <Esqueleto className="h-4 flex-1" />
              </div>
            ))}
          </div>
        </div>
      )}

      {reporte && (
        <>
          {reporte.count > 0 && (
            <section className="mt-6">
              <h2 className="mb-3 text-lg font-extrabold text-marino">
                Totales de {reporte.count} {reporte.count === 1 ? 'vuelo' : 'vuelos'}
              </h2>
              <OcupacionVuelo ocupacion={reporte.totales} />
            </section>
          )}
          <div className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <caption className="sr-only">Ocupación por vuelo</caption>
              <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
                <tr>
                  {['Número', 'Fecha', 'Ruta', 'Estado', ...clases.map((c) => NOMBRE_CLASE[c]), 'Ocupación'].map((t) => (
                    <th key={t} scope="col" className="px-3 py-3 font-semibold">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reporte.results.map(({ vuelo: v, clases: porClase, total }) => (
                  <tr key={v.id} className="border-b border-slate-100 last:border-0">
                    <th scope="row" className="px-3 py-2">
                      <Link to={`/admin/vuelos/${v.id}/ocupacion`} title="Ver ocupación" className="font-bold text-marino hover:text-cielo hover:underline">
                        {v.numero_vuelo}
                      </Link>
                    </th>
                    <td className="px-3 py-2">{fechaCorta(v.fecha_operacion)} · {hora(v.hora_partida)}</td>
                    <td className="px-3 py-2">{v.origen.codigo_iata} → {v.destino.codigo_iata}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${v.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                        {v.estado === 'activo' ? 'Activo' : 'Cancelado'}
                      </span>
                    </td>
                    {porClase.map((c) => (
                      <td key={c.clase} className="px-3 py-2">
                        <span className="font-semibold">{c.vendidos}</span> / {c.capacidad}
                        <span className="block text-xs text-slate-500">{c.disponibles} disp.</span>
                      </td>
                    ))}
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <BarraOcupacion chica vendidos={total.vendidos} capacidad={total.capacidad} etiqueta={`${total.vendidos} de ${total.capacidad} vendidos`} />
                        <span className="font-bold">{porcentaje(total.vendidos, total.capacidad)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {reporte.count === 0 && (
                  <tr>
                    <td colSpan={5 + clases.length} className="px-3 py-8 text-center text-slate-500">No hay vuelos para esos criterios.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {reporte.count > POR_PAGINA && (
            <nav aria-label="Páginas" className="mt-6 flex flex-wrap items-center justify-center gap-1.5 text-sm">
              <button type="button" onClick={() => irAPagina(filtros.page - 1)} disabled={!reporte.previous} aria-label="Página anterior" className={PAGINA}>
                <Flecha d="M15 6l-6 6 6 6" />
              </button>
              {paginasVisibles(filtros.page, Math.ceil(reporte.count / POR_PAGINA)).map((n, i) =>
                n === null ? (
                  <span key={`hueco-${i}`} aria-hidden="true" className="px-1 text-slate-400">…</span>
                ) : (
                  <button
                    key={n}
                    type="button"
                    onClick={() => irAPagina(n)}
                    aria-label={`Página ${n}`}
                    aria-current={n === filtros.page ? 'page' : undefined}
                    className={`${PAGINA} aria-[current=page]:border-marino aria-[current=page]:bg-marino aria-[current=page]:text-white`}
                  >
                    {n}
                  </button>
                ),
              )}
              <button type="button" onClick={() => irAPagina(filtros.page + 1)} disabled={!reporte.next} aria-label="Página siguiente" className={PAGINA}>
                <Flecha d="M9 6l6 6-6 6" />
              </button>
            </nav>
          )}
        </>
      )}
    </main>
  )
}
