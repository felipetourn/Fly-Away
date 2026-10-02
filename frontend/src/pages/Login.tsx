import { Link, useNavigate } from 'react-router-dom'
import { useSesion } from '../lib/sesion'
import Proximamente from './Proximamente'

export default function Login() {
  const { loginDemo } = useSesion()
  const navigate = useNavigate()
  return (
    <Proximamente titulo="Iniciar sesión">
      <button
        type="button"
        onClick={() => {
          loginDemo()
          navigate('/')
        }}
        className="rounded-xl bg-marino px-5 py-2.5 font-bold text-white hover:bg-cielo"
      >
        Entrar (demo)
      </button>
      <p className="mt-4 text-sm text-slate-500">
        ¿No tenés cuenta?{' '}
        <Link to="/registro" className="font-semibold text-marino underline">
          Registrate
        </Link>
      </p>
    </Proximamente>
  )
}
