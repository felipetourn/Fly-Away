import { createContext, use, useState, type ReactNode } from 'react'
import { CLAVE_TOKEN, usuarioActual, type Usuario } from './auth.ts'

interface Sesion {
  usuario: Usuario | null
  loginDemo: () => void
  logout: () => void
}

const SesionContext = createContext<Sesion | null>(null)

export function SesionProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState(usuarioActual)

  const loginDemo = () => {
    localStorage.setItem(CLAVE_TOKEN, 'demo')
    setUsuario(usuarioActual())
  }
  const logout = () => {
    localStorage.removeItem(CLAVE_TOKEN)
    localStorage.removeItem('refresh')
    setUsuario(null)
  }

  return <SesionContext value={{ usuario, loginDemo, logout }}>{children}</SesionContext>
}

export function useSesion(): Sesion {
  const sesion = use(SesionContext)
  if (!sesion) throw new Error('useSesion se usa dentro de <SesionProvider>')
  return sesion
}
