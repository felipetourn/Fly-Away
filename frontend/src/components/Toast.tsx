import { useEffect, useRef } from 'react'
import type { Aviso } from '../lib/pagos'

const DURACION_MS = 6000
const TONO = {
  ok: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-700',
}

/** Aviso que se va solo a los 6 s; también se cierra con ✕. */
export default function Toast({ aviso, onCerrar }: { aviso: Aviso; onCerrar: () => void }) {
  // En un ref: si el padre pasa una función nueva en cada render, el temporizador no se reinicia.
  const cerrar = useRef(onCerrar)
  useEffect(() => {
    cerrar.current = onCerrar
  })

  useEffect(() => {
    const id = setTimeout(() => cerrar.current(), DURACION_MS)
    return () => clearTimeout(id)
  }, [aviso])

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed inset-x-4 bottom-4 z-50 flex items-start gap-3 rounded-2xl border p-4 text-sm font-medium shadow-lg sm:inset-x-auto sm:right-4 sm:max-w-sm ${TONO[aviso.tono]}`}
    >
      <p className="flex-1">{aviso.texto}</p>
      <button
        type="button"
        onClick={() => cerrar.current()}
        aria-label="Cerrar aviso"
        className="-m-1 grid h-7 w-7 shrink-0 place-items-center rounded-full hover:bg-black/5"
      >
        ✕
      </button>
    </div>
  )
}
