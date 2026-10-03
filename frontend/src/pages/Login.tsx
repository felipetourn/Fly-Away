import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { inicioPorRol } from '../lib/auth'
import { useSesion } from '../lib/sesion'

export default function Login() {
  const { usuario, login, cargando } = useSesion()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (cargando) return <main className="mx-auto max-w-md px-4 py-16" aria-busy="true">Cargando sesión…</main>
  if (usuario) return <Navigate to={inicioPorRol(usuario.rol)} replace />

  const enviar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setEnviando(true)
    try {
      const actual = await login(email, password)
      navigate(inicioPorRol(actual.rol), { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo iniciar sesión.')
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
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20"
          />
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
