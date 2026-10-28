import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EsqueletoPagina } from '../components/Esqueleto'
import OcupacionVuelo from '../components/OcupacionVuelo'
import { ApiError } from '../lib/api'
import { fechaCorta, hora } from '../lib/formato'
import { getOcupacion, type OcupacionDeVuelo } from '../lib/ocupacion'
import { llegaAlDiaSiguiente } from '../lib/vuelos'

/** Ocupación de una instancia de vuelo (US12). Se llega desde el ícono de barras de Gestión de vuelos. */
export default function AdminOcupacionVuelo() {
  const { id = '' } = useParams()
  const [resultado, setResultado] = useState<{ id: string; datos: OcupacionDeVuelo | null; error: string; noExiste: boolean } | null>(null)

  useEffect(() => {
    let vigente = true
    getOcupacion(id).then(
      (datos) => {
        if (vigente) setResultado({ id, datos, error: '', noExiste: false })
      },
      (e) => {
        if (!vigente) return
        const noExiste = e instanceof ApiError && e.status === 404
        setResultado({ id, datos: null, error: e instanceof Error ? e.message : 'No pudimos cargar la ocupación.', noExiste })
      },
    )
    return () => {
      vigente = false
    }
  }, [id])

  if (!resultado || resultado.id !== id) return <EsqueletoPagina />

  const volver = (
    <Link to="/admin/vuelos" className="font-bold text-cielo hover:underline">
      ← Gestión de vuelos
    </Link>
  )
  const { datos, error, noExiste } = resultado
  if (!datos)
    return (
      <main className="mx-auto max-w-4xl px-4 py-8">
        {volver}
        <h1 className="mt-4 text-3xl font-extrabold text-marino">{noExiste ? 'No encontramos el vuelo' : 'Ocupación del vuelo'}</h1>
        {!noExiste && <p role="alert" className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</p>}
      </main>
    )

  const { vuelo } = datos
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      {volver}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <h1 className="text-3xl font-extrabold text-marino">Ocupación del {vuelo.numero_vuelo}</h1>
        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${vuelo.estado === 'activo' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
          {vuelo.estado === 'activo' ? 'Activo' : 'Cancelado'}
        </span>
      </div>
      <p className="mt-2 text-slate-600">
        {fechaCorta(vuelo.fecha_operacion)} · {vuelo.origen.ciudad} ({vuelo.origen.codigo_iata}) → {vuelo.destino.ciudad} ({vuelo.destino.codigo_iata}) ·{' '}
        {hora(vuelo.hora_partida)} a {hora(vuelo.hora_llegada)}
        {llegaAlDiaSiguiente(vuelo) && <sup className="ml-0.5 font-bold text-naranja" title="Llega al día siguiente">+1</sup>}
        {' · '}
        {vuelo.avion.matricula} ({vuelo.avion.modelo})
      </p>
      <p className="mt-1 font-mono text-xs break-all text-slate-500">{vuelo.id}</p>

      <div className="mt-6">
        <OcupacionVuelo ocupacion={datos} />
      </div>
      <p className="mt-3 text-sm text-slate-500">Vendidos cuenta solo las compras confirmadas (pago aprobado).</p>
    </main>
  )
}
