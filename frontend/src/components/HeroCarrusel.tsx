import { useEffect, useState } from 'react'

// Orden de aparición y texto de la esquina ('' = sin texto).
const FOTOS: [archivo: string, lugar: string][] = [
  ['perito-moreno.jpg', 'Glaciar Perito Moreno, El Calafate'],
  ['ushuaia.jpg', 'Faro Les Éclaireurs, Ushuaia'],
  ['hornocal.jpg', 'Serranía de Hornocal, Humahuaca, Jujuy'],
  ['obelisco.jpg', 'Obelisco, Buenos Aires'],
  ['bariloche-1.jpg', 'San Carlos de Bariloche, Río Negro'],
  ['cafayate.jpg', 'Cafayate, Salta'],
  ['caminito.jpg', 'Caminito, Buenos Aires'],
  ['bariloche-2.jpg', 'San Carlos de Bariloche, Río Negro'],
  ['guanacos.jpg', ''],
  ['casa-rosada.jpg', 'Casa Rosada, Buenos Aires'],
  ['floralis-generica.jpg', 'Floralis Genérica, Buenos Aires'],
]

export default function HeroCarrusel() {
  const [actual, setActual] = useState(0)

  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => setActual((i) => (i + 1) % FOTOS.length), 6000)
    return () => clearInterval(id)
  }, [])

  return (
    <section className="relative h-[62vh] min-h-[420px] overflow-hidden bg-marino">
      <div aria-hidden="true">
        {FOTOS.map(([archivo], i) => (
          <img
            key={archivo}
            src={`/destinos/${archivo}`}
            alt=""
            fetchPriority={i === 0 ? 'high' : 'low'}
            className={`slide absolute inset-0 h-full w-full object-cover ${i === actual ? 'on' : ''}`}
          />
        ))}
      </div>
      <div className="absolute inset-0 bg-linear-to-b from-marino/60 via-marino/25 to-marino/70" />
      <div className="relative mx-auto flex h-full max-w-[88rem] flex-col justify-center px-4 pb-24">
        <p className="mb-3 text-sm font-semibold tracking-[0.2em] text-ambar uppercase">Volá por toda la Argentina</p>
        <h1 className="text-4xl leading-tight font-extrabold text-white md:text-6xl md:whitespace-nowrap">
          ¿A dónde querés ir?
        </h1>
      </div>
      <p aria-hidden="true" className="absolute right-4 bottom-24 text-xs font-medium text-white/80 md:right-8">
        {FOTOS[actual][1]}
      </p>
    </section>
  )
}
