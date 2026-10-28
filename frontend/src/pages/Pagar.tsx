import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AvionCargando from '../components/AvionCargando'
import { EsqueletoPagina } from '../components/Esqueleto'
import { erroresDe, primero } from '../lib/adminVuelos'
import { ApiError } from '../lib/api'
import { fechaCorta, hora, precio } from '../lib/formato'
import {
  DATOS_PRUEBA,
  erroresTarjeta,
  formatearNumero,
  formatearVencimiento,
  marcaDe,
  NOMBRE_MARCA,
  pagarConMercadoPago,
  pagarConTarjeta,
  pasajesDe,
  soloDigitos,
  TARJETAS_PRUEBA,
  vueloCorto,
  type DatosTarjeta,
  type ErroresTarjeta,
} from '../lib/pagos'
import { getReserva, type Reserva } from '../lib/reservas'

const VACIA: DatosTarjeta = { numero: '', titular: '', vencimiento: '', cvv: '' }
const CAMPOS = ['numero', 'titular', 'vencimiento', 'cvv'] as const
const CAMPO =
  'mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-marino focus:ring-2 focus:ring-marino/20'
// ponytail: la pasarela simulada responde al instante; la espera imita a una real. Sacar con una pasarela de verdad.
const ESPERA_TARJETA_MS = 2500
const COLOR_RESULTADO = { ok: 'text-emerald-700', error: 'text-red-700', aviso: 'text-amber-700' }

export default function Pagar() {
  const { reservaId } = useParams()
  const navigate = useNavigate()
  const [reserva, setReserva] = useState<Reserva | null | undefined>(undefined) // undefined = cargando, null = no existe
  const [medio, setMedio] = useState<'tarjeta' | 'mercadopago'>('tarjeta')
  const [tarjeta, setTarjeta] = useState<DatosTarjeta>(VACIA)
  const [errores, setErrores] = useState<ErroresTarjeta>({})
  const [error, setError] = useState('')
  const [procesando, setProcesando] = useState(false)

  useEffect(() => {
    getReserva(reservaId ?? '')
      .then(setReserva)
      .catch((e: Error) => {
        setReserva(null)
        if (!(e instanceof ApiError && e.status === 404)) setError(e.message)
      })
  }, [reservaId])

  if (reserva === undefined) return <EsqueletoPagina angosta />
  if (reserva === null)
    return (
      <main className="mx-auto max-w-xl px-4 py-16">
        <h1 className="text-3xl font-extrabold text-marino">No encontramos la reserva</h1>
        {error && <p role="alert" className="mt-4 text-sm font-medium text-red-700">{error}</p>}
        <Link to="/reservas" className="mt-6 inline-block font-bold text-cielo hover:underline">Volver a mis reservas</Link>
      </main>
    )

  const cambiar = (campo: keyof DatosTarjeta, valor: string) => {
    const formateado =
      campo === 'numero' ? formatearNumero(valor) : campo === 'vencimiento' ? formatearVencimiento(valor) : campo === 'cvv' ? soloDigitos(valor).slice(0, 4) : valor
    setTarjeta((t) => ({ ...t, [campo]: formateado }))
    setErrores((e) => ({ ...e, [campo]: undefined }))
  }

  const pagarTarjeta = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    const locales = erroresTarjeta(tarjeta)
    setErrores(locales)
    if (Object.keys(locales).length) return
    setProcesando(true)
    const espera = new Promise((listo) => setTimeout(listo, ESPERA_TARJETA_MS))
    try {
      const pago = await pagarConTarjeta(reserva.id, tarjeta)
      await espera
      navigate(`/pagos/${pago.id}?recien=1`) // recien: avisa del envío de la factura
    } catch (err) {
      await espera
      const delBackend = erroresDe(err)
      const porCampo = Object.fromEntries(CAMPOS.map((c) => [c, primero(delBackend[c])]).filter(([, m]) => m)) as ErroresTarjeta
      setErrores(porCampo)
      if (!Object.keys(porCampo).length) setError(err instanceof Error ? err.message : 'No pudimos procesar el pago.')
      setProcesando(false)
    }
  }

  const pagarMercadoPago = async () => {
    setError('')
    setProcesando(true)
    try {
      const { checkout_url } = await pagarConMercadoPago(reserva.id)
      window.location.assign(checkout_url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No pudimos conectar con Mercado Pago.')
      setProcesando(false)
    }
  }

  const marca = marcaDe(soloDigitos(tarjeta.numero))
  const opcion = (valor: typeof medio, texto: string) => (
    <button
      type="button"
      aria-pressed={medio === valor}
      onClick={() => {
        setMedio(valor)
        setError('')
      }}
      className={`flex-1 rounded-lg px-4 py-2 text-sm font-bold ${medio === valor ? 'bg-white text-marino shadow-sm' : 'text-slate-500 hover:text-marino'}`}
    >
      {texto}
    </button>
  )

  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">Pagar reserva</h1>

      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="font-bold text-marino">{vueloCorto(reserva.vuelo)}</p>
        <p className="mt-1 text-sm text-slate-500">
          {fechaCorta(reserva.vuelo.fecha_operacion)} - {hora(reserva.vuelo.hora_partida)} - {pasajesDe(reserva)}
        </p>
        <p className="mt-4 flex items-baseline justify-between border-t border-slate-100 pt-4">
          <span className="text-slate-500">Total</span>
          <span className="text-2xl font-extrabold">{precio(Number(reserva.monto))}</span>
        </p>
      </section>

      {reserva.estado === 'pagada' ? (
        <p className="mt-6 rounded-2xl bg-emerald-50 p-5 font-medium text-emerald-800">
          Esta reserva ya está pagada. <Link to="/perfil" className="font-bold underline">Ver mis pagos</Link>
        </p>
      ) : (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {procesando ? (
            <AvionCargando
              texto={medio === 'tarjeta' ? 'Validando tu tarjeta…' : 'Conectando con Mercado Pago…'}
              detalle="No cierres ni recargues esta página."
            />
          ) : (
            <>
              <div className="flex gap-1 rounded-xl bg-slate-100 p-1">
                {opcion('tarjeta', 'Tarjeta')}
                {opcion('mercadopago', 'Mercado Pago')}
              </div>

              {medio === 'tarjeta' ? (
                <form onSubmit={pagarTarjeta} noValidate className="mt-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="font-bold text-marino">Tarjeta de crédito o débito</p>
                    <button type="button" popoverTarget="tarjetas-prueba" className="text-sm font-bold text-cielo hover:underline">
                      ⓘ Tarjetas de prueba
                    </button>
                  </div>
                  <div
                    id="tarjetas-prueba"
                    popover="auto"
                    className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-2xl border border-slate-200 bg-white p-5 shadow-xl backdrop:bg-slate-900/30"
                  >
                    <p className="font-bold text-marino">Tarjetas de prueba</p>
                    <p className="mt-1 text-sm text-slate-500">Tocá una para completar el formulario.</p>
                    <ul className="mt-3 divide-y divide-slate-100">
                      {TARJETAS_PRUEBA.map((t) => (
                        <li key={t.numero}>
                          <button
                            type="button"
                            popoverTarget="tarjetas-prueba"
                            popoverTargetAction="hide"
                            onClick={() => {
                              setTarjeta({ numero: t.numero, ...DATOS_PRUEBA })
                              setErrores({})
                            }}
                            className="flex w-full items-center justify-between gap-3 rounded-lg px-2 py-2.5 text-left hover:bg-slate-50"
                          >
                            <span className="flex items-center gap-3">
                          <span className="grid w-9 shrink-0 place-items-center">
                            <img src={`/medios/${t.marca}.svg`} alt={NOMBRE_MARCA[t.marca]} className="max-h-4 max-w-9" />
                          </span>
                          <span className="font-mono text-sm">{t.numero}</span>
                        </span>
                            <span className={`text-sm font-bold ${COLOR_RESULTADO[t.tono]}`}>{t.resultado}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-3 text-xs text-slate-500">Titular y CVV: cualquiera. Vencimiento: cualquier fecha futura.</p>
                  </div>

                  <label className="block text-sm font-bold text-slate-700">
                    Número de tarjeta {marca && <span className="font-normal text-slate-500">- {NOMBRE_MARCA[marca]}</span>}
                    <input
                      value={tarjeta.numero}
                      onChange={(e) => cambiar('numero', e.target.value)}
                      inputMode="numeric"
                      autoComplete="off"
                      placeholder="1234 5678 9012 3456"
                      aria-invalid={Boolean(errores.numero)}
                      className={CAMPO}
                    />
                    {errores.numero && <span className="mt-1 block font-medium text-red-700">{errores.numero}</span>}
                  </label>
                  <label className="block text-sm font-bold text-slate-700">
                    Titular (como figura en la tarjeta)
                    <input
                      value={tarjeta.titular}
                      onChange={(e) => cambiar('titular', e.target.value)}
                      autoComplete="off"
                      aria-invalid={Boolean(errores.titular)}
                      className={CAMPO}
                    />
                    {errores.titular && <span className="mt-1 block font-medium text-red-700">{errores.titular}</span>}
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    <label className="block text-sm font-bold text-slate-700">
                      Vencimiento
                      <input
                        value={tarjeta.vencimiento}
                        onChange={(e) => cambiar('vencimiento', e.target.value)}
                        inputMode="numeric"
                        autoComplete="off"
                        placeholder="MM/AA"
                        aria-invalid={Boolean(errores.vencimiento)}
                        className={CAMPO}
                      />
                      {errores.vencimiento && <span className="mt-1 block font-medium text-red-700">{errores.vencimiento}</span>}
                    </label>
                    <label className="block text-sm font-bold text-slate-700">
                      CVV
                      <input
                        value={tarjeta.cvv}
                        onChange={(e) => cambiar('cvv', e.target.value)}
                        inputMode="numeric"
                        autoComplete="off"
                        placeholder="123"
                        aria-invalid={Boolean(errores.cvv)}
                        className={CAMPO}
                      />
                      {errores.cvv && <span className="mt-1 block font-medium text-red-700">{errores.cvv}</span>}
                    </label>
                  </div>
                  {error && <p role="alert" className="text-sm font-medium text-red-700">{error}</p>}
                  <button
                    type="submit"
                    disabled={procesando}
                    className="w-full rounded-xl bg-naranja px-5 py-3 font-bold text-white hover:bg-naranja/90 disabled:opacity-60"
                  >
                    {procesando ? 'Procesando pago…' : `Pagar ${precio(Number(reserva.monto))}`}
                  </button>
                </form>
              ) : (
                <div className="mt-5 space-y-4">
                  <p className="text-slate-600">Te llevamos a Mercado Pago para completar el pago y después volvés acá con el resultado.</p>
                  {error && <p role="alert" className="text-sm font-medium text-red-700">{error}</p>}
                  <button
                    type="button"
                    onClick={pagarMercadoPago}
                    disabled={procesando}
                    className="w-full rounded-xl bg-cielo px-5 py-3 font-bold text-white hover:bg-cielo/90 disabled:opacity-60"
                  >
                    {procesando ? 'Procesando pago…' : 'Pagar con Mercado Pago'}
                  </button>
                  <p className="rounded-xl bg-slate-50 p-3 text-xs text-slate-500">
                    Sandbox: iniciá sesión con el comprador de prueba y pagá con la Mastercard 5031 7557 3453 0604, CVV 123,
                    vencimiento 11/30. Titular APRO = aprobada, OTHE = rechazada.
                  </p>
                </div>
              )}
            </>
          )}
        </section>
      )}
    </main>
  )
}
