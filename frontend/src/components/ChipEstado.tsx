import { ETIQUETA_ESTADO, type EstadoPago } from '../lib/pagos'

const COLORES: Record<EstadoPago, string> = {
  aprobado: 'bg-emerald-50 text-emerald-700',
  rechazado: 'bg-red-50 text-red-700',
  pendiente: 'bg-amber-50 text-amber-700',
}

export default function ChipEstado({ estado, texto }: { estado: EstadoPago; texto?: string }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-bold whitespace-nowrap ${COLORES[estado]}`}>
      {texto ?? ETIQUETA_ESTADO[estado]}
    </span>
  )
}
