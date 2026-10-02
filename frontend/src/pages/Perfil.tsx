import { Link, useNavigate } from 'react-router-dom'
import { useSesion } from '../lib/sesion'
import Proximamente from './Proximamente'

export default function Perfil() {
  const { usuario, logout } = useSesion()
  const navigate = useNavigate()

  if (!usuario) {
    return (
      <Proximamente titulo="Mi perfil">
        <Link to="/login" className="font-semibold text-marino underline">
          Iniciá sesión
        </Link>{' '}
        para ver tu perfil.
      </Proximamente>
    )
  }

  return (
    <Proximamente titulo={`${usuario.nombre} ${usuario.apellido}`}>
      <p className="mb-4 text-slate-500">{usuario.email}</p>
      <button
        type="button"
        onClick={() => {
          logout()
          navigate('/')
        }}
        className="rounded-xl border border-slate-300 px-5 py-2.5 font-bold text-marino hover:bg-white"
      >
        Cerrar sesión
      </button>
    </Proximamente>
  )
}
