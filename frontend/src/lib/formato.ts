// Hora local, no UTC: new Date('2026-10-26') sería el 25 en Argentina.
const aFecha = (iso: string) => new Date(`${iso}T00:00:00`)
const mayuscula = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/** "Lunes, 26 de octubre" */
export function fechaLarga(iso: string): string {
  return mayuscula(aFecha(iso).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' }))
}

/** "Lun, 26 oct" */
export function fechaCorta(iso: string): string {
  return mayuscula(aFecha(iso).toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' }))
}

/** "Martes, 20 de octubre de 2026" */
export function fechaCompleta(iso: string): string {
  return mayuscula(
    aFecha(iso).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
  )
}

/** "Del 20 de octubre al 25 de octubre" */
export function rangoFechas(desde: string, hasta: string): string {
  const diaMes = (iso: string) => aFecha(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long' })
  return `Del ${diaMes(desde)} al ${diaMes(hasta)}`
}

/** Etiqueta del selector de fechas: "26 oct" o "26 oct – 28 oct"; '' sin fecha. */
export function rangoCorto(desde: string, hasta: string): string {
  const diaMes = (iso: string) => aFecha(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })
  if (!desde) return ''
  return hasta ? `${diaMes(desde)} – ${diaMes(hasta)}` : diaMes(desde)
}

/** "06:40:00" → "06:40" */
export function hora(t: string): string {
  return t.slice(0, 5)
}

/** 175512 → "$ 175.512" */
export function precio(n: number): string {
  return `$ ${Math.round(n).toLocaleString('es-AR')}`
}

/** 85 → "1 h 25 m" */
export function duracion(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h} h ${m} m` : `${h} h`
}
