import type { Clase } from './busqueda.ts'

// Tipos con la forma de la API (nombres de docs/modelo.dbml).
export interface Aeropuerto {
  id: string
  codigo_iata: string
  nombre: string
  ciudad: string
  pais: string
}

export interface Vuelo {
  id: string
  numero_vuelo: string
  origen: Aeropuerto
  destino: Aeropuerto
  fecha_operacion: string // YYYY-MM-DD
  hora_partida: string // HH:MM:SS
  hora_llegada: string
  precio_economy: string // decimal: DRF lo serializa como string
  precio_primera: string
  asientos_disponibles_economy: number
  asientos_disponibles_primera: number
  estado: 'activo' | 'cancelado'
}

/** `origen` / `destino` '' = cualquiera. `hasta` '' = solo el día `desde`. Precios por persona en `clase`. */
export interface ParamsBusqueda {
  origen: string
  destino: string
  desde: string
  hasta: string
  pasajeros: number
  clase: Clase
  precioMin: number | null
  precioMax: number | null
}

// ponytail: todo lo de abajo es mock. Al conectar el backend:
//   getAeropuertos → api('/aeropuertos/')
//   buscarVuelos   → api(`/vuelos/buscar/?origen=&destino=&desde=&hasta=&pasajeros=&clase=&precio_min=&precio_max=`)
const aeropuerto = (codigo_iata: string, ciudad: string, nombre: string): Aeropuerto => ({
  id: codigo_iata,
  codigo_iata,
  nombre,
  ciudad,
  pais: 'Argentina',
})

const AEROPUERTOS: Aeropuerto[] = [
  aeropuerto('AEP', 'Buenos Aires', 'Aeroparque Jorge Newbery'),
  aeropuerto('EZE', 'Buenos Aires', 'Aeropuerto Internacional Ministro Pistarini'),
  aeropuerto('BHI', 'Bahía Blanca', 'Aeropuerto Comandante Espora'),
  aeropuerto('BRC', 'San Carlos de Bariloche', 'Aeropuerto Teniente Luis Candelaria'),
  aeropuerto('COR', 'Córdoba', 'Aeropuerto Ingeniero Ambrosio Taravella'),
  aeropuerto('MDZ', 'Mendoza', 'Aeropuerto El Plumerillo'),
  aeropuerto('IGR', 'Puerto Iguazú', 'Aeropuerto Cataratas del Iguazú'),
  aeropuerto('USH', 'Ushuaia', 'Aeropuerto Malvinas Argentinas'),
  aeropuerto('FTE', 'El Calafate', 'Aeropuerto Comandante Armando Tola'),
  aeropuerto('SLA', 'Salta', 'Aeropuerto Martín Miguel de Güemes'),
  aeropuerto('JUJ', 'San Salvador de Jujuy', 'Aeropuerto Horacio Guzmán'),
]

const esperar = (ms: number) => new Promise((r) => setTimeout(r, ms))

/** FNV-1a: mismo texto → mismo número. */
function semilla(texto: string): number {
  let h = 2166136261
  for (let i = 0; i < texto.length; i++) h = Math.imul(h ^ texto.charCodeAt(i), 16777619)
  return h >>> 0
}

/** mulberry32: números "al azar" pero repetibles a partir de una semilla. */
function azar(s: number): () => number {
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const dosDigitos = (n: number) => String(n).padStart(2, '0')
const aHora = (min: number) => `${dosDigitos(Math.floor(min / 60))}:${dosDigitos(min % 60)}:00`
const aMinutos = (t: string) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))

/** Vuelos de una ruta y fecha, sin filtrar. Determinístico. Exportado para los chequeos. */
export function generarVuelos(origen: string, destino: string, fecha: string): Vuelo[] {
  const o = AEROPUERTOS.find((a) => a.codigo_iata === origen)
  const d = AEROPUERTOS.find((a) => a.codigo_iata === destino)
  if (!o || !d || o.ciudad === d.ciudad) return []
  const ruta = semilla(`${origen}-${destino}`)
  const r = azar(semilla(`${origen}-${destino}-${fecha}`))
  const duracionMin = 60 + (ruta % 30) * 5 // 1 h a 3 h 25 m, fija por ruta
  const cantidad = Math.floor(r() * 5) // 0 a 4 vuelos ese día
  return Array.from({ length: cantidad }, (_, i): Vuelo => {
    const partida = (6 + i * 4) * 60 + Math.floor(r() * 8) * 15 // de 06:00 a 19:45: siempre llega antes de medianoche
    const economy = Math.round((40000 + duracionMin * 900 + r() * 40000) / 10) * 10
    const numero = `FA ${1000 + (ruta % 90) * 10 + i}`
    return {
      id: `${numero.replace(' ', '')}-${fecha}`,
      numero_vuelo: numero,
      origen: o,
      destino: d,
      fecha_operacion: fecha,
      hora_partida: aHora(partida),
      hora_llegada: aHora(partida + duracionMin),
      precio_economy: economy.toFixed(2),
      precio_primera: (Math.round((economy * 2.2) / 10) * 10).toFixed(2),
      asientos_disponibles_economy: Math.floor(r() * 40),
      asientos_disponibles_primera: Math.floor(r() * 10),
      estado: r() < 0.1 ? 'cancelado' : 'activo',
    }
  })
}

export async function getAeropuertos(): Promise<Aeropuerto[]> {
  await esperar(150)
  return AEROPUERTOS
}

export const precioDe = (v: Vuelo, clase: Clase) => Number(clase === 'economy' ? v.precio_economy : v.precio_primera)

export const asientosDe = (v: Vuelo, clase: Clase) =>
  clase === 'economy' ? v.asientos_disponibles_economy : v.asientos_disponibles_primera

/** Duración en minutos. */
export const duracionDe = (v: Vuelo) => aMinutos(v.hora_llegada) - aMinutos(v.hora_partida)

/** Fechas de `desde` a `hasta` inclusive ('' = solo `desde`). */
function fechasDelRango(desde: string, hasta: string): string[] {
  const fechas = [desde]
  while (hasta && fechas[fechas.length - 1] < hasta) {
    const d = new Date(`${fechas[fechas.length - 1]}T00:00:00Z`)
    d.setUTCDate(d.getUTCDate() + 1)
    fechas.push(d.toISOString().slice(0, 10))
  }
  return fechas
}

/**
 * Regla que debe cumplir GET /vuelos/buscar/: vuelos activos, con lugar para todos, dentro del rango de precio,
 * que todavía no salieron, ordenados por fecha y hora. `ahora` se inyecta para poder probarlo.
 */
export async function buscarVuelos(p: ParamsBusqueda, ahora = new Date()): Promise<Vuelo[]> {
  await esperar(400)
  const codigos = AEROPUERTOS.map((a) => a.codigo_iata)
  const origenes = p.origen ? [p.origen] : codigos
  const destinos = p.destino ? [p.destino] : codigos
  const hoy = ahora.toLocaleDateString('sv-SE')
  const horaActual = ahora.toTimeString().slice(0, 8)
  return fechasDelRango(p.desde, p.hasta)
    .flatMap((fecha) => origenes.flatMap((o) => destinos.flatMap((d) => generarVuelos(o, d, fecha))))
    .filter((v) => {
      const precio = precioDe(v, p.clase)
      return (
        v.estado === 'activo' &&
        asientosDe(v, p.clase) >= p.pasajeros &&
        (p.precioMin === null || precio >= p.precioMin) &&
        (p.precioMax === null || precio <= p.precioMax) &&
        !(v.fecha_operacion === hoy && v.hora_partida <= horaActual)
      )
    })
    .sort((a, b) => (a.fecha_operacion + a.hora_partida).localeCompare(b.fecha_operacion + b.hora_partida))
}

/** Si la vuelta es el mismo día que la ida, solo sirven las que salen después de que la ida aterriza. */
export function vueltasPosibles(vueltas: Vuelo[], ida: Vuelo): Vuelo[] {
  return vueltas.filter((v) => v.fecha_operacion !== ida.fecha_operacion || v.hora_partida > ida.hora_llegada)
}
