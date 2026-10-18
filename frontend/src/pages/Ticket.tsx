import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EsqueletoPagina } from '../components/Esqueleto'
import { NOMBRE_CLASE } from '../lib/busqueda'
import { fechaCorta, hora } from '../lib/formato'
import { descargarTicket, getTicket, type TicketElectronico } from '../lib/reservas'

export default function Ticket() {
  const { codigo = '' } = useParams()
  const [ticket, setTicket] = useState<TicketElectronico | null>(null)
  const [error, setError] = useState('')
  const [errorDescarga, setErrorDescarga] = useState('')
  const [descargando, setDescargando] = useState(false)

  useEffect(() => {
    getTicket(codigo)
      .then(setTicket)
      .catch((e: Error) => setError(e.message))
  }, [codigo])

  if (!ticket && !error) return <EsqueletoPagina angosta />
  if (!ticket)
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <h1 className="text-3xl font-extrabold text-marino">No encontramos el ticket</h1>
        <p role="alert" className="mt-4 text-sm font-medium text-red-700">{error}</p>
        <Link to="/reservas" className="mt-6 inline-block font-bold text-cielo hover:underline">Volver a mis reservas</Link>
      </main>
    )

  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <article className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <header className="bg-marino px-6 py-6 text-white sm:px-8">
          <p className="text-sm font-bold uppercase tracking-widest text-sky-300">Fly Away - Ticket electrónico</p>
          <h1 className="mt-2 text-3xl font-extrabold">Ticket de {ticket.nombre_pasajero} {ticket.apellido_pasajero}</h1>
          <p className="mt-2 font-mono text-sm">{ticket.codigo_pasaje}</p>
        </header>

        <dl className="grid gap-x-8 gap-y-6 p-6 sm:grid-cols-2 sm:p-8">
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Pasajero</dt>
            <dd className="mt-1 font-semibold text-marino">{ticket.nombre_pasajero} {ticket.apellido_pasajero}</dd>
            <dd className="text-sm text-slate-600">DNI {ticket.dni_pasajero}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Vuelo</dt>
            <dd className="mt-1 font-semibold text-marino">{ticket.vuelo.numero_vuelo}</dd>
            <dd className="text-sm text-slate-600">Clase {NOMBRE_CLASE[ticket.clase]}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Origen</dt>
            <dd className="mt-1 text-2xl font-extrabold text-marino">{ticket.vuelo.origen}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Destino</dt>
            <dd className="mt-1 text-2xl font-extrabold text-marino">{ticket.vuelo.destino}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Salida</dt>
            <dd className="mt-1 font-semibold text-marino">
              {fechaCorta(ticket.vuelo.fecha_operacion)} - {hora(ticket.vuelo.hora_partida)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Llegada</dt>
            <dd className="mt-1 font-semibold text-marino">
              {fechaCorta(ticket.vuelo.fecha_llegada)} - {hora(ticket.vuelo.hora_llegada)}
            </dd>
          </div>
          {ticket.asiento && (
            <div>
              <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Asiento</dt>
              <dd className="mt-1 font-semibold text-marino">{ticket.asiento}</dd>
            </div>
          )}
          <div>
            <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Estado de compra</dt>
            <dd className="mt-1 font-semibold text-green-700">Confirmada</dd>
          </div>
        </dl>

        <footer className="flex flex-col gap-3 border-t border-slate-100 p-6 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <Link to="/reservas" className="font-bold text-cielo hover:underline">Volver a mis reservas</Link>
          <div>
            {errorDescarga && <p role="alert" className="mb-2 text-sm font-medium text-red-700">{errorDescarga}</p>}
            <button
              type="button"
              disabled={descargando}
              onClick={() => {
                setDescargando(true)
                setErrorDescarga('')
                descargarTicket(ticket.codigo_pasaje)
                  .catch((e: Error) => setErrorDescarga(e.message))
                  .finally(() => setDescargando(false))
              }}
              className="rounded-xl bg-naranja px-5 py-2.5 font-bold text-white hover:bg-naranja/90 disabled:opacity-60"
            >
              {descargando ? 'Preparando PDF…' : 'Descargar ticket PDF'}
            </button>
          </div>
        </footer>
      </article>
    </main>
  )
}
