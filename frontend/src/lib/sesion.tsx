import { createContext, use, useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import { CLAVE_REFRESH, CLAVE_TOKEN, type Usuario } from './auth.ts'

interface Sesion {
  usuario: Usuario | null
  cargando: boolean
  login: (email: string, password: string) => Promise<Usuario>
  registrarse: (datos: DatosRegistro) => Promise<Usuario>
  logout: () => void
}

export interface DatosRegistro {
  email: string
  nombre: string
  apellido: string
  password: string
}

interface Tokens {
  access: string
  refresh: string
}

const SesionContext = createContext<Sesion | null>(null)

export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [cargando, setCargando] = useState(() => Boolean(localStorage.getItem(CLAVE_TOKEN)))

  useEffect(() => {
    const token = localStorage.getItem(CLAVE_TOKEN)
    if (!token) return
    api<Usuario>('/api/auth/yo/')
      .then(setUsuario)
      .catch(() => {
        localStorage.removeItem(CLAVE_TOKEN)
        localStorage.removeItem(CLAVE_REFRESH)
      })
      .finally(() => setCargando(false))
  }, [])

  const login = async (email: string, password: string) => {
    const tokens = await api<Tokens>('/api/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    localStorage.setItem(CLAVE_TOKEN, tokens.access)
    localStorage.setItem(CLAVE_REFRESH, tokens.refresh)
    try {
      const actual = await api<Usuario>('/api/auth/yo/')
      setUsuario(actual)
      return actual
    } catch (error) {
      localStorage.removeItem(CLAVE_TOKEN)
      localStorage.removeItem(CLAVE_REFRESH)
      throw error
    }
  }

  const registrarse = async (datos: DatosRegistro) => {
    await api<Usuario>('/api/auth/registro/', {
      method: 'POST',
      body: JSON.stringify(datos),
    })
    return login(datos.email, datos.password)
  }

  const logout = () => {
    localStorage.removeItem(CLAVE_TOKEN)
    localStorage.removeItem(CLAVE_REFRESH)
    setUsuario(null)
  }

  return <SesionContext value={{ usuario, cargando, login, registrarse, logout }}>{children}</SesionContext>
}

export function useSesion(): Sesion {
  const sesion = use(SesionContext)
  if (!sesion) throw new Error('useSesion se usa dentro de <SesionProvider>')
  return sesion
}
