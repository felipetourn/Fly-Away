import { NOMBRE_CLASE, porcentaje, type Ocupacion } from '../lib/ocupacion'

const numero = (n: number) => n.toLocaleString('es-AR')

function Cifra({ titulo, valor }: { titulo: string; valor: number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold text-slate-500 uppercase">{titulo}</p>
      <p className="mt-1 text-3xl font-extrabold text-marino">{numero(valor)}</p>
    </div>
  )
}

/** Barra de vendidos sobre la capacidad. */
export function BarraOcupacion({ vendidos, capacidad, etiqueta, chica = false }: { vendidos: number; capacidad: number; etiqueta: string; chica?: boolean }) {
  return (
    <div role="img" aria-label={etiqueta} className={`overflow-hidden rounded-full bg-slate-100 ${chica ? 'h-1.5 w-20' : 'h-3 w-full'}`}>
      <div className="h-full rounded-full bg-marino" style={{ width: `${porcentaje(vendidos, capacidad)}%` }} />
    </div>
  )
}

/**
 * Capacidad, vendidos y disponibles del total y de cada clase. Solo muestra: los datos los trae la pantalla
 * (administrador: `getOcupacion`; la US14 puede usarlo con los suyos).
 */
export default function OcupacionVuelo({ ocupacion }: { ocupacion: Ocupacion }) {
  const { total, clases } = ocupacion
  return (
    <section aria-label="Ocupación">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Cifra titulo="Capacidad" valor={total.capacidad} />
        <Cifra titulo="Vendidos" valor={total.vendidos} />
        <Cifra titulo="Disponibles" valor={total.disponibles} />
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="text-xs font-semibold text-slate-500 uppercase">Ocupación</p>
          <p className="mt-1 text-3xl font-extrabold text-marino">{porcentaje(total.vendidos, total.capacidad)}%</p>
        </div>
      </div>
      <ul className="mt-3 space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
        {clases.map((c) => (
          <li key={c.clase}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <p className="font-bold text-marino">{NOMBRE_CLASE[c.clase]}</p>
              <p className="text-sm text-slate-600">
                {numero(c.vendidos)} vendidos · {numero(c.disponibles)} disponibles de {numero(c.capacidad)} ·{' '}
                <span className="font-bold text-slate-900">{porcentaje(c.vendidos, c.capacidad)}%</span>
              </p>
            </div>
            <div className="mt-2">
              <BarraOcupacion vendidos={c.vendidos} capacidad={c.capacidad} etiqueta={`${NOMBRE_CLASE[c.clase]}: ${c.vendidos} de ${c.capacidad} vendidos`} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
