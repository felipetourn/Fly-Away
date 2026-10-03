import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Esqueleto } from '../components/Esqueleto'
import {
  DIAS,
  crearVuelos,
  editarVuelo,
  errorDePeriodo,
  erroresDe,
  fechasDePeriodo,
  getAviones,
  primero,
  yaSalio,
  type ErroresApi,
  type Periodo,
} from '../lib/adminVuelos'
import { hora } from '../lib/formato'
import { getAeropuertos, getVuelo, type Aeropuerto, type Avion, type VueloDetalle } from '../lib/vuelos'

const CAMPO = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20 disabled:bg-slate-100'
const PERIODO_VACIO: Periodo = { desde: '', hasta: '', dias: [], avion: '', precio_economy: '', precio_primera: '' }

function Campo({ etiqueta, error, children }: { etiqueta: string; error: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-semibold text-slate-700">
      {etiqueta}
      {children}
      {error && <span role="alert" className="mt-1 block text-xs font-medium text-red-700">{error}</span>}
    </label>
  )
}

/** Alta (sin `id` en la ruta): datos comunes y períodos. Edición (con `id`): una sola fecha, la del vuelo. */
export default function AdminVueloForm() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [aviones, setAviones] = useState<Avion[]>([])
  const [vuelo, setVuelo] = useState<VueloDetalle | null>(null)
  const [listo, setListo] = useState(false)
  const [errorCarga, setErrorCarga] = useState('')
  const [comunes, setComunes] = useState({ origen: '', destino: '', hora_partida: '', hora_llegada: '' })
  // En la edición hay un solo "período": `desde` es la fecha del vuelo; `hasta` y `dias` no se usan.
  const [periodos, setPeriodos] = useState<Periodo[]>([PERIODO_VACIO])
  const [errores, setErrores] = useState<ErroresApi>({})
  const [errorGeneral, setErrorGeneral] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    let vigente = true
    Promise.all([getAeropuertos(), getAviones(), id ? getVuelo(id) : null]).then(
      ([listaAeropuertos, listaAviones, v]) => {
        if (!vigente) return
        setAeropuertos(listaAeropuertos)
        setAviones(listaAviones)
        if (v) {
          setVuelo(v)
          setComunes({
            origen: v.origen.codigo_iata,
            destino: v.destino.codigo_iata,
            hora_partida: hora(v.hora_partida),
            hora_llegada: hora(v.hora_llegada),
          })
          setPeriodos([
            { ...PERIODO_VACIO, desde: v.fecha_operacion, avion: v.avion.id, precio_economy: v.precio_economy, precio_primera: v.precio_primera },
          ])
        }
        setListo(true)
      },
      (e) => {
        if (vigente) setErrorCarga(e instanceof Error ? e.message : 'No pudimos cargar los datos.')
      },
    )
    return () => {
      vigente = false
    }
  }, [id])

  const soloLectura = vuelo !== null && (vuelo.estado === 'cancelado' || yaSalio(vuelo))
  const cargando = !errorCarga && !listo
  const total = periodos.reduce((n, p) => n + fechasDePeriodo(p.desde, p.hasta, p.dias).length, 0)
  const llegaDespues = comunes.hora_partida !== '' && comunes.hora_llegada !== '' && comunes.hora_llegada < comunes.hora_partida

  const cambiarComun = (campo: keyof typeof comunes, valor: string) => setComunes((c) => ({ ...c, [campo]: valor }))
  const cambiarPeriodo = (i: number, cambios: Partial<Periodo>) =>
    setPeriodos((lista) => lista.map((p, j) => (j === i ? { ...p, ...cambios } : p)))

  // En la edición los errores llegan con los nombres de los campos del vuelo.
  const errorEn = (i: number, campo: keyof Periodo) =>
    id ? primero(errores[campo === 'desde' ? 'fecha_operacion' : campo]) : errorDePeriodo(errores, i, campo)

  async function guardar(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrores({})
    setErrorGeneral('')
    setEnviando(true)
    try {
      if (id) {
        const [p] = periodos
        await editarVuelo(id, { ...comunes, fecha_operacion: p.desde, avion: p.avion, precio_economy: p.precio_economy, precio_primera: p.precio_primera })
        navigate(`/admin/vuelos?q=${encodeURIComponent(id)}`)
      } else {
        const { numero_vuelo } = await crearVuelos({ ...comunes, periodos })
        navigate(`/admin/vuelos?q=${encodeURIComponent(numero_vuelo)}`)
      }
    } catch (e) {
      const detalle = erroresDe(e)
      setErrores(detalle)
      setErrorGeneral(
        primero(detalle.non_field_errors) ||
          (Object.keys(detalle).length ? 'Revisá los campos marcados.' : e instanceof Error ? e.message : 'No se pudo guardar.'),
      )
      setEnviando(false)
    }
  }

  if (errorCarga) {
    return (
      <main className="mx-auto max-w-[88rem] px-4 py-8">
        <p role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{errorCarga}</p>
        <Link to="/admin/vuelos" className="mt-4 inline-block font-semibold text-marino underline">Volver al listado</Link>
      </main>
    )
  }
  if (cargando) {
    return (
      <main role="status" aria-label="Cargando" aria-busy="true" className="mx-auto max-w-[88rem] px-4 py-8">
        <Esqueleto className="h-4 w-32" />
        <Esqueleto className="mt-3 h-9 w-72 max-w-full" />
        {[0, 1].map((i) => (
          <div key={i} className="mt-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-4">
            {[0, 1, 2, 3].map((j) => (
              <Esqueleto key={j} className="h-16" />
            ))}
          </div>
        ))}
      </main>
    )
  }

  const opcionesAeropuerto = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <main className="mx-auto max-w-[88rem] px-4 py-8">
      <Link to="/admin/vuelos" className="text-sm font-semibold text-marino underline">Volver al listado</Link>
      <h1 className="mt-2 text-3xl font-extrabold text-marino">{vuelo ? `Vuelo ${vuelo.numero_vuelo}` : 'Nuevo vuelo'}</h1>
      {vuelo && <p className="mt-1 font-mono text-xs break-all text-slate-500">ID - {vuelo.id}</p>}
      {soloLectura && (
        <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-100 p-4 text-sm font-semibold text-slate-600">
          {vuelo?.estado === 'cancelado' ? 'Este vuelo está cancelado' : 'Este vuelo ya salió'}: no se puede modificar.
        </p>
      )}

      <form onSubmit={guardar} className="mt-6">
        <fieldset disabled={soloLectura || enviando} className="space-y-6">
          <section className="grid gap-4 rounded-2xl border border-slate-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-4">
            <Campo etiqueta="Aeropuerto de origen" error={primero(errores.origen)}>
              <select required value={comunes.origen} onChange={(e) => cambiarComun('origen', e.target.value)} className={CAMPO}>
                <option value="">Elegí un aeropuerto</option>
                {opcionesAeropuerto}
              </select>
            </Campo>
            <Campo etiqueta="Aeropuerto de destino" error={primero(errores.destino)}>
              <select required value={comunes.destino} onChange={(e) => cambiarComun('destino', e.target.value)} className={CAMPO}>
                <option value="">Elegí un aeropuerto</option>
                {opcionesAeropuerto}
              </select>
            </Campo>
            <Campo etiqueta="Hora de partida" error={primero(errores.hora_partida)}>
              <input type="time" required value={comunes.hora_partida} onChange={(e) => cambiarComun('hora_partida', e.target.value)} className={CAMPO} />
            </Campo>
            <Campo etiqueta="Hora de llegada" error={primero(errores.hora_llegada)}>
              <input type="time" required value={comunes.hora_llegada} onChange={(e) => cambiarComun('hora_llegada', e.target.value)} className={CAMPO} />
              {llegaDespues && <span className="mt-1 block text-xs font-semibold text-naranja">Llega al día siguiente</span>}
            </Campo>
          </section>

          {periodos.map((p, i) => (
            <section key={i} aria-label={id ? 'Fecha, avión y precios' : `Período ${i + 1}`} className="rounded-2xl border border-slate-200 bg-white p-5">
              {!id && (
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-extrabold text-marino">Período {i + 1}</h2>
                  {periodos.length > 1 && (
                    <button type="button" onClick={() => setPeriodos((lista) => lista.filter((_, j) => j !== i))} className="text-sm font-semibold text-red-700 underline">
                      Quitar
                    </button>
                  )}
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Campo etiqueta={id ? 'Fecha' : 'Desde'} error={errorEn(i, 'desde')}>
                  <input type="date" required value={p.desde} onChange={(e) => cambiarPeriodo(i, { desde: e.target.value })} className={CAMPO} />
                </Campo>
                {!id && (
                  <Campo etiqueta="Hasta" error={errorEn(i, 'hasta')}>
                    <input type="date" required min={p.desde} value={p.hasta} onChange={(e) => cambiarPeriodo(i, { hasta: e.target.value })} className={CAMPO} />
                  </Campo>
                )}
                {!id && (
                  <fieldset className="sm:col-span-2">
                    <legend className="text-sm font-semibold text-slate-700">Días de la semana</legend>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {DIAS.map((nombre, dia) => (
                        <label key={dia} className="flex cursor-pointer items-center gap-1.5 rounded-xl border border-slate-300 px-3 py-2 text-sm has-checked:border-marino has-checked:bg-marino/5">
                          <input
                            type="checkbox"
                            checked={p.dias.includes(dia)}
                            onChange={(e) => cambiarPeriodo(i, { dias: e.target.checked ? [...p.dias, dia].sort() : p.dias.filter((d) => d !== dia) })}
                          />
                          {nombre}
                        </label>
                      ))}
                    </div>
                    {errorEn(i, 'dias') && <span role="alert" className="mt-1 block text-xs font-medium text-red-700">{errorEn(i, 'dias')}</span>}
                  </fieldset>
                )}
                <div className={id ? '' : 'sm:col-span-2'}>
                  <Campo etiqueta="Avión" error={errorEn(i, 'avion')}>
                    <select required value={p.avion} onChange={(e) => cambiarPeriodo(i, { avion: e.target.value })} className={CAMPO}>
                      <option value="">Elegí un avión</option>
                      {aviones.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.matricula} - {a.modelo} ({a.capacidad_economy} economy, {a.capacidad_primera} primera)
                        </option>
                      ))}
                    </select>
                  </Campo>
                </div>
                <Campo etiqueta="Precio economy" error={errorEn(i, 'precio_economy')}>
                  <input type="number" required min="0.01" step="0.01" value={p.precio_economy} onChange={(e) => cambiarPeriodo(i, { precio_economy: e.target.value })} className={CAMPO} />
                </Campo>
                <Campo etiqueta="Precio primera" error={errorEn(i, 'precio_primera')}>
                  <input type="number" required min="0.01" step="0.01" value={p.precio_primera} onChange={(e) => cambiarPeriodo(i, { precio_primera: e.target.value })} className={CAMPO} />
                </Campo>
              </div>
              {!id && (
                <p className="mt-3 text-xs text-slate-500">
                  {fechasDePeriodo(p.desde, p.hasta, p.dias).length} vuelos en este período
                </p>
              )}
            </section>
          ))}

          {!id && (
            <button type="button" onClick={() => setPeriodos((lista) => [...lista, PERIODO_VACIO])} className="rounded-xl border border-marino bg-white px-4 py-2 text-sm font-bold text-marino hover:border-cielo hover:text-cielo">
              Agregar período
            </button>
          )}

          {errorGeneral && <p role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{errorGeneral}</p>}

          {!soloLectura && (
            <div className="flex flex-wrap items-center justify-end gap-4">
              {!id && (
                <p className="mr-auto text-sm font-semibold text-slate-600">
                  Se {total === 1 ? 'va a generar 1 vuelo' : `van a generar ${total} vuelos`}
                </p>
              )}
              <Link to="/admin/vuelos" className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-marino hover:border-cielo">
                Descartar
              </Link>
              <button type="submit" disabled={!id && total === 0} className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo disabled:cursor-not-allowed disabled:bg-slate-300">
                {enviando ? 'Guardando…' : id ? 'Guardar cambios' : 'Crear vuelos'}
              </button>
            </div>
          )}
        </fieldset>
      </form>
    </main>
  )
}
