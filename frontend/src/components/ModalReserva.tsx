import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { NOMBRE_CLASE, type Clase } from '../lib/busqueda'
import { fechaCompleta, hora, precio } from '../lib/formato'
import {
  crearReserva,
  crearReservaIdaVuelta,
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

export default function ModalReserva({
  vuelo,
  vueloVuelta,
  claseInicial = 'economy',
  pasajerosInicial = 1,
  onCerrar,
}: Props) {
  const dialogo = useRef<HTMLDialogElement>(null)
  const navigate = useNavigate()
  const { usuario } = useSesion()

  const [clase, setClase] = useState<Clase>(claseInicial)
  const [cantidad, setCantidad] = useState<number>(Math.max(MINIMO_PASAJES, Math.min(pasajerosInicial, MAXIMO_PASAJES)))
  const [cargando, setCargando] = useState(false)
  const [errorApi, setErrorApi] = useState<string | null>(null)

  // Datos de cada pasajero
  const [pasajeros, setPasajeros] = useState<PasajeroInput[]>(() => {
    return Array.from({ length: cantidad }, (_, i) => ({
      nombre_pasajero: i === 0 && usuario ? usuario.nombre : '',
      apellido_pasajero: i === 0 && usuario ? usuario.apellido : '',
      dni_pasajero: '',
    }))
  })

  useEffect(() => {
    const d = dialogo.current
    if (d && !d.open) d.showModal()
  }, [])

  // Al cambiar la cantidad, ajustar el tamaño del array de pasajeros conservando lo escrito
  function cambiarCantidad(nueva: number) {
    if (nueva < MINIMO_PASAJES || nueva > MAXIMO_PASAJES) return
    setCantidad(nueva)
    setPasajeros((prev) => {
      const actual = [...prev]
      if (nueva > actual.length) {
        for (let i = actual.length; i < nueva; i++) {
          actual.push({ nombre_pasajero: '', apellido_pasajero: '', dni_pasajero: '' })
        }
      } else {
        actual.length = nueva
      }
      return actual
    })
  }

  function actualizarPasajero(indice: number, campo: keyof PasajeroInput, valor: string) {
    setPasajeros((prev) => {
      const nuevo = [...prev]
      nuevo[indice] = { ...nuevo[indice], [campo]: valor }
      return nuevo
    })
  }

  const disponibles = vueloVuelta
    ? Math.min(asientosDe(vuelo, clase), asientosDe(vueloVuelta, clase))
    : asientosDe(vuelo, clase)
  const precioUnitario = precioDe(vuelo, clase)
  const total = (precioUnitario + (vueloVuelta ? precioDe(vueloVuelta, clase) : 0)) * cantidad
  const errorValidacion = validarReglasReserva(cantidad, disponibles)

  async function confirmar(e: React.FormEvent) {
    e.preventDefault()
    if (!usuario) return
    if (errorValidacion) return

    setCargando(true)
    setErrorApi(null)

    try {
      if (vueloVuelta) {
        await crearReservaIdaVuelta({
          vuelo_ida: vuelo.id,
          vuelo_vuelta: vueloVuelta.id,
          clase,
          cantidad_pasajes: cantidad,
          pasajeros,
        })
        dialogo.current?.close()
        navigate('/reservas')
        return
      }

      const reserva = await crearReserva({ vuelo_id: vuelo.id, clase, cantidad_pasajes: cantidad, pasajeros })
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
      className="m-auto max-h-[90vh] w-[min(42rem,calc(100%-2rem))] overflow-y-auto rounded-3xl p-0 text-slate-900 shadow-2xl backdrop:bg-marino/45 backdrop:backdrop-blur-sm"
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

      <form onSubmit={confirmar} className="p-5 sm:p-6 space-y-6">
        {/* Resumen del vuelo */}
        <div className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
          <p className="font-bold text-marino">
            {vuelo.origen.ciudad} ({vuelo.origen.codigo_iata}) → {vuelo.destino.ciudad} ({vuelo.destino.codigo_iata})
          </p>
          <p className="mt-1 text-sm text-slate-600">
            {fechaCompleta(vuelo.fecha_operacion)} - Salida: {hora(vuelo.hora_partida)} | Llegada: {hora(vuelo.hora_llegada)}
          </p>
          {vueloVuelta && (
            <>
              <p className="mt-3 font-bold text-marino">
                Vuelta: {vueloVuelta.origen.ciudad} ({vueloVuelta.origen.codigo_iata}) → {vueloVuelta.destino.ciudad} ({vueloVuelta.destino.codigo_iata})
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {fechaCompleta(vueloVuelta.fecha_operacion)} - Salida: {hora(vueloVuelta.hora_partida)} | Llegada: {hora(vueloVuelta.hora_llegada)}
              </p>
              <p className="mt-3 text-sm font-medium text-slate-600">
                Se crearán dos reservas independientes para pagar cada tramo por separado.
              </p>
            </>
          )}
        </div>

        {/* Selección de clase */}
        <div>
          <label className="block text-sm font-bold text-slate-700 mb-2">Clase</label>
          <div className="grid grid-cols-2 gap-3">
            {(['economy', 'primera'] as Clase[]).map((c) => {
              const asientos = asientosDe(vuelo, c)
              const seleccionada = clase === c
              return (
                <button
                  type="button"
                  key={c}
                  onClick={() => setClase(c)}
                  className={`rounded-2xl border p-4 text-left transition-all ${
                    seleccionada
                      ? 'border-marino bg-marino/5 ring-2 ring-marino'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-extrabold text-marino">{NOMBRE_CLASE[c]}</span>
                    <span className="text-xs font-semibold text-slate-500">
                      {asientos} {asientos === 1 ? 'disponible' : 'disponibles'}
                    </span>
                  </div>
                  <p className="mt-2 text-base font-bold text-slate-900">{precio(precioDe(vuelo, c))}</p>
                </button>
              )
            })}
          </div>
        </div>

        {/* Selección de cantidad */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label htmlFor="cantidad-pasajes" className="text-sm font-bold text-slate-700">
              Cantidad de pasajes (máx. 9)
            </label>
            <span className="text-xs text-slate-500">
              {vueloVuelta ? 'Disponibles en ambos tramos' : 'Disponibles'}:{' '}
              <strong className="text-marino">{disponibles}</strong>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => cambiarCantidad(cantidad - 1)}
              disabled={cantidad <= MINIMO_PASAJES}
              className="h-11 w-11 rounded-xl border border-slate-300 bg-white text-xl font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              −
            </button>
            <input
              id="cantidad-pasajes"
              type="number"
              min={MINIMO_PASAJES}
              max={MAXIMO_PASAJES}
              value={cantidad}
              onChange={(e) => cambiarCantidad(Number(e.target.value))}
              className="h-11 w-20 text-center font-extrabold text-lg rounded-xl border border-slate-300 focus:border-marino focus:ring-1 focus:ring-marino outline-none"
            />
            <button
              type="button"
              onClick={() => cambiarCantidad(cantidad + 1)}
              disabled={cantidad >= MAXIMO_PASAJES || cantidad >= disponibles}
              className="h-11 w-11 rounded-xl border border-slate-300 bg-white text-xl font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              +
            </button>
          </div>
          {errorValidacion && (
            <p role="alert" className="mt-2 text-xs font-semibold text-red-600">
              {errorValidacion}
            </p>
          )}
        </div>

        {/* Formulario de Pasajeros */}
        <div className="border-t border-slate-100 pt-4">
          <h3 className="text-sm font-bold text-slate-700 mb-3">Datos de los pasajeros</h3>
          <div className="space-y-4">
            {pasajeros.map((p, idx) => (
              <div key={idx} className="rounded-xl border border-slate-200 p-3 bg-white">
                <p className="text-xs font-bold text-marino mb-2">Pasajero {idx + 1}</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <div>
                    <label className="text-[11px] font-semibold text-slate-500">Nombre</label>
                    <input
                      type="text"
                      required
                      value={p.nombre_pasajero ?? ''}
                      onChange={(e) => actualizarPasajero(idx, 'nombre_pasajero', e.target.value)}
                      placeholder="Ej. Juan"
                      className="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm focus:border-marino outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-500">Apellido</label>
                    <input
                      type="text"
                      required
                      value={p.apellido_pasajero ?? ''}
                      onChange={(e) => actualizarPasajero(idx, 'apellido_pasajero', e.target.value)}
                      placeholder="Ej. Pérez"
                      className="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm focus:border-marino outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-semibold text-slate-500">DNI / Documento</label>
                    <input
                      type="text"
                      required
                      value={p.dni_pasajero ?? ''}
                      onChange={(e) => actualizarPasajero(idx, 'dni_pasajero', e.target.value)}
                      placeholder="Ej. 12345678"
                      className="w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-sm focus:border-marino outline-none"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Alerta de sesión */}
        {!usuario && (
          <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <p className="font-bold">Iniciá sesión para reservar</p>
            <p className="mt-1">Para completar la reserva de pasajes necesitás ingresar con tu cuenta de pasajero.</p>
            <Link to="/login" className="mt-2 inline-block font-bold text-marino underline">
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
              Total ({cantidad} {cantidad === 1 ? 'pasaje' : 'pasajes'}, {NOMBRE_CLASE[clase]})
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
              disabled={cargando || !usuario || Boolean(errorValidacion)}
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
