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
  vuelo: VueloResumen & { estado: 'activo' | 'cancelado' }
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
  nombre_pasajero: string
  apellido_pasajero: string
  dni_pasajero: string
}

export interface DatosCrearReserva {
  vuelo_id: string
  clase: Clase
  cantidad_pasajes: number
  pasajeros: PasajeroInput[]
  contacto_email?: string
  contacto_nombre?: string
}

export interface DatosCrearReservaIdaVuelta {
  vuelo_ida: string
  vuelo_vuelta: string
  ida: Omit<DatosCrearReserva, 'vuelo_id'>
  vuelta: Omit<DatosCrearReserva, 'vuelo_id'>
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

// Mismas reglas que PasajeroInputSerializer del backend.
const NOMBRE_VALIDO = /^\p{L}[\p{L} '’.-]*$/u
const DNI_VALIDO = /^\d{8}$/

export type ErroresPasajero = Partial<Record<keyof PasajeroInput, string>>

/** Errores de los datos de un pasajero; vacío = válido. El DNI (8 dígitos) se acepta con puntos, espacios o guiones. */
export function erroresPasajero(p: PasajeroInput): ErroresPasajero {
  const errores: ErroresPasajero = {}
  const nombre = (campo: 'nombre_pasajero' | 'apellido_pasajero', texto: string) => {
    const valor = p[campo].trim()
    if (!valor) errores[campo] = `Ingresá el ${texto}.`
    else if (!NOMBRE_VALIDO.test(valor)) errores[campo] = `El ${texto} solo puede tener letras, espacios, apóstrofos, guiones y puntos.`
  }
  nombre('nombre_pasajero', 'nombre')
  nombre('apellido_pasajero', 'apellido')
  const dni = p.dni_pasajero.replace(/[\s.-]/g, '')
  if (!dni) errores.dni_pasajero = 'Ingresá el DNI.'
  else if (!DNI_VALIDO.test(dni)) errores.dni_pasajero = 'El DNI debe tener 8 dígitos.'
  return errores
}

export const crearReserva = (datos: DatosCrearReserva) =>
  api<Reserva>('/reservas/', {
    method: 'POST',
    body: JSON.stringify(datos),
  })

export const crearReservaIdaVuelta = (datos: DatosCrearReservaIdaVuelta) =>
  api<{ ida: Reserva; vuelta: Reserva }>('/reservas/ida-vuelta/', {
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
