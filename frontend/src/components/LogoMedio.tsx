import { NOMBRE_MARCA, type Pago } from '../lib/pagos'

const CAJA = 'grid h-8 w-12 shrink-0 place-items-center rounded-md border text-[10px] font-extrabold'

/** Insignia del medio de pago: el logo de Mercado Pago (public/medios) o la marca de la tarjeta. */
export default function LogoMedio({ pago }: { pago: Pick<Pago, 'metodo_pago' | 'marca'> }) {
  if (pago.metodo_pago === 'mercadopago')
    return (
      <span title="Mercado Pago" className={`${CAJA} border-slate-200 bg-white`}>
        <img src="/medios/mercadopago.svg" alt="Mercado Pago" className="h-6" />
      </span>
    )
  if (pago.marca === 'mastercard')
    return (
      <span title={NOMBRE_MARCA.mastercard} className={`${CAJA} border-slate-200 bg-white`}>
        <svg viewBox="0 0 32 20" className="h-5 w-8" aria-hidden="true">
          <circle cx="12" cy="10" r="8" fill="#eb001b" />
          <circle cx="20" cy="10" r="8" fill="#f79e1b" fillOpacity="0.9" />
        </svg>
      </span>
    )
  if (pago.marca === 'visa')
    return (
      <span title={NOMBRE_MARCA.visa} className={`${CAJA} border-slate-200 bg-white text-xs text-[#1a1f71] italic`}>
        VISA
      </span>
    )
  if (pago.marca === 'amex')
    return (
      <span title={NOMBRE_MARCA.amex} className={`${CAJA} border-[#2e77bc] bg-[#2e77bc] text-white`}>
        AMEX
      </span>
    )
  return (
    <span title="Tarjeta" className={`${CAJA} border-slate-200 bg-slate-50 text-slate-500`}>
      ••••
    </span>
  )
}
