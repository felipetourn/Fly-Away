import { useNavigate } from 'react-router-dom'
import { iniciales, type Usuario } from '../lib/auth'
import { useSesion } from '../lib/sesion'

// El pasajero no muestra rol.
const ETIQUETA_ROL: Partial<Record<Usuario['rol'], string>> = {
  empleado_mostrador: 'Empleado',
  administrador: 'Admin',
}

export default function Perfil() {
  const { usuario, logout } = useSesion()
  const navigate = useNavigate()

  // La ruta ya exige sesión (RutaProtegida).
  if (!usuario) return null

  const rol = ETIQUETA_ROL[usuario.rol]

  return (
    <main className="mx-auto max-w-md px-4 py-16">
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
    </main>
  )
}
