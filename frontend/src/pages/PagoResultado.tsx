import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { EsqueletoPagina } from '../components/Esqueleto'
import { precio } from '../lib/formato'
import { getPago, medioDePago, mensajeCompra, vueloCorto, type Pago } from '../lib/pagos'

const TITULO = { aprobado: '¡Compra confirmada!', rechazado: 'Pago rechazado', pendiente: 'Pago pendiente' }

export default function PagoResultado() {
  const { id = '' } = useParams()
  const [pago, setPago] = useState<Pago | null>(null)
  const [error, setError] = useState('')
  const [actualizando, setActualizando] = useState(false)

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
    </main>
  )
}
