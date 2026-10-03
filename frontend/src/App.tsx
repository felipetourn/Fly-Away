import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import Header from './components/Header'
import type { Usuario } from './lib/auth'
import { useSesion } from './lib/sesion'
import AdminVueloForm from './pages/AdminVueloForm'
import AdminVuelos from './pages/AdminVuelos'
import Login from './pages/Login'
import Perfil from './pages/Perfil'
import Proximamente from './pages/Proximamente'
import Registro from './pages/Registro'
import Vuelos from './pages/Vuelos'

function RutaProtegida({ roles, children }: { roles: Usuario['rol'][]; children: ReactNode }) {
  const { usuario, cargando } = useSesion()
  if (cargando) return <main className="p-8" aria-busy="true">Cargando sesión…</main>
  if (!usuario) return <Navigate to="/login" replace />
  if (!roles.includes(usuario.rol)) return <Navigate to="/" replace />
  return children
}

function Layout() {
  return (
    <>
      <Header />
      <div className="flex-1">
        <Outlet />
      </div>
      <footer className="border-t border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500">
        Antonio Sevenants y Felipe Tourn
      </footer>
    </>
  )
}

// Mismo layout para todos; el header muestra las opciones del rol (MENU en lib/auth).
export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 font-sans text-slate-900">
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Vuelos />} />
          <Route path="reservas" element={<RutaProtegida roles={['pasajero']}><Proximamente titulo="Mis reservas" /></RutaProtegida>} />
          <Route path="perfil" element={<RutaProtegida roles={['pasajero', 'empleado_mostrador', 'administrador']}><Perfil /></RutaProtegida>} />
          <Route path="login" element={<Login />} />
          <Route path="registro" element={<Registro />} />
          <Route path="empleado/reservas" element={<RutaProtegida roles={['empleado_mostrador']}><Proximamente titulo="Reservas" /></RutaProtegida>} />
          <Route path="admin/reservas" element={<RutaProtegida roles={['administrador']}><Proximamente titulo="Reservas" /></RutaProtegida>} />
          <Route path="admin/vuelos" element={<RutaProtegida roles={['administrador']}><AdminVuelos /></RutaProtegida>} />
          <Route path="admin/vuelos/nuevo" element={<RutaProtegida roles={['administrador']}><AdminVueloForm /></RutaProtegida>} />
          <Route path="admin/vuelos/:id" element={<RutaProtegida roles={['administrador']}><AdminVueloForm /></RutaProtegida>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </div>
  )
}
