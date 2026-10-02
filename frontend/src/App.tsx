import { Outlet, Route, Routes } from 'react-router-dom'
import Header from './components/Header'
import Login from './pages/Login'
import Perfil from './pages/Perfil'
import Proximamente from './pages/Proximamente'
import Vuelos from './pages/Vuelos'

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
          <Route path="reservas" element={<Proximamente titulo="Mis reservas" />} />
          <Route path="perfil" element={<Perfil />} />
          <Route path="login" element={<Login />} />
          <Route path="registro" element={<Proximamente titulo="Registrarse" />} />
        </Route>
        <Route path="/mostrador/*" element={<h1 className="p-8 text-2xl">Mostrador</h1>} />
        <Route path="/admin/*" element={<h1 className="p-8 text-2xl">Administración</h1>} />
      </Routes>
    </div>
  )
}
