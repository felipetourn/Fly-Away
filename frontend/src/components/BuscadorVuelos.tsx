import { useState, type FormEvent, type ReactNode } from 'react'
import {
  MAX_PASAJEROS,
  hoyISO,
  validarBusqueda,
  type Clase,
  type ErroresBusqueda,
  type Filtros,
} from '../lib/busqueda'
import type { Aeropuerto } from '../lib/vuelos'

interface Props {
  aeropuertos: Aeropuerto[]
  inicial: Filtros | null
  /** Errores de una URL inválida: se muestran hasta el primer envío. */
  erroresIniciales?: ErroresBusqueda
  onBuscar: (f: Filtros) => void
}

const caja = 'rounded-2xl border border-slate-200 px-4 py-2.5 focus-within:border-cielo'
const etiqueta = 'block text-xs font-semibold text-slate-500'
const control = 'w-full bg-transparent font-semibold outline-none'
const pildora = (activa: boolean) =>
  `cursor-pointer rounded-full px-4 py-1.5 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-cielo ${
    activa ? 'bg-marino text-white' : 'text-slate-500 hover:bg-slate-100'
  }`

function MensajeError({ id, texto }: { id: string; texto?: string }) {
  return texto ? (
    <p id={id} className="mt-1 px-1 text-xs font-medium text-red-600">
      {texto}
    </p>
  ) : null
}

function CampoFecha(props: {
  id: string
  texto: ReactNode
  valor: string
  min: string
  error?: string
  onChange: (v: string) => void
}) {
  return (
    <div>
      <div className={caja}>
        <label htmlFor={props.id} className={etiqueta}>
          {props.texto}
        </label>
        <input
          id={props.id}
          type="date"
          min={props.min}
          value={props.valor}
          onChange={(e) => props.onChange(e.target.value)}
          aria-invalid={!!props.error}
          aria-describedby={`error-${props.id}`}
          className={control}
        />
      </div>
      <MensajeError id={`error-${props.id}`} texto={props.error} />
    </div>
  )
}

/** "Hasta (opcional)"; `de` aclara a cuál fecha para lectores de pantalla. */
const hastaOpcional = (de: string) => (
  <>
    Hasta <span className="sr-only">{de} </span>
    <span className="font-normal">(opcional)</span>
  </>
)

export default function BuscadorVuelos({ aeropuertos, inicial, erroresIniciales = {}, onBuscar }: Props) {
  const pasajerosIniciales = inicial?.pasajeros ?? 1
  const [soloIda, setSoloIda] = useState(inicial?.vuelta === null)
  const [origen, setOrigen] = useState(inicial?.origen ?? '')
  const [destino, setDestino] = useState(inicial?.destino ?? '')
  const [ida, setIda] = useState(inicial?.ida ?? '')
  const [hasta, setHasta] = useState(inicial?.hasta ?? '')
  const [vuelta, setVuelta] = useState(inicial?.vuelta ?? '')
  const [vueltaHasta, setVueltaHasta] = useState(inicial?.vueltaHasta ?? '')
  const [pasajeros, setPasajeros] = useState(
    Number.isInteger(pasajerosIniciales) && pasajerosIniciales >= 1 && pasajerosIniciales <= MAX_PASAJEROS
      ? pasajerosIniciales
      : 1,
  )
  const [clase, setClase] = useState<Clase>(inicial?.clase === 'primera' ? 'primera' : 'economy')
  const [enviados, setEnviados] = useState<ErroresBusqueda | null>(null)
  const errores = enviados ?? erroresIniciales
  const hoy = hoyISO()

  function enviar(e: FormEvent) {
    e.preventDefault()
    const filtros: Filtros = {
      origen,
      destino,
      ida,
      hasta,
      vuelta: soloIda ? null : vuelta,
      vueltaHasta: soloIda ? '' : vueltaHasta,
      pasajeros,
      clase,
      // El rango de precio se edita sobre los resultados; una búsqueda nueva lo conserva.
      precioMin: inicial?.precioMin ?? null,
      precioMax: inicial?.precioMax ?? null,
    }
    const nuevos = validarBusqueda(filtros, hoy, aeropuertos.length ? aeropuertos : undefined)
    setEnviados(nuevos)
    if (Object.keys(nuevos).length === 0) onBuscar(filtros)
  }

  function invertir() {
    setOrigen(destino)
    setDestino(origen)
  }

  const opciones = aeropuertos.map((a) => (
    <option key={a.id} value={a.codigo_iata}>
      {a.ciudad} ({a.codigo_iata})
    </option>
  ))

  return (
    <form onSubmit={enviar} noValidate className="rounded-3xl bg-white p-4 shadow-2xl shadow-marino/20 md:p-6">
      <fieldset className="mb-4 flex gap-2 text-sm font-semibold">
        <legend className="sr-only">Tipo de viaje</legend>
        <label className={pildora(!soloIda)}>
          <input type="radio" name="tipo" className="sr-only" checked={!soloIda} onChange={() => setSoloIda(false)} />
          Ida y vuelta
        </label>
        <label className={pildora(soloIda)}>
          <input type="radio" name="tipo" className="sr-only" checked={soloIda} onChange={() => setSoloIda(true)} />
          Solo ida
        </label>
      </fieldset>

      <div
        className={`grid gap-2 lg:items-start ${
          soloIda
            ? 'lg:grid-cols-[1fr_auto_1fr_2fr_1.3fr_auto]'
            : 'lg:grid-cols-[1fr_auto_1fr_2fr_2fr_1.3fr_auto]'
        }`}
      >
        <div>
          <div className={caja}>
            <label htmlFor="origen" className={etiqueta}>
              Origen
            </label>
            <select
              id="origen"
              value={origen}
              onChange={(e) => setOrigen(e.target.value)}
              aria-invalid={!!errores.origen}
              aria-describedby="error-origen"
              className={control}
            >
              {/* En solo ida el origen es opcional: "Cualquiera". */}
              <option value="" disabled={!soloIda}>
                {soloIda ? 'Cualquiera' : '¿Desde dónde?'}
              </option>
              {opciones}
            </select>
          </div>
          <MensajeError id="error-origen" texto={errores.origen} />
        </div>

        <button
          type="button"
          onClick={invertir}
          aria-label="Invertir origen y destino"
          className="z-10 mx-auto -my-3 grid h-9 w-9 place-items-center rounded-full border border-slate-200 bg-white text-marino shadow-sm hover:bg-slate-50 lg:-mx-4 lg:my-0 lg:mt-3.5"
        >
          ⇄
        </button>

        <div>
          <div className={caja}>
            <label htmlFor="destino" className={etiqueta}>
              Destino
            </label>
            <select
              id="destino"
              value={destino}
              onChange={(e) => setDestino(e.target.value)}
              aria-invalid={!!errores.destino}
              aria-describedby="error-destino"
              className={control}
            >
              <option value="" disabled={!soloIda}>
                {soloIda ? 'Cualquiera' : '¿A dónde?'}
              </option>
              {opciones}
            </select>
          </div>
          <MensajeError id="error-destino" texto={errores.destino} />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <CampoFecha
            id="ida"
            texto={soloIda ? 'Desde' : 'Ida'}
            valor={ida}
            min={hoy}
            error={errores.ida}
            onChange={setIda}
          />
          <CampoFecha
            id="hasta"
            texto={hastaOpcional(soloIda ? '' : 'de la ida')}
            valor={hasta}
            min={ida || hoy}
            error={errores.hasta}
            onChange={setHasta}
          />
        </div>

        {!soloIda && (
          <div className="grid grid-cols-2 gap-2">
            <CampoFecha
              id="vuelta"
              texto="Vuelta"
              valor={vuelta}
              min={ida || hoy}
              error={errores.vuelta}
              onChange={setVuelta}
            />
            <CampoFecha
              id="vueltaHasta"
              texto={hastaOpcional('de la vuelta')}
              valor={vueltaHasta}
              min={vuelta || ida || hoy}
              error={errores.vueltaHasta}
              onChange={setVueltaHasta}
            />
          </div>
        )}

        <div>
          <div className={caja}>
            <span className={etiqueta}>Pasajeros y clase</span>
            <div className="flex gap-2">
              <select
                aria-label="Pasajeros"
                aria-invalid={!!errores.pasajeros}
                aria-describedby="error-pasajeros"
                value={pasajeros}
                onChange={(e) => setPasajeros(Number(e.target.value))}
                className={control}
              >
                {Array.from({ length: MAX_PASAJEROS }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>
                    {n} {n === 1 ? 'pasajero' : 'pasajeros'}
                  </option>
                ))}
              </select>
              <select
                aria-label="Clase"
                value={clase}
                onChange={(e) => setClase(e.target.value as Clase)}
                className={control}
              >
                <option value="economy">Economy</option>
                <option value="primera">Primera</option>
              </select>
            </div>
          </div>
          <MensajeError id="error-pasajeros" texto={errores.pasajeros ?? errores.clase} />
        </div>

        <button
          type="submit"
          className="min-h-[62px] rounded-2xl bg-naranja px-7 text-base font-bold text-white shadow-lg shadow-naranja/30 hover:bg-[#f0600a]"
        >
          Buscar
        </button>
      </div>
    </form>
  )
}
