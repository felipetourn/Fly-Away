import { api, apiBlob } from './api.ts'
import type { Clase } from './busqueda.ts'
import type { VueloResumen } from './pagos.ts'

export interface Pasaje {
  id: string
  codigo_pasaje: string
  nombre_pasajero: string
  apellido_pasajero: string
  dni_pasajero: string
  clase: Clase
  asiento: string | null
  precio: string
  ticket_electronico_url: string | null
}

export interface TicketElectronico extends Pasaje {
  vuelo: VueloResumen & {
    fecha_llegada: string
    hora_llegada: string
  }
  reserva_id: string
  estado_compra: 'pendiente' | 'pagada' | 'cancelada'
  ticket_pdf_url: string
}

export interface Reserva {
  id: string
  vuelo: VueloResumen
  clase: Clase
  cantidad: number
  cantidad_pasajes: number
  monto: string
  estado: 'pendiente' | 'pagada' | 'cancelada'
  contacto_email: string
  contacto_nombre: string
  pasajes: Pasaje[]
  creado_en: string
}

export interface PasajeroInput {
  nombre_pasajero?: string
  apellido_pasajero?: string
  dni_pasajero?: string
}

export interface DatosCrearReserva {
  vuelo_id: string
  clase: Clase
  cantidad_pasajes: number
  pasajeros?: PasajeroInput[]
  contacto_email?: string
  contacto_nombre?: string
}

export const MINIMO_PASAJES = 1
export const MAXIMO_PASAJES = 9

/**
 * Valida las reglas de reserva del lado del cliente por UX.
 * El backend siempre vuelve a validar estas reglas dentro de una transacción con lock.
 */
export function validarReglasReserva(cantidad: number, asientosDisponibles: number): string | null {
  if (!Number.isInteger(cantidad) || cantidad < MINIMO_PASAJES || cantidad > MAXIMO_PASAJES) {
    return `La cantidad de pasajes debe ser entre ${MINIMO_PASAJES} y ${MAXIMO_PASAJES}.`
  }
  if (cantidad > asientosDisponibles) {
    return `No hay disponibilidad suficiente. Solo quedan ${asientosDisponibles} ${
      asientosDisponibles === 1 ? 'asiento disponible' : 'asientos disponibles'
    }.`
  }
  return null
}

export const crearReserva = (datos: DatosCrearReserva) =>
  api<Reserva>('/reservas/', {
    method: 'POST',
    body: JSON.stringify(datos),
  })

export const getMisReservas = () => api<Reserva[]>('/reservas/')

export const getReserva = (id: string) => api<Reserva>(`/reservas/${id}/`)

export const getTicket = (codigo: string) =>
  api<TicketElectronico>(`/pasajes/${encodeURIComponent(codigo)}/`)

export async function descargarTicket(codigo: string): Promise<void> {
  const pdf = await apiBlob(`/pasajes/${encodeURIComponent(codigo)}/pdf/`)
  const url = URL.createObjectURL(pdf)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = `ticket-${codigo}.pdf`
  document.body.append(enlace)
  enlace.click()
  enlace.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
