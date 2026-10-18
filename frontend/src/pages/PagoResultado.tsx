import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { EsqueletoPagina } from '../components/Esqueleto'
import { precio } from '../lib/formato'
import { getPago, medioDePago, mensajeCompra, vueloCorto, type Pago } from '../lib/pagos'
import { descargarTicket, getReserva, type Reserva } from '../lib/reservas'

const TITULO = { aprobado: '¡Compra confirmada!', rechazado: 'Pago rechazado', pendiente: 'Pago pendiente' }

export default function PagoResultado() {
  const { id = '' } = useParams()
  const [pago, setPago] = useState<Pago | null>(null)
  const [error, setError] = useState('')
  const [actualizando, setActualizando] = useState(false)
  const [reserva, setReserva] = useState<Reserva | null>(null)
  const [descargando, setDescargando] = useState('')
  const [errorDescarga, setErrorDescarga] = useState('')
  const dialogo = useRef<HTMLDialogElement>(null)

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

  // Compra confirmada: se abre el diálogo con los tickets para descargar.
  useEffect(() => {
    if (!aprobado || !reservaId) return
    getReserva(reservaId)
      .then((r) => {
        setReserva(r)
        const d = dialogo.current
        if (d && !d.open) d.showModal()
      })
      .catch(() => setReserva(null))
  }, [aprobado, reservaId])

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
      <dialog
        ref={dialogo}
        aria-labelledby="titulo-tickets"
        className="m-auto max-h-[90vh] w-[min(32rem,calc(100%-2rem))] overflow-y-auto rounded-3xl p-0 text-slate-900 shadow-2xl backdrop:bg-marino/45 backdrop:backdrop-blur-sm"
      >
        <div className="p-6">
          <h2 id="titulo-tickets" className="text-2xl font-extrabold text-marino">Tus tickets</h2>
          <p className="mt-1 text-sm text-slate-500">Descargá el PDF de cada pasajero.</p>
          <ul className="mt-5 space-y-3">
            {reserva?.pasajes.map((pasaje) => (
              <li key={pasaje.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 p-4">
                <div>
                  <p className="font-bold text-marino">{pasaje.nombre_pasajero} {pasaje.apellido_pasajero}</p>
                  <p className="font-mono text-xs text-slate-500">{pasaje.codigo_pasaje}</p>
                </div>
                <button
                  type="button"
                  disabled={descargando !== ''}
                  onClick={() => descargar(pasaje.codigo_pasaje)}
                  className="rounded-xl bg-naranja px-4 py-2 text-sm font-bold text-white hover:bg-naranja/90 disabled:opacity-60"
                >
                  {descargando === pasaje.codigo_pasaje ? 'Preparando PDF…' : 'Descargar ticket PDF'}
                </button>
              </li>
            ))}
          </ul>
          {errorDescarga && <p role="alert" className="mt-3 text-sm font-medium text-red-700">{errorDescarga}</p>}
          <p className="mt-5 text-sm text-slate-500">Enviando la factura a tu correo…</p>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={() => dialogo.current?.close()}
              className="rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-slate-50"
            >
              Cerrar
            </button>
          </div>
        </div>
      </dialog>
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
          {pago.estado === 'aprobado' && (
            <Link to="/reservas" className="rounded-xl bg-cielo px-5 py-2.5 font-bold text-white hover:bg-cielo/90">
              Ver mis tickets
            </Link>
          )}
          <Link to="/perfil" className="rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-slate-50">
            Ver mis pagos
          </Link>
        </div>
      </section>
    </main>
  )
}
