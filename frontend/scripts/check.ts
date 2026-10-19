// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, abreHaciaArriba, elegirDia, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCompleta, fechaCorta, fechaDeInstante, fechaLarga, hora, precio, rangoCorto, rangoFechas } from '../src/lib/formato.ts'
import { cuentaDelPago, erroresTarjeta, formatearNumero, formatearVencimiento, luhnValido, marcaDe, medioDePago, mensajeCompra, TARJETAS_PRUEBA } from '../src/lib/pagos.ts'
import { errorDePeriodo, erroresDe, fechasDePeriodo, paginasVisibles, primero, queryListado, yaSalio } from '../src/lib/adminVuelos.ts'
import { ApiError } from '../src/lib/api.ts'
import { destinoTrasLogin } from '../src/lib/auth.ts'
import { validarReglasReserva } from '../src/lib/reservas.ts'
import { duracionDe, estadoClase, llegaAlDiaSiguiente, queryBusqueda, vueltasPosibles, type ParamsBusqueda, type Vuelo } from '../src/lib/vuelos.ts'

const hoy = '2026-10-02'
const base: Filtros = {
  origen: 'BHI',
  destino: 'AEP',
  ida: '2026-10-26',
  hasta: '',
  vuelta: '2026-10-31',
  vueltaHasta: '',
  pasajeros: 2,
  clase: 'economy',
  precioMin: null,
  precioMax: null,
}
const soloIda: Filtros = { ...base, vuelta: null }

// validarBusqueda: ida y vuelta
assert.deepEqual(validarBusqueda(base, hoy), {})
assert.ok(validarBusqueda({ ...base, origen: '' }, hoy).origen, 'ida y vuelta pide origen')
assert.ok(validarBusqueda({ ...base, destino: '' }, hoy).destino, 'ida y vuelta pide destino')
assert.ok(validarBusqueda({ ...base, destino: 'BHI' }, hoy).destino, 'origen = destino')
assert.ok(validarBusqueda({ ...base, ida: '2026-10-01' }, hoy).ida, 'ida en el pasado')
assert.deepEqual(validarBusqueda({ ...base, ida: hoy, vuelta: hoy }, hoy), {}, 'ida hoy y vuelta el mismo día valen')
assert.ok(validarBusqueda({ ...base, vuelta: '' }, hoy).vuelta, 'ida y vuelta sin fecha de vuelta')
assert.ok(validarBusqueda({ ...base, vuelta: '2026-10-25' }, hoy).vuelta, 'vuelta antes que la ida')
const conRangos: Filtros = { ...base, hasta: '2026-10-28', vueltaHasta: '2026-11-04' }
assert.deepEqual(validarBusqueda(conRangos, hoy), {}, 'ida y vuelta con rango en las dos')
assert.ok(validarBusqueda({ ...base, hasta: '2026-10-25' }, hoy).hasta, 'hasta de la ida antes que la ida')
assert.ok(validarBusqueda({ ...base, vueltaHasta: '2026-10-30' }, hoy).vueltaHasta, 'hasta de la vuelta antes que la vuelta')
assert.ok(validarBusqueda({ ...base, pasajeros: 0 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: 10 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: Number.NaN }, hoy).pasajeros)

// validarBusqueda: solo ida (explorador)
assert.deepEqual(validarBusqueda(soloIda, hoy), {})
assert.deepEqual(validarBusqueda({ ...soloIda, destino: '' }, hoy), {}, 'solo origen alcanza')
assert.deepEqual(validarBusqueda({ ...soloIda, origen: '' }, hoy), {}, 'solo destino alcanza')
assert.ok(validarBusqueda({ ...soloIda, origen: '', destino: '' }, hoy).origen, 'al menos uno de los dos')
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2027-10-01' }, hoy), {}, 'rango sin límite de días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-10-25' }, hoy).hasta, 'hasta antes que desde')

// validarBusqueda: contra la lista de aeropuertos (si se pasa)
const lista = [
  { codigo_iata: 'AEP', ciudad: 'Buenos Aires' },
  { codigo_iata: 'EZE', ciudad: 'Buenos Aires' },
  { codigo_iata: 'BHI', ciudad: 'Bahía Blanca' },
]
assert.deepEqual(validarBusqueda(base, hoy, lista), {})
assert.ok(validarBusqueda({ ...base, origen: 'ZZZ' }, hoy, lista).origen, 'origen desconocido')
assert.ok(validarBusqueda({ ...soloIda, origen: '', destino: 'ZZZ' }, hoy, lista).destino, 'destino desconocido')
assert.ok(validarBusqueda({ ...base, origen: 'AEP', destino: 'EZE' }, hoy, lista).destino, 'misma ciudad')
assert.deepEqual(validarBusqueda({ ...base, origen: 'ZZZ' }, hoy), {}, 'sin lista no se valida contra aeropuertos')

// validarBusqueda: precio
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000, precioMax: 200000 }, hoy), {})
assert.deepEqual(validarBusqueda({ ...base, precioMin: 100000 }, hoy), {}, 'solo mínimo')
assert.ok(validarBusqueda({ ...base, precioMin: 200000, precioMax: 100000 }, hoy).precio, 'mínimo > máximo')
assert.ok(validarBusqueda({ ...base, precioMin: -1 }, hoy).precio, 'precio negativo')
assert.ok(validarBusqueda({ ...base, precioMax: Number.NaN }, hoy).precio, 'precio no numérico')

// leerFiltros / aParams
assert.equal(leerFiltros(new URLSearchParams('')), null, 'sin búsqueda')
assert.deepEqual(leerFiltros(aParams(base)), base, 'ida y vuelta por la URL')
const explorador: Filtros = { ...soloIda, origen: '', hasta: '2026-10-30', precioMin: 50000, precioMax: 150000 }
assert.deepEqual(leerFiltros(aParams(explorador)), explorador, 'explorador por la URL')
assert.equal(aParams(base).has('idaId'), false, 'una búsqueda nueva no arrastra el vuelo elegido')
assert.deepEqual(leerFiltros(aParams(conRangos)), conRangos, 'ida y vuelta con rangos por la URL')
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&hasta=2026-10-28&vueltaHasta=2026-11-01'))!.vueltaHasta, '', 'vueltaHasta solo en ida y vuelta')
const basura = leerFiltros(new URLSearchParams('origen=bhi&destino=AEP&ida=mañana&vuelta=2026-13&pasajeros=50&clase=xx'))!
assert.equal(basura.origen, 'BHI')
assert.equal(basura.ida, '', 'fecha mal formada se descarta')
assert.ok(validarBusqueda(basura, hoy).clase, 'clase desconocida → error, no se cambia en silencio')
assert.ok(validarBusqueda(basura, hoy).ida && validarBusqueda(basura, hoy).vuelta && validarBusqueda(basura, hoy).pasajeros)
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-10-26'))!.clase, 'economy', 'sin clase → economy')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2027-02-30'))!.ida, '', 'fecha inexistente se descarta')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-13-45'))!.ida, '', 'mes inexistente se descarta')

// elegirDia: primer clic = inicio, segundo clic = fin (un rango cerrado se reemplaza con el próximo clic)
const vacio = { desde: '', hasta: '', abierto: false }
const inicio = elegirDia(vacio, '2026-10-26')
assert.deepEqual(inicio, { desde: '2026-10-26', hasta: '', abierto: true }, 'primer clic marca el inicio')
assert.deepEqual(elegirDia(inicio, '2026-10-28'), { desde: '2026-10-26', hasta: '2026-10-28', abierto: false }, 'segundo clic cierra el rango')
assert.deepEqual(elegirDia(inicio, '2026-10-26'), { desde: '2026-10-26', hasta: '', abierto: false }, 'mismo día = un solo día')
assert.deepEqual(elegirDia(inicio, '2026-10-20'), { desde: '2026-10-20', hasta: '', abierto: true }, 'día anterior = nuevo inicio')
const cerrado = { desde: '2026-10-26', hasta: '2026-10-28', abierto: false }
assert.deepEqual(elegirDia(cerrado, '2026-11-02'), { desde: '2026-11-02', hasta: '', abierto: true }, 'con rango cerrado empieza otro')

// abreHaciaArriba: el calendario se da vuelta solo si abajo no entra y arriba hay más lugar
assert.equal(abreHaciaArriba(500, 300, 380), false, 'entra abajo')
assert.equal(abreHaciaArriba(200, 450, 380), true, 'no entra abajo y arriba hay más lugar')
assert.equal(abreHaciaArriba(200, 120, 380), false, 'no entra en ningún lado: abajo, donde hay más lugar')

// formato
assert.equal(rangoCorto('', ''), '')
assert.equal(rangoCorto('2026-10-26', ''), '26 oct')
assert.equal(rangoCorto('2026-10-26', '2026-10-28'), '26 oct – 28 oct')
assert.ok(fechaLarga('2026-10-26').startsWith('Lunes') && fechaLarga('2026-10-26').includes('26'), fechaLarga('2026-10-26'))
assert.ok(fechaCorta('2026-10-26').startsWith('Lun') && fechaCorta('2026-10-26').includes('26'), fechaCorta('2026-10-26'))
assert.equal(rangoFechas('2026-10-20', '2026-10-25'), 'Del 20 de octubre al 25 de octubre')
assert.equal(fechaCompleta('2026-10-20'), 'Martes, 20 de octubre de 2026')
assert.equal(hora('06:40:00'), '06:40')
assert.equal(precio(175512), '$ 175.512')
assert.equal(precio(149990.4), '$ 149.990')
assert.equal(duracion(85), '1 h 25 m')
assert.equal(duracion(120), '2 h')

// formato: fechaDeInstante: en hora de Buenos Aires, no UTC
assert.equal(fechaDeInstante('2026-10-21T02:00:00Z'), fechaDeInstante('2026-10-20T23:00:00-03:00'))
assert.match(fechaDeInstante('2026-10-21T02:00:00Z'), /^20 de oct/)
console.log('busqueda + formato: OK')

// vuelos: query string de GET /vuelos/buscar/ (nombres del backend, sin parámetros vacíos)
const params: ParamsBusqueda = {
  origen: 'BHI',
  destino: '',
  desde: '2026-10-20',
  hasta: '',
  pasajeros: 2,
  clase: 'primera',
  precioMin: 50000,
  precioMax: null,
}
assert.equal(queryBusqueda(params).toString(), 'origen=BHI&desde=2026-10-20&pasajeros=2&clase=primera&precio_min=50000')
assert.equal(
  queryBusqueda({ ...params, destino: 'AEP', hasta: '2026-10-25', precioMin: 0, precioMax: 90000 }).toString(),
  'origen=BHI&destino=AEP&desde=2026-10-20&hasta=2026-10-25&pasajeros=2&clase=primera&precio_min=0&precio_max=90000',
  'precio 0 se manda',
)

assert.equal(duracionDe({ fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-14', hora_partida: '06:40:00', hora_llegada: '08:05:00' } as Vuelo), 85)
const nocturno = { fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-15', hora_partida: '23:00:00', hora_llegada: '01:30:00' } as Vuelo
assert.equal(duracionDe(nocturno), 150, 'cruza medianoche')
assert.equal(llegaAlDiaSiguiente(nocturno), true)

// vueltasPosibles: solo las que salen después de que aterriza la ida (la vuelta puede ser un rango superpuesto)
const ida = { fecha_operacion: '2026-11-14', fecha_llegada: '2026-11-14', hora_llegada: '12:00:00' } as Vuelo
const vueltas = [
  { id: 'diaAnterior', fecha_operacion: '2026-11-13', hora_partida: '18:00:00' },
  { id: 'aLaManana', fecha_operacion: '2026-11-14', hora_partida: '09:00:00' },
  { id: 'alAterrizar', fecha_operacion: '2026-11-14', hora_partida: '12:00:00' },
  { id: 'aLaTarde', fecha_operacion: '2026-11-14', hora_partida: '15:00:00' },
  { id: 'otroDia', fecha_operacion: '2026-11-15', hora_partida: '06:00:00' },
] as Vuelo[]
assert.deepEqual(vueltasPosibles(vueltas, ida).map((v) => v.id), ['aLaTarde', 'otroDia'])
assert.deepEqual(vueltasPosibles(vueltas, nocturno).map((v) => v.id), ['otroDia'], 'la ida aterriza el 15 a la 01:30')

// estadoClase
assert.equal(estadoClase(0), 'agotada')
assert.equal(estadoClase(1), 'ultimos')
assert.equal(estadoClase(5), 'ultimos')
assert.equal(estadoClase(6), 'disponible')

console.log('vuelos: OK')

// adminVuelos: fechas de un período (0 = lunes ... 6 = domingo, como el backend)
assert.deepEqual(
  fechasDePeriodo('2026-10-21', '2026-11-03', [0, 2]),
  ['2026-10-21', '2026-10-26', '2026-10-28', '2026-11-02'],
  'lunes y miércoles',
)
assert.deepEqual(fechasDePeriodo('2026-10-25', '2026-10-25', [6]), ['2026-10-25'], 'domingo = 6')
assert.deepEqual(fechasDePeriodo('2026-10-21', '2026-10-21', [0]), [], 'ningún día cae en el rango')
assert.deepEqual(fechasDePeriodo('', '2026-10-21', [0]), [], 'sin fecha')
assert.deepEqual(fechasDePeriodo('2026-10-22', '2026-10-21', [0, 1, 2, 3, 4, 5, 6]), [], 'rango al revés')
assert.equal(fechasDePeriodo('2026-01-01', '2026-12-31', [0, 1, 2, 3, 4, 5, 6]).length, 365)

const filtrosAdmin = { q: '', origen: '', destino: '', desde: '', hasta: '', estado: '', page: 1 }
assert.equal(queryListado(filtrosAdmin).toString(), '', 'sin filtros')
assert.equal(
  queryListado({ ...filtrosAdmin, q: 'FA 1432', origen: 'BHI', estado: 'cancelado', page: 3 }).toString(),
  'q=FA+1432&origen=BHI&estado=cancelado&page=3',
)

const partida = { fecha_operacion: '2026-10-21', hora_partida: '15:00:00' }
assert.equal(yaSalio(partida, new Date('2026-10-21T14:59:00')), false)
assert.equal(yaSalio(partida, new Date('2026-10-21T15:00:00')), true)

const e400 = new ApiError(400, { origen: ['No conocemos el aeropuerto "ZZZ".'], periodos: { 1: { desde: ['x'] } } })
assert.equal(primero(erroresDe(e400).origen), 'No conocemos el aeropuerto "ZZZ".')
assert.equal(primero(erroresDe(e400).destino), '')
assert.equal(errorDePeriodo(erroresDe(e400), 1, 'desde'), 'x', 'DRF indexa los errores de la lista por posición')
assert.equal(errorDePeriodo(erroresDe(e400), 0, 'desde'), '')
assert.equal(errorDePeriodo({ periodos: [{}, { hasta: ['y'] }] }, 1, 'hasta'), 'y', 'también como arreglo')
assert.equal(errorDePeriodo({ periodos: ['Esta lista no puede estar vacía.'] }, 0, 'desde'), '')
assert.deepEqual(erroresDe(new ApiError(500, 'boom')), {})
assert.deepEqual(erroresDe(new Error('red')), {})

// paginasVisibles: primera, última y las vecinas de la actual; null = puntos suspensivos
assert.deepEqual(paginasVisibles(1, 1), [1])
assert.deepEqual(paginasVisibles(1, 0), [1], 'sin resultados igual hay una página')
assert.deepEqual(paginasVisibles(3, 5), [1, 2, 3, 4, 5])
assert.deepEqual(paginasVisibles(1, 20), [1, 2, null, 20])
assert.deepEqual(paginasVisibles(10, 20), [1, null, 9, 10, 11, null, 20])
assert.deepEqual(paginasVisibles(4, 20), [1, 2, 3, 4, 5, null, 20], 'un hueco de una sola página muestra el número')
assert.deepEqual(paginasVisibles(20, 20), [1, null, 19, 20])

console.log('adminVuelos: OK')

// api: una respuesta que no es JSON (500 de Django, página de Render) no se vuelca en pantalla
const SIN_SERVIDOR = 'No pudimos conectar con el servidor. Probá de nuevo en unos minutos.'
assert.equal(new ApiError(500, '<!DOCTYPE html><html><title>ProgrammingError</title></html>').message, SIN_SERVIDOR)
assert.equal(new ApiError(502, '').message, SIN_SERVIDOR)
assert.equal(new ApiError(400, { origen: ['No conocemos el aeropuerto "ZZZ".'] }).message, 'No conocemos el aeropuerto "ZZZ".')
assert.equal(new ApiError(404, { detail: 'No encontrado.' }).message, 'No encontrado.')
assert.equal(new ApiError(500, {}).message, 'Error 500')

console.log('api: OK')

// pagos: tarjeta (mismas reglas que el backend)
assert.equal(luhnValido('4242424242424242'), true)
assert.equal(luhnValido('4242424242424241'), false)
for (const t of TARJETAS_PRUEBA) {
  assert.equal(luhnValido(t.numero.replace(/ /g, '')), true, `tarjeta de prueba ${t.numero}`)
  assert.equal(marcaDe(t.numero.replace(/ /g, '')), t.marca, `marca de ${t.numero}`)
}
assert.equal(TARJETAS_PRUEBA.filter((t) => t.marca === 'visa').length, TARJETAS_PRUEBA.filter((t) => t.marca === 'mastercard').length, 'una Visa y una Mastercard por caso')
assert.equal(marcaDe('4242424242424242'), 'visa')
assert.equal(marcaDe('5031755734530604'), 'mastercard', 'la Mastercard de prueba de Mercado Pago empieza con 50')
assert.equal(marcaDe('5555555555554444'), 'mastercard')
assert.equal(marcaDe('2221000000000009'), 'mastercard')
assert.equal(marcaDe('378282246310005'), 'amex')
assert.equal(marcaDe('6011111111111117'), null)
assert.equal(formatearNumero('42424242abc42424242999999'), '4242 4242 4242 4242 999', 'máximo 19 dígitos')
assert.equal(formatearVencimiento('1230'), '12/30')
assert.equal(formatearVencimiento('1'), '1')
const tarjetaOk = { numero: '4242 4242 4242 4242', titular: 'Ana', vencimiento: '12/30', cvv: '123' }
const octubre = new Date(2026, 9, 20)
assert.deepEqual(erroresTarjeta(tarjetaOk, octubre), {})
assert.deepEqual(erroresTarjeta({ ...tarjetaOk, vencimiento: '10/26' }, octubre), {}, 'vence a fin de mes')
assert.ok(erroresTarjeta({ ...tarjetaOk, vencimiento: '09/26' }, octubre).vencimiento, 'vencida')
assert.ok(erroresTarjeta({ ...tarjetaOk, vencimiento: '13/30' }, octubre).vencimiento)
assert.ok(erroresTarjeta({ ...tarjetaOk, numero: '4242 4242 4242 4241' }, octubre).numero, 'Luhn')
assert.ok(erroresTarjeta({ ...tarjetaOk, numero: '6011 1111 1111 1117' }, octubre).numero, 'marca no soportada')
assert.ok(erroresTarjeta({ ...tarjetaOk, titular: ' ' }, octubre).titular)
assert.ok(erroresTarjeta({ ...tarjetaOk, numero: '3782 822463 10005', cvv: '123' }, octubre).cvv, 'Amex pide 4')
const conTarjeta = { metodo_pago: 'tarjeta', ultimos_4: '4242', marca: 'visa', cuenta_mp: null } as const
const conMp = { metodo_pago: 'mercadopago', ultimos_4: null, marca: 'mastercard', cuenta_mp: 'test@testuser.com' } as const
assert.equal(medioDePago(conTarjeta), 'Visa •••• 4242')
assert.equal(medioDePago({ ...conTarjeta, marca: null }), 'Tarjeta •••• 4242', 'pagos viejos sin marca')
assert.equal(medioDePago(conMp), 'Mercado Pago')
assert.equal(cuentaDelPago(conTarjeta), '•••• 4242')
assert.equal(cuentaDelPago(conMp), 'test@testuser.com')
assert.equal(cuentaDelPago({ ...conMp, cuenta_mp: null }), 'Cuenta de Mercado Pago', 'MP no informó el mail')
const vuelo = { id: 'v', numero_vuelo: 'FA 1072', origen: 'AEP', destino: 'COR', fecha_operacion: '2026-10-21', hora_partida: '15:00:00' }
assert.equal(mensajeCompra({ estado: 'aprobado', vuelo, cantidad_pasajes: 2 }), 'Tus 2 pasajes para FA 1072, AEP → COR están confirmados.')
assert.equal(mensajeCompra({ estado: 'aprobado', vuelo, cantidad_pasajes: 1 }), 'Tu pasaje para FA 1072, AEP → COR está confirmado.')
assert.equal(mensajeCompra({ estado: 'aprobado', vuelo: null, cantidad_pasajes: null }), 'Tu compra está confirmada.')
assert.equal(mensajeCompra({ estado: 'rechazado', vuelo, cantidad_pasajes: 2 }), 'La compra no se confirmó.')
assert.equal(mensajeCompra({ estado: 'pendiente', vuelo, cantidad_pasajes: 2 }), '')
console.log('pagos: OK')

// validarReglasReserva (US06)
assert.equal(validarReglasReserva(1, 10), null, '1 pasaje con 10 disponibles es válido')
assert.equal(validarReglasReserva(9, 10), null, '9 pasajes con 10 disponibles es válido')
assert.equal(validarReglasReserva(5, 5), null, 'exactamente la cantidad de disponibles es válido')
assert.ok(validarReglasReserva(0, 10), '0 pasajes es inválido')
assert.ok(validarReglasReserva(10, 15), 'más de 9 pasajes es inválido')
assert.ok(validarReglasReserva(4, 3), 'más pasajes que disponibles es inválido')
assert.ok(validarReglasReserva(-1, 5), 'cantidad negativa es inválida')
console.log('reservas: OK')


// auth: adónde volver tras iniciar sesión (solo rutas internas; nunca de vuelta al login o al registro)
assert.equal(destinoTrasLogin(undefined), '/')
assert.equal(destinoTrasLogin(null), '/')
assert.equal(destinoTrasLogin({ desde: '/?origen=EZE&idaId=1&vueltaId=2' }), '/?origen=EZE&idaId=1&vueltaId=2')
assert.equal(destinoTrasLogin({ desde: '/reservas' }), '/reservas')
assert.equal(destinoTrasLogin({ desde: '//otro-sitio.com' }), '/')
assert.equal(destinoTrasLogin({ desde: 'https://otro-sitio.com' }), '/')
assert.equal(destinoTrasLogin({ desde: '/login' }), '/')
assert.equal(destinoTrasLogin({ desde: '/registro?x=1' }), '/')
assert.equal(destinoTrasLogin({ desde: 42 }), '/')
console.log('auth: OK')
