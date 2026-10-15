import { ETIQUETA_ESTADO, type EstadoPago } from '../lib/pagos'

const COLORES: Record<EstadoPago, string> = {
  aprobado: 'bg-emerald-100 text-emerald-800',
  rechazado: 'bg-red-100 text-red-800',
  pendiente: 'bg-amber-100 text-amber-800',
}

export default function ChipEstado({ estado, texto }: { estado: EstadoPago; texto?: string }) {
  return (
    <span className={`inline-block rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap ${COLORES[estado]}`}>
      {texto ?? ETIQUETA_ESTADO[estado]}
    </span>
  )
}
