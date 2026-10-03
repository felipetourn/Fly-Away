import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import BuscadorVuelos from '../components/BuscadorVuelos'
import FiltroPrecio from '../components/FiltroPrecio'
import HeroCarrusel from '../components/HeroCarrusel'
import ListaVuelos from '../components/ListaVuelos'
import { NOMBRE_CLASE, aParams, hoyISO, leerFiltros, validarBusqueda, type Clase, type Filtros } from '../lib/busqueda'
import { fechaCorta, fechaLarga, hora, precio, rangoFechas } from '../lib/formato'
import { useVuelos } from '../lib/useVuelos'
import { getAeropuertos, llegaAlDiaSiguiente, precioDe, vueltasPosibles, type Aeropuerto, type Vuelo } from '../lib/vuelos'

function Pasos({ actual, total }: { actual: 1 | 2; total: 1 | 2 }) {
  const paso = (n: 1 | 2, texto: string) => (
    <li
      aria-current={n === actual ? 'step' : undefined}
      className={`flex items-center gap-2 ${n <= actual ? 'text-marino' : 'text-slate-400'}`}
    >
      <span
        className={`grid h-6 w-6 place-items-center rounded-full text-xs ${
          n <= actual ? 'bg-marino text-white' : 'bg-slate-200'
        }`}
      >
        {n}
      </span>
      {texto}
    </li>
  )
  return (
    <ol aria-label="Pasos" className="mb-6 flex items-center gap-3 text-sm font-semibold">
      {paso(1, 'Vuelo de ida')}
      {total === 2 && <li className="h-px w-10 bg-slate-300" aria-hidden="true" />}
      {total === 2 && paso(2, 'Vuelo de vuelta')}
    </ol>
  )
}

function LineaVuelo({ etiqueta, vuelo, clase }: { etiqueta: string; vuelo: Vuelo; clase: Clase }) {
  return (
    <p className="text-slate-700">
      <span className="font-bold text-marino">{etiqueta}</span> - {vuelo.numero_vuelo},{' '}
      {fechaCorta(vuelo.fecha_operacion)}, {hora(vuelo.hora_partida)} → {hora(vuelo.hora_llegada)}{llegaAlDiaSiguiente(vuelo) ? ' (+1)' : ''},{' '}
      {vuelo.origen.codigo_iata} → {vuelo.destino.codigo_iata}, {precio(precioDe(vuelo, clase))} por persona
    </p>
  )
}

export default function Vuelos() {
  const [params, setParams] = useSearchParams()
  const [aeropuertos, setAeropuertos] = useState<Aeropuerto[]>([])
  const [errorAeropuertos, setErrorAeropuertos] = useState(false)
  const [intentoAeropuertos, setIntentoAeropuertos] = useState(0)
  // Vuelta elegida, atada a la búsqueda (e ida) en la que se eligió. Se limpia al cambiar de búsqueda o de ida.
  const [vuelta, setVuelta] = useState<{ busqueda: string; vuelo: Vuelo } | null>(null)

  useEffect(() => {
    getAeropuertos().then(
      (lista) => {
        setAeropuertos(lista)
        setErrorAeropuertos(false)
      },
      () => setErrorAeropuertos(true),
    )
  }, [intentoAeropuertos])

  const filtros = leerFiltros(params)
  // Se valida (y se busca) recién con los aeropuertos cargados: así se detectan códigos desconocidos.
  const listos = aeropuertos.length > 0
  const erroresUrl = filtros && listos ? validarBusqueda(filtros, hoyISO(), aeropuertos) : {}
  // Solo se busca con filtros válidos: la URL puede venir editada o ser de otro día.
  const f = filtros && listos && Object.keys(erroresUrl).length === 0 ? filtros : null
  // Cambia con cada búsqueda (sin idaId): remonta el buscador con los valores de la URL.
  const claveFiltros = filtros ? aParams(filtros).toString() : ''

  const busquedaIda = useVuelos(
    f && {
      origen: f.origen,
      destino: f.destino,
      desde: f.ida,
      hasta: f.hasta,
      pasajeros: f.pasajeros,
      clase: f.clase,
      precioMin: f.precioMin,
      precioMax: f.precioMax,
    },
  )
  // Si el idaId de la URL no está en los resultados (URL vieja o editada), se vuelve al paso 1.
  const idaElegida = busquedaIda.vuelos.find((v) => v.id === params.get('idaId')) ?? null
  const busquedaVuelta = useVuelos(
    f?.vuelta && idaElegida
      ? {
          origen: f.destino,
          destino: f.origen,
          desde: f.vuelta,
          hasta: f.vueltaHasta,
          pasajeros: f.pasajeros,
          clase: f.clase,
          precioMin: f.precioMin,
          precioMax: f.precioMax,
        }
      : null,
  )
  const vueltaElegida = vuelta?.busqueda === params.toString() ? vuelta.vuelo : null

  const ciudad = (iata: string) => aeropuertos.find((a) => a.codigo_iata === iata)?.ciudad ?? iata

  function irA(p: URLSearchParams) {
    setVuelta(null)
    setParams(p)
  }
  function buscar(nuevos: Filtros) {
    irA(aParams(nuevos))
  }
  function filtrarPrecio(min: number | null, max: number | null) {
    if (filtros) irA(aParams({ ...filtros, precioMin: min, precioMax: max }))
  }
  function elegirIda(v: Vuelo) {
    const p = new URLSearchParams(params)
    p.set('idaId', v.id)
    irA(p)
  }
  function cambiarIda() {
    const p = new URLSearchParams(params)
    p.delete('idaId')
    irA(p)
  }

  let contenido = null
  if (errorAeropuertos) {
    contenido = (
      <div role="alert" className="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-700">
        <p className="font-semibold">No pudimos cargar los aeropuertos. Probá de nuevo.</p>
        <button
          type="button"
          onClick={() => setIntentoAeropuertos((n) => n + 1)}
          className="mt-3 rounded-xl bg-white px-4 py-2 text-sm font-bold ring-1 ring-red-200 hover:bg-red-100"
        >
          Reintentar
        </button>
      </div>
    )
  } else if (filtros && listos && !f) {
    contenido = <p className="text-slate-500">Revisá los datos marcados en el buscador y volvé a buscar.</p>
  } else if (f) {
    const total = f.vuelta === null ? 1 : 2
    const detalle = `${f.pasajeros} ${f.pasajeros === 1 ? 'pasajero' : 'pasajeros'}, ${NOMBRE_CLASE[f.clase]}`
    const sugerencia =
      f.precioMin !== null || f.precioMax !== null
        ? 'Probá ampliar el rango de precio.'
        : !f.hasta || (f.vuelta !== null && !f.vueltaHasta)
          ? 'Probá con un rango de fechas.'
          : 'Probá con otras fechas.'
    const tituloIda =
      f.origen && f.destino
        ? `${ciudad(f.origen)} → ${ciudad(f.destino)}`
        : f.origen
          ? `Desde ${ciudad(f.origen)}`
          : `Hacia ${ciudad(f.destino)}`

    if (!idaElegida) {
      contenido = (
        <>
          <Pasos actual={1} total={total} />
          <ListaVuelos
            key={claveFiltros}
            titulo={tituloIda}
            subtitulo={`${f.hasta ? rangoFechas(f.ida, f.hasta) : fechaLarga(f.ida)} - ${detalle}`}
            estado={busquedaIda.estado}
            vuelos={busquedaIda.vuelos}
            clase={f.clase}
            pasajeros={f.pasajeros}
            sugerencia={sugerencia}
            onElegir={elegirIda}
            onReintentar={busquedaIda.reintentar}
          />
        </>
      )
    } else if (f.vuelta !== null && !vueltaElegida) {
      contenido = (
        <>
          <Pasos actual={2} total={2} />
          <div className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4">
            <LineaVuelo etiqueta="Ida elegida" vuelo={idaElegida} clase={f.clase} />
            <button type="button" onClick={cambiarIda} className="text-sm font-bold text-cielo hover:underline">
              Cambiar
            </button>
          </div>
          <ListaVuelos
            key={`${claveFiltros}-${idaElegida.id}`}
            titulo={`${ciudad(f.destino)} → ${ciudad(f.origen)}`}
            subtitulo={`${f.vueltaHasta ? rangoFechas(f.vuelta, f.vueltaHasta) : fechaLarga(f.vuelta)} - ${detalle}`}
            estado={busquedaVuelta.estado}
            vuelos={vueltasPosibles(busquedaVuelta.vuelos, idaElegida)}
            clase={f.clase}
            pasajeros={f.pasajeros}
            sugerencia={sugerencia}
            onElegir={(v) => setVuelta({ busqueda: params.toString(), vuelo: v })}
            onReintentar={busquedaVuelta.reintentar}
          />
        </>
      )
    } else {
      const elegidos = vueltaElegida ? [idaElegida, vueltaElegida] : [idaElegida]
      const totalPrecio = elegidos.reduce((suma, v) => suma + precioDe(v, f.clase), 0) * f.pasajeros
      contenido = (
        <section className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8">
          <h2 className="mb-4 text-2xl font-extrabold text-marino">Tu viaje</h2>
          <div className="space-y-2">
            <LineaVuelo etiqueta="Ida" vuelo={idaElegida} clase={f.clase} />
            {vueltaElegida && <LineaVuelo etiqueta="Vuelta" vuelo={vueltaElegida} clase={f.clase} />}
          </div>
          <div className="mt-6 flex flex-wrap items-end justify-between gap-4 border-t border-slate-100 pt-6">
            <div>
              <p className="text-sm text-slate-500">Total - {detalle}</p>
              <p className="text-3xl font-extrabold text-marino">{precio(totalPrecio)}</p>
            </div>
            <div className="text-right">
              <button
                type="button"
                disabled
                className="cursor-not-allowed rounded-xl bg-slate-300 px-6 py-3 font-bold text-white"
              >
                Continuar
              </button>
              <p className="mt-1 text-xs text-slate-500">La compra llega pronto</p>
            </div>
          </div>
          <button type="button" onClick={cambiarIda} className="mt-4 text-sm font-bold text-cielo hover:underline">
            Cambiar vuelos
          </button>
        </section>
      )
    }

  }

  return (
    <>
      <HeroCarrusel />
      <section className="relative z-10 mx-auto -mt-20 max-w-[88rem] px-4">
        <BuscadorVuelos
          key={`${claveFiltros}-${listos}`}
          aeropuertos={aeropuertos}
          inicial={filtros}
          erroresIniciales={erroresUrl}
          onBuscar={buscar}
        />
      </section>
      <main className="mx-auto max-w-[88rem] px-4 py-10">
        {/* Visible aunque la URL sea inválida: así se puede corregir un rango de precio mal cargado. */}
        {filtros && (
          <FiltroPrecio
            key={`${filtros.precioMin}-${filtros.precioMax}-${listos}`}
            min={filtros.precioMin}
            max={filtros.precioMax}
            clase={filtros.clase}
            errorInicial={erroresUrl.precio}
            onAplicar={filtrarPrecio}
          />
        )}
        {contenido}
      </main>
    </>
  )
}
