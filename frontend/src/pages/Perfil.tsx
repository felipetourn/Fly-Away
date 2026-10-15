import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import DetalleVuelo from '../components/DetalleVuelo'
import LogoMedio from '../components/LogoMedio'
import { Esqueleto } from '../components/Esqueleto'
import { iniciales, type Usuario } from '../lib/auth'
import { fechaDeInstante, precio } from '../lib/formato'
import { cuentaDelPago, getPagos, type Pago } from '../lib/pagos'
import { getVuelo, type Vuelo } from '../lib/vuelos'
import { useSesion } from '../lib/sesion'

// El pasajero no muestra rol.
const ETIQUETA_ROL: Partial<Record<Usuario['rol'], string>> = {
  empleado_mostrador: 'Empleado',
  administrador: 'Admin',
}

function MisPagos() {
  const [pagos, setPagos] = useState<Pago[] | null>(null)
  const [error, setError] = useState('')
  // Vuelo cuyo detalle está abierto (null = diálogo cerrado). El comprobante del pago llega con la US09.
  const [vuelo, setVuelo] = useState<Vuelo | null>(null)

  const verVuelo = (id: string) => {
    setError('')
    getVuelo(id)
      .then(setVuelo)
      .catch((e: Error) => setError(e.message))
  }

  useEffect(() => {
    getPagos()
      .then(setPagos)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-extrabold text-marino">Mis pagos</h2>
      {error && <p role="alert" className="mt-4 text-sm font-medium text-red-700">{error}</p>}
      {!pagos && !error && (
        <div className="mt-4 space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => <Esqueleto key={i} className="h-14 w-full" />)}
        </div>
      )}
      {pagos?.length === 0 && (
        <p className="mt-4 text-slate-500">
          Todavía no hiciste pagos. <Link to="/reservas" className="font-bold text-cielo hover:underline">Ir a mis reservas</Link>
        </p>
      )}
      {pagos && pagos.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-slate-200 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-3 py-2 text-left font-bold">Medio</th>
                <th className="px-3 py-2 text-left font-bold">Tarjeta o cuenta</th>
                <th className="px-3 py-2 text-left font-bold">Fecha</th>
                <th className="px-3 py-2 text-left font-bold">Vuelo</th>
                <th className="px-3 py-2 text-left font-bold">Valor</th>
                <th className="px-3 py-2 text-left font-bold">Estado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pagos.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-3 py-3">
                    <LogoMedio pago={p} />
                  </td>
                  <td className="px-3 py-3 break-all">{cuentaDelPago(p)}</td>
                  <td className="px-3 py-3 whitespace-nowrap text-slate-500">{fechaDeInstante(p.creado_en)}</td>
                  <td className="px-3 py-3">
                    {p.vuelo ? (
                      <button
                        type="button"
                        onClick={() => verVuelo(p.vuelo!.id)}
                        className="text-left font-medium whitespace-nowrap text-marino hover:underline"
                      >
                        <span className="block">{p.vuelo.numero_vuelo}</span>
                        <span className="block text-slate-500">
                          {p.vuelo.origen} → {p.vuelo.destino}
                        </span>
                      </button>
                    ) : (
                      'Reserva'
                    )}
                  </td>
                  <td className="px-3 py-3 font-bold whitespace-nowrap">{precio(Number(p.monto))}</td>
                  <td className="px-3 py-3">
                    <ChipEstado estado={p.estado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {vuelo && <DetalleVuelo key={vuelo.id} vuelo={vuelo} onCerrar={() => setVuelo(null)} />}
    </section>
  )
}

export default function Perfil() {
  const { usuario, logout } = useSesion()
  const navigate = useNavigate()

  // La ruta ya exige sesión (RutaProtegida).
  if (!usuario) return null

  const rol = ETIQUETA_ROL[usuario.rol]
  const esPasajero = usuario.rol === 'pasajero'

  const tarjeta = (
    <div className="flex flex-col items-center rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
      <div
        aria-hidden="true"
        className="grid h-24 w-24 place-items-center rounded-full bg-linear-to-br from-naranja to-ambar text-3xl font-bold text-white shadow ring-4 ring-white"
      >
        {iniciales(usuario)}
      </div>
      <h1 className="mt-5 text-2xl font-extrabold text-marino">
        {usuario.nombre} {usuario.apellido}
      </h1>
      {rol && (
        <p className="mt-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-bold tracking-wide text-marino uppercase">
          {rol}
        </p>
      )}
      <p className="mt-3 break-all text-slate-500">{usuario.email}</p>
      <p className="mt-1 font-mono text-xs break-all text-slate-400">ID - {usuario.id}</p>
      <button
        type="button"
        onClick={() => {
          logout()
          navigate('/')
        }}
        className="mt-8 w-full rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-slate-50"
      >
        Cerrar sesión
      </button>
    </div>
  )

  if (!esPasajero) return <main className="mx-auto max-w-md px-4 py-16">{tarjeta}</main>

  return (
    <main className="mx-auto max-w-5xl space-y-8 px-4 py-16">
      <div className="mx-auto max-w-md">{tarjeta}</div>
      <MisPagos />
    </main>
  )
}
