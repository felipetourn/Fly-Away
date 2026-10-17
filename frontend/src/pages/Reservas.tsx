import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { Esqueleto } from '../components/Esqueleto'
import { fechaCorta, hora, precio } from '../lib/formato'
import { pasajesDe, vueloCorto } from '../lib/pagos'
import { getMisReservas, type Reserva } from '../lib/reservas'

export default function Reservas() {
  const [reservas, setReservas] = useState<Reserva[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getMisReservas()
      .then(setReservas)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">Mis reservas</h1>
      <p className="mt-2 text-slate-500">Consultá tus reservas de pasajes y continuá con el pago de las que tenés pendientes.</p>
      {error && <p role="alert" className="mt-6 text-sm font-medium text-red-700">{error}</p>}
      {!reservas && !error && (
        <div className="mt-8 space-y-4" aria-busy="true">
          {[0, 1, 2].map((i) => <Esqueleto key={i} className="h-28 w-full rounded-2xl" />)}
        </div>
      )}
      {reservas?.length === 0 && (
        <div className="mt-12 rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-bold text-marino">No tenés reservas registradas</p>
          <p className="mt-2 text-sm text-slate-500">Buscá tu próximo vuelo y reservá hasta 9 pasajes para vos o tus acompañantes.</p>
          <Link
            to="/"
            className="mt-6 inline-block rounded-xl bg-marino px-6 py-3 font-bold text-white hover:bg-cielo transition-colors"
          >
            Buscar vuelos
          </Link>
        </div>
      )}
      <ul className="mt-8 space-y-4">
        {reservas?.map((r) => (
          <li
            key={r.id}
            className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between"
          >
            <div>
              <p className="font-bold text-marino">{vueloCorto(r.vuelo)}</p>
              <p className="mt-1 text-sm text-slate-500">
                {fechaCorta(r.vuelo.fecha_operacion)} - {hora(r.vuelo.hora_partida)} - {pasajesDe(r)}
              </p>
              {r.contacto_nombre && (
                <p className="mt-1 text-xs text-slate-400">
                  Contacto: {r.contacto_nombre} ({r.contacto_email})
                </p>
              )}
              {r.estado === 'pagada' && r.pasajes.length > 0 && (
                <ul className="mt-4 space-y-2 border-t border-slate-100 pt-3">
                  {r.pasajes.map((pasaje) => (
                    <li key={pasaje.id}>
                      <Link
                        to={`/pasajes/${encodeURIComponent(pasaje.codigo_pasaje)}`}
                        className="text-sm font-bold text-cielo hover:underline"
                      >
                        Ver ticket de {pasaje.nombre_pasajero} {pasaje.apellido_pasajero} · {pasaje.codigo_pasaje}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="flex items-center justify-between gap-4 sm:justify-end">
              <p className="text-lg font-extrabold">{precio(Number(r.monto))}</p>
              {r.estado === 'pagada' ? (
                <ChipEstado estado="aprobado" texto="Confirmada" />
              ) : r.estado === 'cancelada' ? (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">Cancelada</span>
              ) : (
                <Link
                  to={`/pagar/${r.id}`}
                  className="rounded-xl bg-naranja px-5 py-2.5 font-bold text-white hover:bg-naranja/90 transition-colors"
                >
                  Pagar
                </Link>
              )}
            </div>
          </li>
        ))}
      </ul>
    </main>
  )
}
