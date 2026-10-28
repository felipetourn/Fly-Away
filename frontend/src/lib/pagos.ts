import { api } from './api.ts'
import { NOMBRE_CLASE, type Clase } from './busqueda.ts'

// Tipos con la forma de /api/pagos/ (nombres de docs/modelo.dbml).
export interface VueloResumen {
  id: string
  numero_vuelo: string
  origen: string // código IATA
  destino: string
  fecha_operacion: string // YYYY-MM-DD
  hora_partida: string // HH:MM:SS
}

export type EstadoPago = 'pendiente' | 'aprobado' | 'rechazado'

export interface Pago {
  id: string
  reserva_id: string
  vuelo: VueloResumen | null
  cantidad_pasajes: number | null
  metodo_pago: 'tarjeta' | 'mercadopago'
  ultimos_4: string | null
  marca: Marca | null // de la tarjeta, o la usada dentro de Mercado Pago
  cuenta_mp: string | null // mail del comprador en Mercado Pago
  monto: string
  estado: EstadoPago
  detalle: string
  transaccion_externa_id: string | null
  creado_en: string
  procesado_en: string | null
  factura_enviada_en: string | null // null: el mail de la factura no salió
}

export interface DatosTarjeta {
  numero: string
  titular: string
  vencimiento: string // MM/AA
  cvv: string
}

export type Marca = 'visa' | 'mastercard' | 'amex'
export type ErroresTarjeta = Partial<Record<keyof DatosTarjeta, string>>

export const NOMBRE_MARCA: Record<Marca, string> = { visa: 'Visa', mastercard: 'Mastercard', amex: 'American Express' }
export const ETIQUETA_ESTADO: Record<EstadoPago, string> = { aprobado: 'Aprobado', rechazado: 'Rechazado', pendiente: 'Pendiente' }

/** Las mismas tarjetas de prueba que reconoce la pasarela simulada del backend (pagos/tarjeta.py). */
export const TARJETAS_PRUEBA = [
  { marca: 'visa', numero: '4242 4242 4242 4242', resultado: 'Aprobada', tono: 'ok' },
  { marca: 'mastercard', numero: '5555 5555 5555 4444', resultado: 'Aprobada', tono: 'ok' },
  { marca: 'visa', numero: '4000 0000 0000 0002', resultado: 'Rechazada por el emisor', tono: 'error' },
  { marca: 'mastercard', numero: '5200 0000 0000 0007', resultado: 'Rechazada por el emisor', tono: 'error' },
  { marca: 'visa', numero: '4000 0000 0000 9995', resultado: 'Fondos insuficientes', tono: 'error' },
  { marca: 'mastercard', numero: '5200 0000 0000 9990', resultado: 'Fondos insuficientes', tono: 'error' },
  { marca: 'visa', numero: '4000 0000 0000 0119', resultado: 'Error de procesamiento', tono: 'aviso' },
  { marca: 'mastercard', numero: '5200 0000 0000 0114', resultado: 'Error de procesamiento', tono: 'aviso' },
] as const

export const DATOS_PRUEBA = { titular: 'Pasajero Demo', vencimiento: '12/30', cvv: '123' }

export const soloDigitos = (s: string) => s.replace(/\D/g, '')

export function luhnValido(numero: string): boolean {
  let total = 0
  ;[...numero].reverse().forEach((d, i) => {
    let n = Number(d)
    if (i % 2) {
      n *= 2
      if (n > 9) n -= 9
    }
    total += n
  })
  return total % 10 === 0
}

/** Mismos rangos que el backend: Mastercard incluye el prefijo 50 de la tarjeta de prueba de Mercado Pago. */
export function marcaDe(numero: string): Marca | null {
  if (numero.startsWith('4')) return 'visa'
  if (/^3[47]/.test(numero)) return 'amex'
  const dos = Number(numero.slice(0, 2))
  const cuatro = Number(numero.slice(0, 4))
  if ((dos >= 50 && dos <= 55) || (cuatro >= 2221 && cuatro <= 2720)) return 'mastercard'
  return null
}

/** Mientras se escribe: solo dígitos, de a 4, máximo 19. */
export function formatearNumero(valor: string): string {
  return soloDigitos(valor).slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 ')
}

/** Mientras se escribe: "1230" → "12/30". */
export function formatearVencimiento(valor: string): string {
  const d = soloDigitos(valor).slice(0, 4)
  return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d
}

/** Mismas reglas y mensajes que el backend (pagos/tarjeta.py); el backend vuelve a validar. */
export function erroresTarjeta(t: DatosTarjeta, hoy = new Date()): ErroresTarjeta {
  const errores: ErroresTarjeta = {}
  const numero = soloDigitos(t.numero)
  let marca: Marca | null = null
  if (!/^\d{13,19}$/.test(numero)) errores.numero = 'Ingresá un número de tarjeta de 13 a 19 dígitos.'
  else if (!luhnValido(numero)) errores.numero = 'El número de tarjeta no es válido.'
  else {
    marca = marcaDe(numero)
    if (!marca) errores.numero = 'Tarjeta no soportada. Aceptamos Visa, Mastercard y American Express.'
  }
  if (!t.titular.trim()) errores.titular = 'Ingresá el nombre del titular.'
  const fecha = /^(\d{2})\/(\d{2})$/.exec(t.vencimiento)
  if (!fecha || Number(fecha[1]) < 1 || Number(fecha[1]) > 12) errores.vencimiento = 'Ingresá el vencimiento como MM/AA.'
  else {
    const anio = 2000 + Number(fecha[2])
    const mes = Number(fecha[1])
    if (anio < hoy.getFullYear() || (anio === hoy.getFullYear() && mes < hoy.getMonth() + 1))
      errores.vencimiento = 'La tarjeta está vencida.'
  }
  const largo = marca === 'amex' ? 4 : 3
  if (!new RegExp(`^\\d{${largo}}$`).test(t.cvv)) errores.cvv = `El código de seguridad tiene ${largo} dígitos.`
  return errores
}

type MedioDePago = Pick<Pago, 'metodo_pago' | 'ultimos_4' | 'marca' | 'cuenta_mp'>

/** "Visa •••• 4242" o "Mercado Pago" */
export function medioDePago(p: MedioDePago): string {
  if (p.metodo_pago === 'mercadopago') return 'Mercado Pago'
  return `${p.marca ? NOMBRE_MARCA[p.marca] : 'Tarjeta'} •••• ${p.ultimos_4}`
}

/** Con qué se pagó: "•••• 4242" o el mail de la cuenta de Mercado Pago. */
export function cuentaDelPago(p: MedioDePago): string {
  if (p.metodo_pago === 'tarjeta') return `•••• ${p.ultimos_4}`
  return p.cuenta_mp ?? 'Cuenta de Mercado Pago'
}

/** "2 pasajes en Primera" */
export const pasajesDe = (r: { cantidad: number; clase: Clase }) =>
  `${r.cantidad} ${r.cantidad === 1 ? 'pasaje' : 'pasajes'} en ${NOMBRE_CLASE[r.clase]}`

/** "FA 1001, AEP → COR" */
export const vueloCorto = (v: VueloResumen) => `${v.numero_vuelo}, ${v.origen} → ${v.destino}`

/** Subtítulo del resultado: qué pasó con la compra (US08). */
export function mensajeCompra(p: Pick<Pago, 'estado' | 'vuelo' | 'cantidad_pasajes'>): string {
  if (p.estado === 'rechazado') return 'La compra no se confirmó.'
  if (p.estado !== 'aprobado') return ''
  if (!p.vuelo || !p.cantidad_pasajes) return 'Tu compra está confirmada.'
  return p.cantidad_pasajes === 1
    ? `Tu pasaje para ${vueloCorto(p.vuelo)} está confirmado.`
    : `Tus ${p.cantidad_pasajes} pasajes para ${vueloCorto(p.vuelo)} están confirmados.`
}

export interface Aviso {
  tono: 'ok' | 'error'
  texto: string
}

/** Aviso del envío de la factura al llegar recién pagado; null si la compra no está confirmada. */
export function avisoFactura(p: Pick<Pago, 'estado' | 'factura_enviada_en'>, email: string): Aviso | null {
  if (p.estado !== 'aprobado') return null
  if (!p.factura_enviada_en) return { tono: 'error', texto: 'No pudimos enviar la factura por mail.' }
  return { tono: 'ok', texto: email ? `Te enviamos la factura a ${email}.` : 'Te enviamos la factura por mail.' }
}

export const getPagos = () => api<Pago[]>('/pagos/')
export const getPago = (id: string) => api<Pago>(`/pagos/${id}/`)

export const pagarConTarjeta = (reservaId: string, t: DatosTarjeta) =>
  api<Pago>('/pagos/tarjeta/', {
    method: 'POST',
    body: JSON.stringify({ reserva_id: reservaId, ...t, numero: soloDigitos(t.numero) }),
  })

export const pagarConMercadoPago = (reservaId: string) =>
  api<{ pago: Pago; checkout_url: string }>('/pagos/mercadopago/', {
    method: 'POST',
    body: JSON.stringify({ reserva_id: reservaId }),
  })
