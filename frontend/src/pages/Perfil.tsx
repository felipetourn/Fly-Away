import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ChipEstado from '../components/ChipEstado'
import { Esqueleto } from '../components/Esqueleto'
import { iniciales, type Usuario } from '../lib/auth'
import { fechaDeInstante, precio } from '../lib/formato'
import { getPagos, medioDePago, vueloCorto, type Pago } from '../lib/pagos'
import { useSesion } from '../lib/sesion'

// El pasajero no muestra rol.
const ETIQUETA_ROL: Partial<Record<Usuario['rol'], string>> = {
  empleado_mostrador: 'Empleado',
  administrador: 'Admin',
}

function MisPagos() {
  const [pagos, setPagos] = useState<Pago[] | null>(null)
  const [error, setError] = useState('')

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
        <ul className="mt-4 divide-y divide-slate-100">
          {pagos.map((p) => (
            <li key={p.id}>
              <Link
                to={`/pagos/${p.id}`}
                className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 rounded-lg px-2 py-3 hover:bg-slate-50 sm:grid-cols-[7rem_1fr_auto_auto]"
              >
                <span className="text-sm text-slate-500">{fechaDeInstante(p.creado_en)}</span>
                <span className="col-start-1 font-medium sm:col-start-auto">
                  {p.vuelo ? vueloCorto(p.vuelo) : 'Reserva'}
                  <span className="block text-sm font-normal text-slate-500">{medioDePago(p)}</span>
                </span>
                <span className="row-start-1 text-right font-bold sm:row-start-auto">{precio(Number(p.monto))}</span>
                <span className="text-right">
                  <ChipEstado estado={p.estado} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
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
    <main className="mx-auto grid max-w-5xl items-start gap-6 px-4 py-16 md:grid-cols-[20rem_1fr]">
      {tarjeta}
      <MisPagos />
    </main>
  )
}
