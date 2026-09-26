import { Route, Routes } from 'react-router-dom'

// Una ruta raíz por tipo de usuario (misma UI, distintas funcionalidades).
export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Routes>
        <Route path="/" element={<h1 className="p-8 text-3xl font-bold">Fly Away ✈️</h1>} />
        <Route path="/mostrador/*" element={<h1 className="p-8 text-2xl">Mostrador</h1>} />
        <Route path="/admin/*" element={<h1 className="p-8 text-2xl">Administración</h1>} />
      </Routes>
    </div>
  )
}
