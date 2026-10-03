import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import Header from './components/Header'
import { inicioPorRol, type Usuario } from './lib/auth'
import { useSesion } from './lib/sesion'
import Login from './pages/Login'
import Perfil from './pages/Perfil'
import Proximamente from './pages/Proximamente'
import Registro from './pages/Registro'
import Vuelos from './pages/Vuelos'

function RutaProtegida({ roles, children }: { roles: Usuario['rol'][]; children: ReactNode }) {
  const { usuario, cargando } = useSesion()
  if (cargando) return <main className="p-8" aria-busy="true">Cargando sesión…</main>
  if (!usuario) return <Navigate to="/login" replace />
  if (!roles.includes(usuario.rol)) return <Navigate to={inicioPorRol(usuario.rol)} replace />
  return children
}

function LayoutPasajero() {
  return (
    <>
      <Header />
      <Outlet />
    </>
  )
}

// Una ruta raíz por tipo de usuario (misma UI, distintas funcionalidades).
export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      <Routes>
        <Route element={<LayoutPasajero />}>
          <Route index element={<Vuelos />} />
          <Route path="reservas" element={<RutaProtegida roles={['pasajero']}><Proximamente titulo="Mis reservas" /></RutaProtegida>} />
          <Route path="perfil" element={<RutaProtegida roles={['pasajero', 'empleado_mostrador', 'administrador']}><Perfil /></RutaProtegida>} />
          <Route path="login" element={<Login />} />
          <Route path="registro" element={<Registro />} />
        </Route>
        <Route path="/mostrador/*" element={<RutaProtegida roles={['empleado_mostrador']}><h1 className="p-8 text-2xl">Mostrador</h1></RutaProtegida>} />
        <Route path="/admin/*" element={<RutaProtegida roles={['administrador']}><h1 className="p-8 text-2xl">Administración</h1></RutaProtegida>} />
      </Routes>
    </div>
  )
}
