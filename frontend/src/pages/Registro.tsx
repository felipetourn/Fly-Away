import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { inicioPorRol } from '../lib/auth'
import { useSesion } from '../lib/sesion'

export default function Registro() {
  const { usuario, registrarse, cargando } = useSesion()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [nombre, setNombre] = useState('')
  const [apellido, setApellido] = useState('')
  const [password, setPassword] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  if (cargando) return <main className="mx-auto max-w-md px-4 py-16" aria-busy="true">Cargando sesión…</main>
  if (usuario) return <Navigate to={inicioPorRol(usuario.rol)} replace />

  const enviar = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    if (password !== confirmacion) {
      setError('Las contraseñas no coinciden.')
      return
    }
    setEnviando(true)
    try {
      const actual = await registrarse({ email, nombre, apellido, password })
      navigate(inicioPorRol(actual.rol), { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo crear la cuenta.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">Crear cuenta de pasajero</h1>
      <p className="mt-2 text-slate-600">Completá tus datos para registrarte.</p>
      <form className="mt-8 space-y-5" onSubmit={enviar}>
        <label className="block font-semibold text-slate-700">
          Nombre
          <input required autoComplete="given-name" value={nombre} onChange={(event) => setNombre(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20" />
        </label>
        <label className="block font-semibold text-slate-700">
          Apellido
          <input required autoComplete="family-name" value={apellido} onChange={(event) => setApellido(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20" />
        </label>
        <label className="block font-semibold text-slate-700">
          Email
          <input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20" />
        </label>
        <label className="block font-semibold text-slate-700">
          Contraseña
          <input type="password" required autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20" />
        </label>
        <label className="block font-semibold text-slate-700">
          Repetir contraseña
          <input type="password" required autoComplete="new-password" value={confirmacion} onChange={(event) => setConfirmacion(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20" />
        </label>
        {error && <p className="text-sm font-medium text-red-700" role="alert">{error}</p>}
        <button type="submit" disabled={enviando} className="w-full rounded-xl bg-marino px-5 py-3 font-bold text-white hover:bg-cielo disabled:cursor-wait disabled:opacity-60">
          {enviando ? 'Creando cuenta…' : 'Crear cuenta'}
        </button>
      </form>
      <p className="mt-6 text-sm text-slate-600">
        ¿Ya tenés cuenta? <Link to="/login" className="font-semibold text-marino underline">Iniciá sesión</Link>
      </p>
    </main>
  )
}
