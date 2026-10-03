import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { cancelarVuelo, listarVuelos, yaSalio, type FiltrosAdmin, type Pagina } from '../lib/adminVuelos'
import { fechaCorta, hora, precio } from '../lib/formato'
import { getAeropuertos, llegaAlDiaSiguiente, type Aeropuerto, type VueloDetalle } from '../lib/vuelos'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20'
const ICONO = 'grid h-9 w-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100 hover:text-marino aria-disabled:pointer-events-none aria-disabled:opacity-30 disabled:cursor-not-allowed disabled:opacity-30'

function leerFiltros(params: URLSearchParams): FiltrosAdmin {
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

function Icono({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  )
}
const LAPIZ = 'M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z'
const TACHO = 'M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6'

/** Confirmación de la cancelación. Se abre al montarse; al cerrarse avisa con `onCerrar`. */
function ConfirmarCancelacion({
  vuelo,
  onCancelado,
  onCerrar,
}: {
  vuelo: VueloDetalle
  onCancelado: (v: VueloDetalle) => void
  onCerrar: () => void
}) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    // StrictMode monta dos veces en desarrollo: no volver a abrir un diálogo abierto.
    const d = dialogo.current
    if (d && !d.open) d.showModal()
  }, [])

  async function confirmar() {
    setEnviando(true)
    setError('')
    try {
      onCancelado(await cancelarVuelo(vuelo.id))
      dialogo.current?.close()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo cancelar el vuelo.')
      setEnviando(false)
    }
  }

  return (
    <dialog
      ref={dialogo}
      onClose={onCerrar}
      aria-labelledby="titulo-cancelar"
      className="m-auto w-[min(32rem,calc(100%-2rem))] rounded-3xl p-6 text-slate-900 shadow-2xl backdrop:bg-marino/45 backdrop:backdrop-blur-sm"
    >
      <h2 id="titulo-cancelar" className="text-lg font-extrabold text-marino">
        ¿Cancelar el vuelo <span className="font-mono text-base break-all">{vuelo.id}</span>?
      </h2>
      <p className="mt-3 text-sm text-slate-600">
        {vuelo.numero_vuelo}, {fechaCorta(vuelo.fecha_operacion)}, {vuelo.origen.codigo_iata} → {vuelo.destino.codigo_iata},{' '}
        {hora(vuelo.hora_partida)}
      </p>
      <p className="mt-2 text-sm text-slate-600">
        Deja de ofrecerse para la compra. Los demás vuelos {vuelo.numero_vuelo} no cambian y el vuelo queda en el historial.
      </p>
      {error && <p role="alert" className="mt-3 text-sm font-medium text-red-700">{error}</p>}
      <div className="mt-6 flex justify-end gap-3">
        <button type="button" onClick={() => dialogo.current?.close()} className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-marino hover:border-cielo">
          Volver
        </button>
        <button type="button" onClick={confirmar} disabled={enviando} className="rounded-xl bg-red-700 px-5 py-2.5 font-bold text-white hover:bg-red-800 disabled:cursor-wait disabled:opacity-60">
          {enviando ? 'Cancelando…' : 'Cancelar vuelo'}
        </button>
      </div>
    </dialog>
  )
}

export default function AdminVuelos() {
  const [params, setParams] = useSearchParams()
  const clave = params.toString()
  const filtros = leerFiltros(params)
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [resultado, setResultado] = useState<{ clave: string; pagina: Pagina<VueloDetalle> | null; error: string }>({
    clave: '',
    pagina: null,
    error: '',
  })
  const [aCancelar, setACancelar] = useState<VueloDetalle | null>(null)

  useEffect(() => {
    // Sin la lista, los selectores quedan solo con "Todos": el listado funciona igual.
    getAeropuertos().then(setAeropuertos, () => {})
  }, [])

  useEffect(() => {
    let vigente = true
    listarVuelos(leerFiltros(new URLSearchParams(clave))).then(
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
  }, [clave])

  const cargando = resultado.clave !== clave
  const { pagina, error } = resultado

  function filtrar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nuevos = new URLSearchParams()
    for (const [campo, valor] of new FormData(event.currentTarget)) {
      if (typeof valor === 'string' && valor.trim()) nuevos.set(campo, valor.trim())
    }
    setParams(nuevos) // sin `page`: un filtro nuevo vuelve a la primera página
  }

  function irAPagina(page: number) {
    const nuevos = new URLSearchParams(params)
    if (page > 1) nuevos.set('page', String(page))
    else nuevos.delete('page')
    setParams(nuevos)
  }

  function marcarCancelado(cancelado: VueloDetalle) {
    setResultado((r) =>
      r.pagina ? { ...r, pagina: { ...r.pagina, results: r.pagina.results.map((v) => (v.id === cancelado.id ? cancelado : v)) } } : r,
    )
  }

  const opciones = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <main className="mx-auto max-w-[88rem] px-4 py-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-extrabold text-marino">Gestión de vuelos</h1>
        <Link to="/admin/vuelos/nuevo" className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo">
          Nuevo vuelo
        </Link>
      </div>

      {/* key: al cambiar la URL (atrás, alta nueva) el formulario toma los valores de la URL. */}
      <form key={clave} onSubmit={filtrar} className="mt-6 grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-2 lg:grid-cols-7">
        <label className="text-sm font-semibold text-slate-700 lg:col-span-2">
          ID o número de vuelo
          <input name="q" defaultValue={filtros.q} className={CAMPO} />
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
            Filtrar
          </button>
          <Link to="/admin/vuelos" className="rounded-xl border border-slate-300 bg-white px-5 py-2 text-sm font-bold text-marino hover:border-cielo">
            Limpiar
          </Link>
        </div>
      </form>

      {error && !cargando && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      {cargando && <p role="status" className="mt-6 text-sm text-slate-500">Cargando vuelos…</p>}

      {pagina && !cargando && (
        <>
          <p className="mt-6 text-sm text-slate-500">
            {pagina.count} {pagina.count === 1 ? 'vuelo' : 'vuelos'}
            {!filtros.desde && !filtros.q ? ' desde hoy' : ''}
          </p>
          <div className="mt-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <caption className="sr-only">Vuelos</caption>
              <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
                <tr>
                  {['ID', 'Número', 'Fecha', 'Ruta', 'Partida', 'Llegada', 'Avión', 'Economy', 'Primera', 'Estado', 'Acciones'].map((t) => (
                    <th key={t} scope="col" className="px-3 py-3 font-semibold">{t}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pagina.results.map((v) => {
                  const bloqueado = v.estado === 'cancelado' || yaSalio(v)
                  return (
                    <tr key={v.id} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-2 font-mono text-xs text-slate-500">{v.id}</td>
                      <th scope="row" className="px-3 py-2 font-bold text-marino">{v.numero_vuelo}</th>
                      <td className="px-3 py-2">{fechaCorta(v.fecha_operacion)}</td>
                      <td className="px-3 py-2">{v.origen.codigo_iata} → {v.destino.codigo_iata}</td>
                      <td className="px-3 py-2">{hora(v.hora_partida)}</td>
                      <td className="px-3 py-2">
                        {hora(v.hora_llegada)}
                        {llegaAlDiaSiguiente(v) && <sup className="ml-0.5 font-bold text-naranja" title="Llega al día siguiente">+1</sup>}
                      </td>
                      <td className="px-3 py-2">{v.avion.matricula}</td>
                      <td className="px-3 py-2">{precio(Number(v.precio_economy))}</td>
                      <td className="px-3 py-2">{precio(Number(v.precio_primera))}</td>
                      <td className="px-3 py-2">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${v.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                          {v.estado === 'activo' ? 'Activo' : 'Cancelado'}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-1">
                          <Link to={`/admin/vuelos/${v.id}`} aria-label={`Editar vuelo ${v.id}`} title={bloqueado ? 'Ver' : 'Editar'} className={ICONO}>
                            <Icono d={LAPIZ} />
                          </Link>
                          <button type="button" onClick={() => setACancelar(v)} disabled={bloqueado} aria-label={`Cancelar vuelo ${v.id}`} title="Cancelar" className={ICONO}>
                            <Icono d={TACHO} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {pagina.results.length === 0 && (
                  <tr>
                    <td colSpan={11} className="px-3 py-8 text-center text-slate-500">No hay vuelos con esos filtros.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <nav aria-label="Páginas" className="mt-4 flex items-center justify-end gap-3 text-sm">
            <button type="button" onClick={() => irAPagina(filtros.page - 1)} disabled={!pagina.previous} className="rounded-xl border border-slate-300 bg-white px-4 py-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40">
              Anterior
            </button>
            <span className="text-slate-500">Página {filtros.page}</span>
            <button type="button" onClick={() => irAPagina(filtros.page + 1)} disabled={!pagina.next} className="rounded-xl border border-slate-300 bg-white px-4 py-2 font-bold text-marino hover:border-cielo disabled:cursor-not-allowed disabled:opacity-40">
              Siguiente
            </button>
          </nav>
        </>
      )}

      {aCancelar && <ConfirmarCancelacion vuelo={aCancelar} onCancelado={marcarCancelado} onCerrar={() => setACancelar(null)} />}
    </main>
  )
}
