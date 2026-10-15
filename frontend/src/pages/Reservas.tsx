import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { Esqueleto } from '../components/Esqueleto'
import { fechaCorta, hora, precio } from '../lib/formato'
import { getReservas, pasajesDe, vueloCorto, type Reserva } from '../lib/pagos'

// ponytail: pantalla provisoria sobre las reservas demo; la reemplaza "Mis reservas" de la US06 (docs/arquitectura.md).
export default function Reservas() {
  const [reservas, setReservas] = useState<Reserva[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getReservas()
      .then(setReservas)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">Mis reservas</h1>
      <p className="mt-2 text-slate-500">Reservas de prueba para pagar mientras se completa la reserva de pasajes.</p>
      {error && <p role="alert" className="mt-6 text-sm font-medium text-red-700">{error}</p>}
      {!reservas && !error && (
        <div className="mt-8 space-y-4" aria-busy="true">
          {[0, 1, 2].map((i) => <Esqueleto key={i} className="h-28 w-full rounded-2xl" />)}
        </div>
      )}
      {reservas?.length === 0 && <p className="mt-8 text-slate-500">No hay vuelos disponibles para armar reservas de prueba.</p>}
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
            </div>
            <div className="flex items-center justify-between gap-4 sm:justify-end">
              <p className="text-lg font-extrabold">{precio(Number(r.monto))}</p>
              {r.estado === 'pagada' ? (
                <ChipEstado estado="aprobado" texto="Pagada" />
              ) : (
                <Link to={`/pagar/${r.id}`} className="rounded-xl bg-naranja px-5 py-2.5 font-bold text-white hover:bg-naranja/90">
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
