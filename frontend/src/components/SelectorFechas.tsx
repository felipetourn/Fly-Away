import { useEffect, useRef, useState } from 'react'
import { DayPicker } from 'react-day-picker'
import { es } from 'react-day-picker/locale'
import 'react-day-picker/style.css'
import { elegirDia } from '../lib/busqueda'
import { rangoCorto } from '../lib/formato'

interface Props {
  id: string
  etiqueta: string
  /** YYYY-MM-DD; '' = sin elegir. `hasta` '' = un solo día. */
  desde: string
  hasta: string
  /** Primer día elegible (YYYY-MM-DD). */
  min: string
  placeholder: string
  invalido: boolean
  /** id del mensaje de error, para aria-describedby. */
  idError: string
  onChange: (desde: string, hasta: string) => void
}

// Hora local, no UTC (ver formato.ts).
const aFecha = (iso: string) => new Date(`${iso}T00:00:00`)
const aISO = (d: Date) => d.toLocaleDateString('sv-SE')

/** Caja con un calendario desplegable: primer clic = inicio del rango, segundo clic = fin. */
export default function SelectorFechas(p: Props) {
  const [abierto, setAbierto] = useState(false)
  // true entre el primer y el segundo clic.
  const [esperandoFin, setEsperandoFin] = useState(false)
  const raiz = useRef<HTMLDivElement>(null)
  const boton = useRef<HTMLButtonElement>(null)

  function cerrar(devolverFoco: boolean) {
    setAbierto(false)
    if (devolverFoco) boton.current?.focus()
  }

  useEffect(() => {
    if (!abierto) return
    const afuera = (e: PointerEvent) => {
      if (!raiz.current?.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener('pointerdown', afuera)
    return () => document.removeEventListener('pointerdown', afuera)
  }, [abierto])

  function elegir(dia: Date) {
    const r = elegirDia({ desde: p.desde, hasta: p.hasta, abierto: esperandoFin }, aISO(dia))
    p.onChange(r.desde, r.hasta)
    setEsperandoFin(r.abierto)
    if (!r.abierto) cerrar(true)
  }

  const texto = rangoCorto(p.desde, p.hasta)
  const minimo = aFecha(p.min)
  return (
    <div
      ref={raiz}
      className="relative"
      onKeyDown={(e) => {
        if (e.key === 'Escape' && abierto) {
          e.stopPropagation()
          cerrar(true)
        }
      }}
    >
      <div className="rounded-2xl border border-slate-200 px-4 py-2.5 focus-within:border-cielo">
        <span id={`${p.id}-etiqueta`} className="block text-xs font-semibold text-slate-500">
          {p.etiqueta}
        </span>
        <button
          ref={boton}
          id={p.id}
          type="button"
          onClick={() => {
            setEsperandoFin(false)
            setAbierto((a) => !a)
          }}
          aria-haspopup="dialog"
          aria-expanded={abierto}
          aria-labelledby={`${p.id}-etiqueta ${p.id}`}
          aria-invalid={p.invalido}
          aria-describedby={p.idError}
          className={`w-full text-left font-semibold outline-none ${texto ? '' : 'text-slate-400'}`}
        >
          {texto || p.placeholder}
        </button>
      </div>

      {abierto && (
        <div
          role="dialog"
          aria-label={`${p.etiqueta}: elegí el día de inicio y el de fin`}
          className="absolute left-0 top-full z-50 mt-2 rounded-2xl border border-slate-200 bg-white p-3 shadow-2xl shadow-marino/20"
        >
          <DayPicker
            mode="range"
            locale={es}
            weekStartsOn={1}
            autoFocus
            selected={p.desde ? { from: aFecha(p.desde), to: p.hasta ? aFecha(p.hasta) : aFecha(p.desde) } : undefined}
            onSelect={(_, dia) => elegir(dia)}
            defaultMonth={p.desde ? aFecha(p.desde) : minimo}
            startMonth={minimo}
            disabled={{ before: minimo }}
          />
          <p className="px-2 pt-1 text-xs text-slate-500">
            {esperandoFin ? 'Elegí el día de fin (o el mismo día para uno solo).' : 'Elegí el día de inicio.'}
          </p>
        </div>
      )}
    </div>
  )
}
