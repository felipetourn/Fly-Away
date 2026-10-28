import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { fechaCompleta, hora, precio } from '../lib/formato'
import {
  crearReserva,
  crearReservaIdaVuelta,
  erroresPasajero,
  MAXIMO_PASAJES,
  MINIMO_PASAJES,
  validarReglasReserva,
  type PasajeroInput,
} from '../lib/reservas'
import { useSesion } from '../lib/sesion'
import { asientosDe, precioDe, type Vuelo } from '../lib/vuelos'

interface Props {
  vuelo: Vuelo
  vueloVuelta?: Vuelo
  claseInicial?: Clase
  pasajerosInicial?: number
  onCerrar: () => void
}

interface ConfiguracionTramo {
  clase: Clase
  cantidad: number
  pasajeros: PasajeroInput[]
}

interface ConfiguradorTramoProps {
  etiqueta: string
  vuelo: Vuelo
  configuracion: ConfiguracionTramo
  // Tras intentar confirmar también se marcan los campos vacíos; antes, solo lo mal escrito.
  mostrarErrores: boolean
  onChange: (configuracion: ConfiguracionTramo) => void
}

const pasajerosValidos = (c: ConfiguracionTramo) => c.pasajeros.every((p) => Object.keys(erroresPasajero(p)).length === 0)

function ConfiguradorTramo({ etiqueta, vuelo, configuracion, mostrarErrores, onChange }: ConfiguradorTramoProps) {
  const disponibles = asientosDe(vuelo, configuracion.clase)
  const errorValidacion = validarReglasReserva(configuracion.cantidad, disponibles)

  function cambiarCantidad(cantidad: number) {
    if (cantidad < MINIMO_PASAJES || cantidad > MAXIMO_PASAJES) return
    const pasajeros = [...configuracion.pasajeros]
    if (cantidad > pasajeros.length) {
      for (let i = pasajeros.length; i < cantidad; i++) {
        pasajeros.push({ nombre_pasajero: '', apellido_pasajero: '', dni_pasajero: '' })
      }
    } else {
      pasajeros.length = cantidad
    }
    onChange({ ...configuracion, cantidad, pasajeros })
  }

  function actualizarPasajero(indice: number, campo: keyof PasajeroInput, valor: string) {
    const pasajeros = [...configuracion.pasajeros]
    pasajeros[indice] = { ...pasajeros[indice], [campo]: valor }
    onChange({ ...configuracion, pasajeros })
  }

  return (
    <section aria-label={`Reserva de ${etiqueta.toLowerCase()}`} className="rounded-2xl border border-slate-200 p-4 sm:p-5">
      <div className="border-b border-slate-100 pb-4">
        <h3 className="font-extrabold text-marino">Reserva de {etiqueta}</h3>
        <p className="mt-1 text-sm font-semibold text-slate-700">
          {vuelo.origen.ciudad} ({vuelo.origen.codigo_iata}) → {vuelo.destino.ciudad} ({vuelo.destino.codigo_iata})
        </p>
        <p className="mt-1 text-sm text-slate-500">
          {fechaCompleta(vuelo.fecha_operacion)} - Salida: {hora(vuelo.hora_partida)} | Llegada: {hora(vuelo.hora_llegada)}
        </p>
      </div>

      <fieldset className="mt-4">
        <legend className="mb-2 text-sm font-bold text-slate-700">Clase para la {etiqueta.toLowerCase()}</legend>
        <div className="grid grid-cols-2 gap-3">
          {(['economy', 'primera'] as Clase[]).map((clase) => {
            const asientos = asientosDe(vuelo, clase)
            const seleccionada = configuracion.clase === clase
            return (
              <button
                type="button"
                key={clase}
                aria-pressed={seleccionada}
                onClick={() => onChange({ ...configuracion, clase })}
                className={`rounded-2xl border p-3 text-left transition-all ${
                  seleccionada ? 'border-marino bg-marino/5 ring-2 ring-marino' : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="font-extrabold text-marino">{NOMBRE_CLASE[clase]}</span>
                  <span className="text-xs font-semibold text-slate-500">
                    {asientos} {asientos === 1 ? 'disponible' : 'disponibles'}
                  </span>
                </span>
                <span className="mt-2 block font-bold text-slate-900">{precio(precioDe(vuelo, clase))} por pasaje</span>
              </button>
            )
          })}
        </div>
      </fieldset>

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between">
          <label htmlFor={`cantidad-pasajes-${etiqueta}`} className="text-sm font-bold text-slate-700">
            Pasajeros para la {etiqueta.toLowerCase()} (máx. 9)
          </label>
          <span className="text-xs text-slate-500">
            Disponibles: <strong className="text-marino">{disponibles}</strong>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => cambiarCantidad(configuracion.cantidad - 1)}
            disabled={configuracion.cantidad <= MINIMO_PASAJES}
            aria-label={`Quitar un pasajero de la ${etiqueta.toLowerCase()}`}
            className="h-11 w-11 rounded-xl border border-slate-300 bg-white text-xl font-bold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            −
          </button>
          <input
            id={`cantidad-pasajes-${etiqueta}`}
            type="number"
            min={MINIMO_PASAJES}
            max={MAXIMO_PASAJES}
            value={configuracion.cantidad}
            onChange={(e) => cambiarCantidad(Number(e.target.value))}
            className="h-11 w-20 rounded-xl border border-slate-300 text-center text-lg font-extrabold outline-none focus:border-marino focus:ring-1 focus:ring-marino"
          />
          <button
            type="button"
            onClick={() => cambiarCantidad(configuracion.cantidad + 1)}
            disabled={configuracion.cantidad >= MAXIMO_PASAJES || configuracion.cantidad >= disponibles}
            aria-label={`Agregar un pasajero a la ${etiqueta.toLowerCase()}`}
            className="h-11 w-11 rounded-xl border border-slate-300 bg-white text-xl font-bold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            +
          </button>
        </div>
        {errorValidacion && <p role="alert" className="mt-2 text-xs font-semibold text-red-600">{errorValidacion}</p>}
      </div>

      <div className="mt-4 border-t border-slate-100 pt-4">
        <h4 className="mb-3 text-sm font-bold text-slate-700">Datos de los pasajeros de la {etiqueta.toLowerCase()}</h4>
        <div className="space-y-3">
          {configuracion.pasajeros.map((pasajero, indice) => {
            const errores = erroresPasajero(pasajero)
            return (
              <div key={indice} className="rounded-xl border border-slate-200 bg-white p-3">
                <p className="mb-2 text-xs font-bold text-marino">Pasajero {indice + 1}</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {([
                    ['nombre_pasajero', 'Nombre', 'Ej. Juan'],
                    ['apellido_pasajero', 'Apellido', 'Ej. Pérez'],
                    ['dni_pasajero', 'DNI', 'Ej. 12345678'],
                  ] as const).map(([campo, titulo, placeholder]) => {
                    const error = mostrarErrores || pasajero[campo].trim() ? errores[campo] : undefined
                    return (
                      <label key={campo} className="text-[11px] font-semibold text-slate-500">
                        {titulo}
                        <input
                          type="text"
                          required
                          value={pasajero[campo] ?? ''}
                          onChange={(e) => actualizarPasajero(indice, campo, e.target.value)}
                          placeholder={placeholder}
                          aria-invalid={Boolean(error)}
                          className={`mt-1 w-full rounded-lg border px-2.5 py-1.5 text-sm font-normal text-slate-900 outline-none focus:border-marino ${
                            error ? 'border-red-400' : 'border-slate-200'
                          }`}
                        />
                        {error && <span role="alert" className="mt-1 block font-medium text-red-600">{error}</span>}
                      </label>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <p className="mt-4 text-right text-sm font-bold text-marino">
        Subtotal {etiqueta.toLowerCase()}: {precio(precioDe(vuelo, configuracion.clase) * configuracion.cantidad)}
      </p>
    </section>
  )
}

export default function ModalReserva({
  vuelo,
  vueloVuelta,
  claseInicial = 'economy',
  pasajerosInicial = 1,
  onCerrar,
}: Props) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const navigate = useNavigate()
  const { pathname, search } = useLocation()
  const { usuario } = useSesion()
  const [cargando, setCargando] = useState(false)
  const [errorApi, setErrorApi] = useState<string | null>(null)
  const [intentado, setIntentado] = useState(false)
  const cantidadInicial = Math.max(MINIMO_PASAJES, Math.min(pasajerosInicial, MAXIMO_PASAJES))
  const crearConfiguracionInicial = (): ConfiguracionTramo => ({
    clase: claseInicial,
    cantidad: cantidadInicial,
    pasajeros: Array.from({ length: cantidadInicial }, (_, i) => ({
      nombre_pasajero: i === 0 && usuario ? usuario.nombre : '',
      apellido_pasajero: i === 0 && usuario ? usuario.apellido : '',
      dni_pasajero: '',
    })),
  })
  const [configuracionIda, setConfiguracionIda] = useState<ConfiguracionTramo>(crearConfiguracionInicial)
  const [configuracionVuelta, setConfiguracionVuelta] = useState<ConfiguracionTramo>(crearConfiguracionInicial)

  useEffect(() => {
    const d = dialogo.current
    if (d && !d.open) d.showModal()
  }, [])

  const errorIda = validarReglasReserva(configuracionIda.cantidad, asientosDe(vuelo, configuracionIda.clase))
  const errorVuelta = vueloVuelta
    ? validarReglasReserva(configuracionVuelta.cantidad, asientosDe(vueloVuelta, configuracionVuelta.clase))
    : null
  const totalIda = precioDe(vuelo, configuracionIda.clase) * configuracionIda.cantidad
  const totalVuelta = vueloVuelta ? precioDe(vueloVuelta, configuracionVuelta.clase) * configuracionVuelta.cantidad : 0
  const total = totalIda + totalVuelta

  async function confirmar(e: React.FormEvent) {
    e.preventDefault()
    if (!usuario) return
    if (errorIda || errorVuelta) return
    setIntentado(true)
    if (!pasajerosValidos(configuracionIda) || (vueloVuelta && !pasajerosValidos(configuracionVuelta))) return

    setCargando(true)
    setErrorApi(null)

    try {
      if (vueloVuelta) {
        await crearReservaIdaVuelta({
          vuelo_ida: vuelo.id,
          vuelo_vuelta: vueloVuelta.id,
          ida: {
            clase: configuracionIda.clase,
            cantidad_pasajes: configuracionIda.cantidad,
            pasajeros: configuracionIda.pasajeros,
          },
          vuelta: {
            clase: configuracionVuelta.clase,
            cantidad_pasajes: configuracionVuelta.cantidad,
            pasajeros: configuracionVuelta.pasajeros,
          },
        })
        dialogo.current?.close()
        navigate('/reservas')
        return
      }

      const reserva = await crearReserva({
        vuelo_id: vuelo.id,
        clase: configuracionIda.clase,
        cantidad_pasajes: configuracionIda.cantidad,
        pasajeros: configuracionIda.pasajeros,
      })
      dialogo.current?.close()
      navigate(`/pagar/${reserva.id}`)
    } catch (err) {
      setErrorApi(err instanceof Error ? err.message : 'No se pudo crear la reserva.')
    } finally {
      setCargando(false)
    }
  }

  const cerrar = () => dialogo.current?.close()

  return (
    <dialog
      ref={dialogo}
      onClose={onCerrar}
      aria-labelledby="titulo-reserva"
      className="m-auto max-h-[90vh] w-[min(42rem,calc(100%-2rem))] overflow-y-auto rounded-3xl p-0 text-slate-900 shadow-2xl backdrop:bg-marino/45"
    >
      <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
        <div>
          <h2 id="titulo-reserva" className="text-xl font-extrabold text-marino">
            {vueloVuelta ? 'Reservar ida y vuelta' : 'Reservar pasajes'}
          </h2>
          <p className="text-xs text-slate-500">
            Vuelo {vuelo.numero_vuelo} - {vuelo.origen.codigo_iata} → {vuelo.destino.codigo_iata}
          </p>
        </div>
        <button
          type="button"
          onClick={cerrar}
          aria-label="Cerrar"
          className="grid h-9 w-9 place-items-center rounded-full text-xl text-slate-500 hover:bg-slate-100"
        >
          ✕
        </button>
      </div>

      <form onSubmit={confirmar} noValidate className="space-y-4 p-5 sm:p-6">
        <p className="text-sm text-slate-600">
          Configurá cada tramo por separado. Podés elegir distinta clase, cantidad de pasajeros y datos para la ida y la vuelta.
        </p>
        <ConfiguradorTramo
          etiqueta="Ida"
          vuelo={vuelo}
          configuracion={configuracionIda}
          mostrarErrores={intentado}
          onChange={setConfiguracionIda}
        />
        {vueloVuelta && (
          <ConfiguradorTramo
            etiqueta="Vuelta"
            vuelo={vueloVuelta}
            configuracion={configuracionVuelta}
            mostrarErrores={intentado}
            onChange={setConfiguracionVuelta}
          />
        )}

        {/* Alerta de sesión */}
        {!usuario && (
          <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <p className="font-bold">Iniciá sesión para reservar</p>
            <p className="mt-1">Para completar la reserva de pasajes necesitás ingresar con tu cuenta de pasajero.</p>
            {/* La URL tiene la búsqueda y los vuelos elegidos: tras el login se vuelve a ellos. */}
            <Link to="/login" state={{ desde: pathname + search }} className="mt-2 inline-block font-bold text-marino underline">
              Iniciar sesión
            </Link>
          </div>
        )}

        {/* Error API */}
        {errorApi && (
          <div role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 font-medium">
            {errorApi}
          </div>
        )}

        {/* Total y botón */}
        <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-100 pt-4">
          <div>
            <p className="text-xs text-slate-500">
              {vueloVuelta ? 'Total de ambas reservas' : `Total (${configuracionIda.cantidad} ${
                configuracionIda.cantidad === 1 ? 'pasaje' : 'pasajes'
              }, ${NOMBRE_CLASE[configuracionIda.clase]})`}
            </p>
            <p className="text-2xl font-extrabold text-marino">{precio(total)}</p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={cerrar}
              className="rounded-xl border border-slate-300 bg-white px-5 py-2.5 font-bold text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={cargando || !usuario || Boolean(errorIda || errorVuelta)}
              className="rounded-xl bg-naranja px-6 py-2.5 font-bold text-white hover:bg-naranja/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {cargando ? 'Reservando...' : vueloVuelta ? 'Reservar ida y vuelta' : 'Confirmar reserva'}
            </button>
          </div>
        </div>
      </form>
    </dialog>
  )
}
