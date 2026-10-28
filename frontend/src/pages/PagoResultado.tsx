import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { Esqueleto, EsqueletoPagina } from '../components/Esqueleto'
import Toast from '../components/Toast'
import { precio } from '../lib/formato'
import { avisoFactura, getPago, medioDePago, mensajeCompra, vueloCorto, type Aviso, type Pago } from '../lib/pagos'
import { descargarTicket, getReserva, type Reserva } from '../lib/reservas'
import { useSesion } from '../lib/sesion'

const TITULO = { aprobado: '¡Compra confirmada!', rechazado: 'Pago rechazado', pendiente: 'Pago pendiente' }

export default function PagoResultado() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const { usuario } = useSesion()
  const [pago, setPago] = useState<Pago | null>(null)
  const [error, setError] = useState('')
  const [actualizando, setActualizando] = useState(false)
  const [reserva, setReserva] = useState<Reserva | null | undefined>(undefined) // undefined = cargando, null = falló
  const [descargando, setDescargando] = useState('')
  const [errorDescarga, setErrorDescarga] = useState('')
  const [aviso, setAviso] = useState<Aviso | null>(null)

  const cargar = useCallback(
    () =>
      getPago(id)
        .then((p) => {
          setPago(p)
          setError('')
        })
        .catch((e: Error) => setError(e.message)),
    [id],
  )

  useEffect(() => {
    cargar()
  }, [cargar])

  const aprobado = pago?.estado === 'aprobado'
  const reservaId = pago?.reserva_id

  // Recién pagado (?recien=1, al llegar desde el pago): se avisa una sola vez del envío de la factura.
  // Se lee al montar: si el pago sigue pendiente, el aviso sale cuando "Actualizar" lo trae aprobado.
  const avisoPendiente = useRef(params.get('recien') === '1')
  const facturaEnviadaEn = pago?.factura_enviada_en ?? null
  const email = usuario?.email ?? ''

  // Compra confirmada: los tickets de cada pasajero van en la misma tarjeta.
  useEffect(() => {
    if (!aprobado || !reservaId) return
    const avisar = (r: Reserva | null) => {
      if (!avisoPendiente.current) return
      avisoPendiente.current = false
      setAviso(avisoFactura({ estado: 'aprobado', factura_enviada_en: facturaEnviadaEn }, r?.contacto_email || email))
      setParams(
        (p) => {
          p.delete('recien')
          return p
        },
        { replace: true },
      )
    }
    getReserva(reservaId)
      .then((r) => {
        setReserva(r)
        avisar(r)
      })
      .catch(() => {
        setReserva(null)
        avisar(null)
      })
  }, [aprobado, reservaId, facturaEnviadaEn, email, setParams])

  async function descargar(codigo: string) {
    setDescargando(codigo)
    setErrorDescarga('')
    try {
      await descargarTicket(codigo)
    } catch (e) {
      setErrorDescarga(e instanceof Error ? e.message : 'No pudimos descargar el ticket.')
    } finally {
      setDescargando('')
    }
  }

  if (!pago && !error) return <EsqueletoPagina angosta />
  if (!pago)
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <h1 className="text-3xl font-extrabold text-marino">No encontramos el pago</h1>
        <p role="alert" className="mt-4 text-sm font-medium text-red-700">{error}</p>
        <Link to="/perfil" className="mt-6 inline-block font-bold text-cielo hover:underline">Ver mis pagos</Link>
      </main>
    )

  const mensaje = mensajeCompra(pago)

  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <section role="status" aria-live="polite" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <ChipEstado estado={pago.estado} />
        <h1 className="mt-3 text-3xl font-extrabold text-marino">{TITULO[pago.estado]}</h1>
        {mensaje && <p className="mt-2 font-medium text-slate-700">{mensaje}</p>}
        <p className="mt-2 text-slate-600">{pago.detalle}</p>
        <dl className="mt-6 space-y-2 border-t border-slate-100 pt-4 text-sm">
          {pago.vuelo && (
            <div className="flex justify-between gap-4"><dt className="text-slate-500">Vuelo</dt><dd className="font-medium">{vueloCorto(pago.vuelo)}</dd></div>
          )}
          <div className="flex justify-between gap-4"><dt className="text-slate-500">Monto</dt><dd className="font-bold">{precio(Number(pago.monto))}</dd></div>
          <div className="flex justify-between gap-4"><dt className="text-slate-500">Medio</dt><dd className="font-medium">{medioDePago(pago)}</dd></div>
          {pago.transaccion_externa_id && (
            <div className="flex justify-between gap-4"><dt className="text-slate-500">N° de operación</dt><dd className="font-mono text-xs break-all">{pago.transaccion_externa_id}</dd></div>
          )}
        </dl>
        {aprobado && (
          <div className="mt-6 border-t border-slate-100 pt-4">
            <h2 className="font-extrabold text-marino">Tus tickets</h2>
            {reserva === undefined && (
              <div className="mt-3 space-y-3" aria-busy="true">
                <Esqueleto className="h-16 w-full rounded-2xl" />
                <Esqueleto className="h-16 w-full rounded-2xl" />
              </div>
            )}
            {reserva === null && (
              <p role="alert" className="mt-3 text-sm text-slate-600">
                No pudimos cargar tus tickets.{' '}
                <Link to="/reservas" className="font-bold text-cielo hover:underline">Ir a mis reservas</Link>
              </p>
            )}
            {reserva && (
              <ul className="mt-3 space-y-3">
                {reserva.pasajes.map((pasaje) => (
                  <li key={pasaje.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 p-4">
                    <div>
                      <p className="font-bold text-marino">{pasaje.nombre_pasajero} {pasaje.apellido_pasajero}</p>
                      <p className="font-mono text-xs text-slate-500">{pasaje.codigo_pasaje}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <Link
                        to={`/pasajes/${encodeURIComponent(pasaje.codigo_pasaje)}`}
                        className="text-sm font-bold text-cielo hover:underline"
                      >
                        Ver ticket
                      </Link>
                      <button
                        type="button"
                        disabled={descargando !== ''}
                        onClick={() => descargar(pasaje.codigo_pasaje)}
                        className="rounded-xl bg-naranja px-4 py-2 text-sm font-bold text-white hover:bg-naranja/90 disabled:opacity-60"
                      >
                        {descargando === pasaje.codigo_pasaje ? 'Preparando PDF…' : 'Descargar PDF'}
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {errorDescarga && <p role="alert" className="mt-3 text-sm font-medium text-red-700">{errorDescarga}</p>}
          </div>
        )}
        {error && <p role="alert" className="mt-4 text-sm font-medium text-red-700">{error}</p>}
        <div className="mt-6 flex flex-wrap gap-3">
          {pago.estado === 'rechazado' && (
            <Link to={`/pagar/${pago.reserva_id}`} className="rounded-xl bg-naranja px-5 py-2.5 font-bold text-white hover:bg-naranja/90">
              Intentar de nuevo
            </Link>
          )}
          {pago.estado === 'pendiente' && (
            <button
              type="button"
              disabled={actualizando}
              onClick={() => {
                setActualizando(true)
                cargar().finally(() => setActualizando(false))
              }}
              className="rounded-xl bg-cielo px-5 py-2.5 font-bold text-white hover:bg-cielo/90 disabled:opacity-60"
            >
              {actualizando ? 'Actualizando…' : 'Actualizar'}
            </button>
          )}
          <Link to="/perfil" className="rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-slate-50">
            Ver mis pagos
          </Link>
        </div>
      </section>
      {aviso && <Toast aviso={aviso} onCerrar={() => setAviso(null)} />}
    </main>
  )
}
