import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ApiError } from '../lib/api'
import { useSesion } from '../lib/sesion'

export default function Login() {
  const { usuario, login, cargando } = useSesion()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [verPassword, setVerPassword] = useState(false)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (cargando) return <main className="mx-auto max-w-md px-4 py-16" aria-busy="true">Cargando sesión…</main>
  if (usuario) return <Navigate to="/" replace />

  const enviar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (e) {
      // El backend responde 401 tanto si el email no existe como si la contraseña es incorrecta.
      setError(
        e instanceof ApiError && e.status === 401
          ? 'El email o la contraseña son incorrectos.'
          : 'No se pudo iniciar sesión. Intentá de nuevo en unos minutos.',
      )
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">Iniciar sesión</h1>
      <p className="mt-2 text-slate-600">Ingresá con el email y la contraseña de tu cuenta.</p>
      <form className="mt-8 space-y-5" onSubmit={enviar}>
        <label className="block font-semibold text-slate-700">
          Email
          <input
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20"
          />
        </label>
        <label className="block font-semibold text-slate-700">
          Contraseña
          <span className="relative mt-2 block">
            <input
              type={verPassword ? 'text' : 'password'}
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-white py-3 pr-12 pl-4 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20"
            />
            <button
              type="button"
              onClick={() => setVerPassword((v) => !v)}
              aria-label={verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              aria-pressed={verPassword}
              title={verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              className="absolute inset-y-0 right-0 grid w-12 place-items-center rounded-r-xl text-slate-500 hover:text-marino"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
                <circle cx="12" cy="12" r="3" />
                {!verPassword && <path d="M4 4l16 16" />}
              </svg>
            </button>
          </span>
        </label>
        {error && <p className="text-sm font-medium text-red-700" role="alert">{error}</p>}
        <button
          type="submit"
          disabled={enviando}
          className="w-full rounded-xl bg-marino px-5 py-3 font-bold text-white hover:bg-cielo disabled:cursor-wait disabled:opacity-60"
        >
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate-600">
        ¿No tenés cuenta?{' '}
        <Link to="/registro" className="font-semibold text-marino underline">Registrate</Link>
      </p>
    </main>
  )
}
