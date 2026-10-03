// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, elegirDia, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCompleta, fechaCorta, fechaLarga, hora, precio, rangoCorto, rangoFechas } from '../src/lib/formato.ts'
import { errorDePeriodo, erroresDe, fechasDePeriodo, paginasVisibles, primero, queryListado, yaSalio } from '../src/lib/adminVuelos.ts'
import { ApiError } from '../src/lib/api.ts'
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
