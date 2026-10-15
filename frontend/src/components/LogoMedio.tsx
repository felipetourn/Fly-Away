import { NOMBRE_MARCA, type Pago } from '../lib/pagos'

const CAJA = 'grid h-8 w-12 shrink-0 place-items-center rounded-md border text-[10px] font-extrabold'

/** Insignia del medio de pago: el logo de Mercado Pago o de la tarjeta (public/medios); Amex, sin logo, va como texto. */
export default function LogoMedio({ pago }: { pago: Pick<Pago, 'metodo_pago' | 'marca'> }) {
  if (pago.metodo_pago === 'mercadopago')
    return (
      <span title="Mercado Pago" className={`${CAJA} border-slate-200 bg-white`}>
        <img src="/medios/mercadopago.svg" alt="Mercado Pago" className="h-6" />
      </span>
    )
  if (pago.marca === 'mastercard' || pago.marca === 'visa')
    return (
      <span title={NOMBRE_MARCA[pago.marca]} className={`${CAJA} border-slate-200 bg-white`}>
        <img src={`/medios/${pago.marca}.svg`} alt={NOMBRE_MARCA[pago.marca]} className="max-h-4 max-w-9" />
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
