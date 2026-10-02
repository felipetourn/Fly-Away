// Chequeos de la lógica pura. Correr con: npm run check
process.env.TZ = 'America/Argentina/Buenos_Aires' // UTC−3: detecta fechas corridas un día

import assert from 'node:assert/strict'
import { aParams, leerFiltros, validarBusqueda, type Filtros } from '../src/lib/busqueda.ts'
import { duracion, fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../src/lib/formato.ts'

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
assert.equal(basura.clase, 'economy', 'clase desconocida → economy')
assert.ok(validarBusqueda(basura, hoy).ida && validarBusqueda(basura, hoy).vuelta && validarBusqueda(basura, hoy).pasajeros)
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2027-02-30'))!.ida, '', 'fecha inexistente se descarta')
assert.equal(leerFiltros(new URLSearchParams('origen=BHI&ida=2026-13-45'))!.ida, '', 'mes inexistente se descarta')

// formato
assert.ok(fechaLarga('2026-10-26').startsWith('Lunes') && fechaLarga('2026-10-26').includes('26'), fechaLarga('2026-10-26'))
assert.ok(fechaCorta('2026-10-26').startsWith('Lun') && fechaCorta('2026-10-26').includes('26'), fechaCorta('2026-10-26'))
assert.equal(rangoFechas('2026-10-20', '2026-10-25'), 'Del 20 de octubre al 25 de octubre')
assert.equal(hora('06:40:00'), '06:40')
assert.equal(precio(175512), '$ 175.512')
assert.equal(precio(149990.4), '$ 149.990')
assert.equal(duracion(85), '1 h 25 m')
assert.equal(duracion(120), '2 h')

console.log('busqueda + formato: OK')
