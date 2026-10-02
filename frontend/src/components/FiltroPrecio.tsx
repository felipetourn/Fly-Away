import { useState, type FormEvent } from 'react'
import { NOMBRE_CLASE, validarPrecio, type Clase } from '../lib/busqueda'

interface Props {
  min: number | null
  max: number | null
  clase: Clase
  onAplicar: (min: number | null, max: number | null) => void
}

const aMonto = (texto: string) => (texto.trim() === '' ? null : Number(texto))
const campo =
  'flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 focus-within:border-cielo'

/** Rango de precio por persona. Lee `min`/`max` al montar: el que lo usa le pasa una `key` que cambia con ellos. */
export default function FiltroPrecio({ min, max, clase, onAplicar }: Props) {
  const [desde, setDesde] = useState(min === null ? '' : String(min))
  const [hasta, setHasta] = useState(max === null ? '' : String(max))
  const [error, setError] = useState<string>()

  function aplicar(e: FormEvent) {
    e.preventDefault()
    const nuevoMin = aMonto(desde)
    const nuevoMax = aMonto(hasta)
    const mensaje = validarPrecio(nuevoMin, nuevoMax)
    setError(mensaje)
    if (!mensaje) onAplicar(nuevoMin, nuevoMax)
  }

  return (
    <form
      onSubmit={aplicar}
      noValidate
      className="mb-8 flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm"
    >
      <span className="font-semibold text-marino">Precio por persona · {NOMBRE_CLASE[clase]}</span>
      <label className={campo}>
        <span className="text-slate-400">$</span>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          step={1000}
          placeholder="Mínimo"
          aria-label="Precio mínimo"
          value={desde}
          onChange={(e) => setDesde(e.target.value)}
          className="w-28 bg-transparent font-semibold outline-none"
        />
      </label>
      <span className="text-slate-400" aria-hidden="true">
        –
      </span>
      <label className={campo}>
        <span className="text-slate-400">$</span>
        <input
          type="number"
          inputMode="numeric"
          min={0}
          step={1000}
          placeholder="Máximo"
          aria-label="Precio máximo"
          value={hasta}
          onChange={(e) => setHasta(e.target.value)}
          className="w-28 bg-transparent font-semibold outline-none"
        />
      </label>
      <button type="submit" className="rounded-xl bg-marino px-4 py-2 font-bold text-white hover:bg-cielo">
        Aplicar
      </button>
      {(min !== null || max !== null) && (
        <button
          type="button"
          onClick={() => onAplicar(null, null)}
          className="font-bold text-cielo hover:underline"
        >
          Limpiar
        </button>
      )}
      {error && <p className="w-full text-xs font-medium text-red-600">{error}</p>}
    </form>
  )
}
