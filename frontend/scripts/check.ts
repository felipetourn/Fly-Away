// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCompleta, fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../src/lib/formato.ts'
import {
  asientosDe,
  buscarVuelos,
  duracionDe,
  estadoClase,
  generarVuelos,
  getAeropuertos,
  getVuelo,
  precioDe,
  vueltasPosibles,
  type ParamsBusqueda,
  type Vuelo,
} from '../src/lib/vuelos.ts'

const hoy = '2026-10-02'
const base: Filtros = {
  origen: 'BHI',
  destino: 'AEP',
  ida: '2026-10-26',
  hasta: '',
  vuelta: '2026-10-31',
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
assert.ok(validarBusqueda({ ...base, pasajeros: 0 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: 10 }, hoy).pasajeros)
assert.ok(validarBusqueda({ ...base, pasajeros: Number.NaN }, hoy).pasajeros)

// validarBusqueda: solo ida (explorador)
assert.deepEqual(validarBusqueda(soloIda, hoy), {})
assert.deepEqual(validarBusqueda({ ...soloIda, destino: '' }, hoy), {}, 'solo origen alcanza')
assert.deepEqual(validarBusqueda({ ...soloIda, origen: '' }, hoy), {}, 'solo destino alcanza')
assert.ok(validarBusqueda({ ...soloIda, origen: '', destino: '' }, hoy).origen, 'al menos uno de los dos')
assert.deepEqual(validarBusqueda({ ...soloIda, hasta: '2026-11-08' }, hoy), {}, 'rango de 14 días')
assert.ok(validarBusqueda({ ...soloIda, hasta: '2026-11-09' }, hoy).hasta, 'rango de 15 días')
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
assert.equal(leerFiltros(new URLSearchParams('ida=2026-10-26&vuelta=2026-10-31&hasta=2026-10-28'))!.hasta, '', 'hasta solo en solo ida')
const basura = leerFiltros(new URLSearchParams('origen=bhi&destino=AEP&ida=mañana&vuelta=2026-13&pasajeros=50&clase=xx'))!
assert.equal(basura.origen, 'BHI')
assert.equal(basura.ida, '', 'fecha mal formada se descarta')
assert.ok(validarBusqueda(basura, hoy).clase, 'clase desconocida → error, no se cambia en silencio')
assert.ok(validarBusqueda(basura, hoy).ida && validarBusqueda(basura, hoy).vuelta && validarBusqueda(basura, hoy).pasajeros)
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-10-26'))!.clase, 'economy', 'sin clase → economy')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2027-02-30'))!.ida, '', 'fecha inexistente se descarta')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-13-45'))!.ida, '', 'mes inexistente se descarta')

// formato
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

// vuelos (mock)
const aeropuertos = await getAeropuertos()
assert.ok(aeropuertos.length >= 10)
assert.ok(aeropuertos.every((a) => /^[A-Z]{3}$/.test(a.codigo_iata)))

const ahora = new Date('2026-10-02T00:00:00') // medianoche local: nada del futuro "ya salió"
const p = (extra: Partial<ParamsBusqueda>): ParamsBusqueda => ({
  origen: 'BHI',
  destino: 'AEP',
  desde: '2026-10-20',
  hasta: '',
  pasajeros: 1,
  clase: 'economy',
  precioMin: null,
  precioMax: null,
  ...extra,
})

const dias = Array.from({ length: 60 }, (_, i) => new Date(Date.UTC(2026, 9, 3 + i)).toISOString().slice(0, 10))
const generados = dias.flatMap((d) => generarVuelos('BHI', 'AEP', d))
assert.ok(generados.some((v) => v.estado === 'cancelado'), 'el mock genera algún cancelado')
assert.ok(generados.every((v) => v.hora_llegada > v.hora_partida && duracionDe(v) > 0), 'llega el mismo día, después de salir')

for (const [pasajeros, clase] of [[1, 'economy'], [9, 'economy'], [3, 'primera']] as const) {
  const porDia = await Promise.all(dias.map((desde) => buscarVuelos(p({ desde, pasajeros, clase }), ahora)))
  for (const vuelos of porDia) {
    assert.ok(vuelos.every((v) => v.estado === 'activo'), 'nunca devuelve cancelados')
    assert.ok(vuelos.every((v) => asientosDe(v, clase) >= pasajeros), 'siempre hay lugar para todos')
    assert.deepEqual(vuelos.map((v) => v.hora_partida), vuelos.map((v) => v.hora_partida).toSorted(), 'ordenados por hora')
  }
  assert.ok(porDia.some((v) => v.length === 0), 'algún día sin vuelos (estado vacío)')
  assert.ok(porDia.some((v) => v.length > 0), 'algún día con vuelos')
}

const cor = p({ origen: 'COR', destino: 'BRC', desde: '2026-11-14' })
assert.deepEqual(await buscarVuelos(cor, ahora), await buscarVuelos(cor, ahora), 'misma búsqueda → mismos resultados')
assert.deepEqual(generarVuelos('AEP', 'AEP', '2026-11-14'), [], 'origen = destino')
assert.deepEqual(generarVuelos('ZZZ', 'AEP', '2026-11-14'), [], 'aeropuerto desconocido')

// explorador: solo origen, solo destino, rango de fechas
const desdeBHI = await buscarVuelos(p({ destino: '', hasta: '2026-10-26' }), ahora)
assert.ok(desdeBHI.every((v) => v.origen.codigo_iata === 'BHI'), 'solo origen: todos salen de BHI')
assert.ok(new Set(desdeBHI.map((v) => v.destino.codigo_iata)).size > 1, 'solo origen: varios destinos')
assert.ok(desdeBHI.every((v) => v.fecha_operacion >= '2026-10-20' && v.fecha_operacion <= '2026-10-26'), 'dentro del rango')
assert.ok(new Set(desdeBHI.map((v) => v.fecha_operacion)).size > 1, 'rango: varios días')
const orden = desdeBHI.map((v) => v.fecha_operacion + v.hora_partida)
assert.deepEqual(orden, orden.toSorted(), 'ordenados por fecha y hora')
const haciaUSH = await buscarVuelos(p({ origen: '', destino: 'USH', hasta: '2026-10-26' }), ahora)
assert.ok(haciaUSH.length > 0 && haciaUSH.every((v) => v.destino.codigo_iata === 'USH'), 'solo destino: todos llegan a USH')

// rango de precio (por persona, en la clase elegida)
const conPrecio = await buscarVuelos(p({ destino: '', hasta: '2026-10-26', precioMin: 120000, precioMax: 160000 }), ahora)
assert.ok(conPrecio.length > 0 && conPrecio.length < desdeBHI.length, 'el filtro de precio recorta')
assert.ok(conPrecio.every((v) => precioDe(v, 'economy') >= 120000 && precioDe(v, 'economy') <= 160000), 'dentro del rango de precio')

// vuelos de hoy que ya salieron no se ofrecen
const mediodia = new Date('2026-10-20T12:00:00')
const todosHoy = aeropuertos.flatMap((a) => generarVuelos('BHI', a.codigo_iata, '2026-10-20'))
assert.ok(todosHoy.some((v) => v.hora_partida < '12:00:00'), 'hay vuelos a la mañana para probar')
const hoyAlMediodia = await buscarVuelos(p({ destino: '' }), mediodia)
assert.ok(hoyAlMediodia.every((v) => v.hora_partida > '12:00:00'), 'solo vuelos que todavía no salieron')

// vueltasPosibles: misma fecha → solo las que salen después de que aterriza la ida
const ida = { fecha_operacion: '2026-11-14', hora_llegada: '12:00:00' } as Vuelo
const vueltas = [
  { id: 'a', fecha_operacion: '2026-11-14', hora_partida: '09:00:00' },
  { id: 'b', fecha_operacion: '2026-11-14', hora_partida: '15:00:00' },
] as Vuelo[]
assert.deepEqual(vueltasPosibles(vueltas, ida).map((v) => v.id), ['b'])
const otroDia = vueltas.map((v) => ({ ...v, fecha_operacion: '2026-11-15' }))
assert.equal(vueltasPosibles(otroDia, ida).length, 2, 'otro día: todas sirven')

// números de vuelo únicos por fecha (índice único numero_vuelo + fecha_operacion del modelo)
for (const fecha of ['2026-10-20', '2026-11-14', '2026-12-24']) {
  const delDia = aeropuertos.flatMap((o) => aeropuertos.flatMap((d) => generarVuelos(o.codigo_iata, d.codigo_iata, fecha)))
  assert.ok(delDia.length > 50, 'hay muchos vuelos ese día')
  assert.equal(new Set(delDia.map((v) => v.numero_vuelo)).size, delDia.length, `números únicos el ${fecha}`)
}

// getVuelo: el mismo vuelo que la búsqueda, con el avión
const encontrados = (await buscarVuelos(p({ destino: '', hasta: '2026-10-22' }), ahora)).slice(0, 5)
assert.ok(encontrados.length === 5)
for (const v of encontrados) {
  const detalle = await getVuelo(v.id)
  assert.deepEqual(detalle, v, `getVuelo(${v.id}) = vuelo de la búsqueda`)
  assert.ok(detalle.avion.modelo && detalle.avion.matricula.startsWith('LV-'), 'trae el avión')
}

// getVuelo: ids que no existen
const rechaza = (id: string) => assert.rejects(getVuelo(id), /Vuelo no encontrado/, `rechaza ${id}`)
await rechaza('cualquiera')
await rechaza('FA999-2026-10-20') // antes del primer número
await rechaza('FA9999-2026-10-20') // después del último bloque de rutas
const conVuelos = dias.find((d) => generarVuelos('BHI', 'AEP', d).length > 0)!
const primero = Number(generarVuelos('BHI', 'AEP', conVuelos)[0].numero_vuelo.slice(3))
const incompleto = dias.find((d) => generarVuelos('BHI', 'AEP', d).length < 4)!
await rechaza(`FA${primero + generarVuelos('BHI', 'AEP', incompleto).length}-${incompleto}`) // número de la ruta que ese día no existe

// getVuelo: un cancelado se devuelve (el detalle informa la cancelación)
const cancelado = generados.find((v) => v.estado === 'cancelado')!
assert.equal((await getVuelo(cancelado.id)).estado, 'cancelado')

// estadoClase
assert.equal(estadoClase(0), 'agotada')
assert.equal(estadoClase(1), 'ultimos')
assert.equal(estadoClase(5), 'ultimos')
assert.equal(estadoClase(6), 'disponible')

console.log('vuelos: OK')
