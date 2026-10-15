/** Barra de espera: el avión naranja de las cards de vuelo cruza la línea de punta a punta. */
export default function AvionCargando({ texto, detalle }: { texto: string; detalle?: string }) {
  return (
    <div role="status" aria-live="polite" className="py-8 text-center">
      <div className="relative mx-auto h-px w-full max-w-sm bg-slate-300">
        <span
          aria-hidden="true"
          className="avion-vuela absolute top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white px-1 text-2xl leading-none text-naranja"
        >
          ✈
        </span>
      </div>
      <p className="mt-6 font-bold text-marino">{texto}</p>
      {detalle && <p className="mt-1 text-sm text-slate-500">{detalle}</p>}
    </div>
  )
}
