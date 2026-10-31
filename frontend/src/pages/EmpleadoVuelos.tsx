import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Esqueleto } from '../components/Esqueleto'
import { POR_PAGINA, paginasVisibles, type Pagina } from '../lib/adminVuelos'
import { fechaCorta, hora } from '../lib/formato'
import { leerFiltrosMostrador, listarVuelosMostrador } from '../lib/mostrador'
import { getAeropuertos, llegaAlDiaSiguiente, type Aeropuerto, type VueloDetalle } from '../lib/vuelos'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20'
const PAGINA = 'grid h-10 min-w-10 place-items-center rounded-xl border border-slate-300 bg-white px-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40'

function Flecha({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  )
}

/** Búsqueda y selección de instancias de vuelo desde mostrador (US14). Solo lectura: sin alta, edición ni cancelación. */
export default function EmpleadoVuelos() {
  const [params, setParams] = useSearchParams()
  const clave = params.toString()
  const filtros = leerFiltrosMostrador(params)
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [pedido, setPedido] = useState(0)
  const [resultado, setResultado] = useState<{ clave: string | null; pagina: Pagina<VueloDetalle> | null; error: string }>({
    clave: null,
    pagina: null,
    error: '',
  })

  useEffect(() => {
    getAeropuertos().then(setAeropuertos, () => {})
  }, [])

  useEffect(() => {
    let vigente = true
    listarVuelosMostrador(leerFiltrosMostrador(new URLSearchParams(clave))).then(
      (pagina) => {
        if (vigente) setResultado({ clave, pagina, error: '' })
      },
      (e) => {
        if (vigente) setResultado({ clave, pagina: null, error: e instanceof Error ? e.message : 'No pudimos cargar los vuelos.' })
      },
    )
    return () => {
      vigente = false
    }
  }, [clave, pedido])

  const cargando = resultado.clave !== clave
  const { pagina, error } = resultado

  function filtrar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nuevos = new URLSearchParams()
    for (const [campo, valor] of new FormData(event.currentTarget)) {
      if (typeof valor === 'string' && valor.trim()) nuevos.set(campo, valor.trim())
    }
    if (nuevos.toString() === clave) setPedido((n) => n + 1)
    else setParams(nuevos)
  }

  function irAPagina(page: number) {
    const nuevos = new URLSearchParams(params)
    if (page > 1) nuevos.set('page', String(page))
    else nuevos.delete('page')
    setParams(nuevos)
  }

  const opciones = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <main className="mx-auto max-w-[88rem] px-4 py-8">
      <div>
        <h1 className="text-3xl font-extrabold text-marino">Estado de vuelos</h1>
        <p className="mt-1 text-sm text-slate-600">
          Buscá y seleccioná una instancia de vuelo para consultar su estado operativo, horarios, ocupación y disponibilidad por clase.
        </p>
      </div>

      <form key={clave} onSubmit={filtrar} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-7">
        <label className="text-sm font-semibold text-slate-700 lg:col-span-2">
          ID o número de vuelo
          <input name="q" defaultValue={filtros.q} placeholder="FA 1020" className={CAMPO} />
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Origen
          <select name="origen" defaultValue={filtros.origen} className={CAMPO}>
            <option value="">Todos</option>
            {opciones}
          </select>
        </label>
        <label className="text-sm font-semibold text-slate-700">
          Destino
          <select name="destino" defaultValue={filtros.destino} className={CAMPO}>
            <option value="">Todos</option>
            {opciones}
          </select>
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
          Estado
          <select name="estado" defaultValue={filtros.estado} className={CAMPO}>
            <option value="">Todos</option>
            <option value="activo">Activo</option>
            <option value="cancelado">Cancelado</option>
          </select>
        </label>
        <div className="flex gap-3 sm:col-span-2 lg:col-span-7">
          <button type="submit" className="rounded-xl bg-marino px-5 py-2 text-sm font-bold text-white hover:bg-cielo">
            Buscar
          </button>
          <Link to="/empleado/vuelos" className="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-marino hover:border-cielo">
            Limpiar
          </Link>
        </div>
      </form>

      {error && !cargando && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      {cargando && (
        <div role="status" aria-label="Cargando vuelos" className="mt-6">
          <Esqueleto className="h-4 w-40" />
          <div className="mt-2 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-3 py-3">
              <Esqueleto className="h-4 w-full" />
            </div>
            {Array.from({ length: 8 }, (_, i) => (
              <div key={i} className="flex items-center gap-4 border-b border-slate-100 px-3 py-3 last:border-0">
                <Esqueleto className="h-4 w-64 max-w-[40%]" />
                <Esqueleto className="h-4 w-20" />
                <Esqueleto className="h-4 flex-1" />
                <Esqueleto className="h-8 w-24" />
              </div>
            ))}
          </div>
        </div>
      )}

      {pagina && !cargando && (
        <>
          <p className="mt-6 text-sm text-slate-500">
            {pagina.count} {pagina.count === 1 ? 'vuelo' : 'vuelos'}
            {!filtros.desde && !filtros.q ? ' desde hoy' : ''}
          </p>
          <div className="mt-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <caption className="sr-only">Instancias de vuelo</caption>
              <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
                <tr>
                  {['ID', 'Número', 'Fecha', 'Ruta', 'Partida', 'Llegada', 'Avión', 'Disp. Economy', 'Disp. Primera', 'Estado', 'Acción'].map((t) => (
                    <th key={t} scope="col" className="px-3 py-3 font-semibold">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagina.results.map((v) => (
                  <tr key={v.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">{v.id}</td>
                    <th scope="row" className="px-3 py-2">
                      <Link to={`/empleado/vuelos/${v.id}`} className="font-bold text-marino hover:text-cielo hover:underline">
                        {v.numero_vuelo}
                      </Link>
                    </th>
                    <td className="px-3 py-2">{fechaCorta(v.fecha_operacion)}</td>
                    <td className="px-3 py-2">{v.origen.codigo_iata} → {v.destino.codigo_iata}</td>
                    <td className="px-3 py-2">{hora(v.hora_partida)}</td>
                    <td className="px-3 py-2">
                      {hora(v.hora_llegada)}
                      {llegaAlDiaSiguiente(v) && <sup className="ml-0.5 font-bold text-naranja" title="Llega al día siguiente">+1</sup>}
                    </td>
                    <td className="px-3 py-2">{v.avion.matricula}</td>
                    <td className="px-3 py-2">
                      <span className="font-semibold text-marino">{v.asientos_disponibles_economy}</span> / {v.avion.capacidad_economy}
                    </td>
                    <td className="px-3 py-2">
                      <span className="font-semibold text-marino">{v.asientos_disponibles_primera}</span> / {v.avion.capacidad_primera}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${v.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                        {v.estado === 'activo' ? 'Activo' : 'Cancelado'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/empleado/vuelos/${v.id}`}
                        className="inline-block rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-marino hover:border-cielo hover:text-cielo"
                      >
                        Consultar estado
                      </Link>
                    </td>
                  </tr>
                ))}
                {pagina.results.length === 0 && (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-slate-500">No hay vuelos con esos filtros.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {pagina.count > POR_PAGINA && (
            <nav aria-label="Páginas" className="mt-6 flex flex-wrap items-center justify-center gap-1.5 text-sm">
              <button type="button" onClick={() => irAPagina(filtros.page - 1)} disabled={!pagina.previous} aria-label="Página anterior" className={PAGINA}>
                <Flecha d="M15 6l-6 6 6 6" />
              </button>
              {paginasVisibles(filtros.page, Math.ceil(pagina.count / POR_PAGINA)).map((n, i) =>
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
              <button type="button" onClick={() => irAPagina(filtros.page + 1)} disabled={!pagina.next} aria-label="Página siguiente" className={PAGINA}>
                <Flecha d="M9 6l6 6-6 6" />
              </button>
            </nav>
          )}
        </>
      )}
    </main>
  )
}

