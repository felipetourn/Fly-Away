export type Clase = 'economy' | 'primera'

export const NOMBRE_CLASE: Record<Clase, string> = { economy: 'Economy', primera: 'Primera' }

export const MAX_PASAJEROS = 9

/**
 * Filtros de búsqueda. Fechas en YYYY-MM-DD.
 * - `vuelta: null` = solo ida (explorador): origen o destino pueden ser '' (cualquiera).
 * - `vuelta: string` = ida y vuelta: origen y destino obligatorios.
 * - `hasta` arma un rango con `ida` ('' = solo ese día); `vueltaHasta` lo mismo con `vuelta` (siempre '' en solo ida).
 * - `precioMin` / `precioMax`: por persona en la clase elegida; `null` = sin límite.
 */
export interface Filtros {
  origen: string
  destino: string
  ida: string
  hasta: string
  vuelta: string | null
  vueltaHasta: string
  pasajeros: number
  clase: Clase
  precioMin: number | null
  precioMax: number | null
}

export type ErroresBusqueda = Partial<
  Record<'origen' | 'destino' | 'ida' | 'hasta' | 'vuelta' | 'vueltaHasta' | 'pasajeros' | 'clase' | 'precio', string>
>

/** Lo mínimo de un aeropuerto que necesita la validación. */
export interface AeropuertoConocido {
  codigo_iata: string
  ciudad: string
}

const FECHA = /^\d{4}-\d{2}-\d{2}$/

/** YYYY-MM-DD que además existe en el calendario (descarta 2027-02-30). */
function fechaValida(v: string): boolean {
  return FECHA.test(v) && new Date(`${v}T00:00:00`).toLocaleDateString('sv-SE') === v
}

/** Fecha local de hoy en YYYY-MM-DD (sv-SE formatea así). */
export function hoyISO(): string {
  return new Date().toLocaleDateString('sv-SE')
}

/** Rango que se está eligiendo en el calendario. `abierto` = falta el día de fin. */
export interface RangoEnCurso {
  desde: string
  hasta: string
  abierto: boolean
}

/**
 * Clic en un día (YYYY-MM-DD) del calendario de rango: el primer clic marca el inicio y el segundo el fin.
 * El mismo día cierra un rango de un solo día; un día anterior al inicio pasa a ser el nuevo inicio.
 * Con un rango ya cerrado, el clic empieza uno nuevo.
 */
export function elegirDia(r: RangoEnCurso, dia: string): RangoEnCurso {
  if (!r.abierto || dia < r.desde) return { desde: dia, hasta: '', abierto: true }
  return { desde: r.desde, hasta: dia === r.desde ? '' : dia, abierto: false }
}

/** Error del rango de precio, o undefined si está bien. */
export function validarPrecio(min: number | null, max: number | null): string | undefined {
  const mal = (n: number | null) => n !== null && (!Number.isFinite(n) || n < 0)
  if (mal(min) || mal(max)) return 'Ingresá montos válidos'
  if (min !== null && max !== null && min > max) return 'El mínimo no puede ser mayor que el máximo'
  return undefined
}

/**
 * Solo UX: el backend repite estas reglas. Las fechas ISO se comparan como texto.
 * Con `aeropuertos` también rechaza códigos desconocidos y origen y destino en la misma ciudad.
 */
export function validarBusqueda(f: Filtros, hoy: string, aeropuertos?: AeropuertoConocido[]): ErroresBusqueda {
  const e: ErroresBusqueda = {}
  if (f.vuelta === null) {
    if (!f.origen && !f.destino) e.origen = 'Elegí un origen, un destino o ambos'
  } else {
    if (!f.origen) e.origen = 'Elegí un origen'
    if (!f.destino) e.destino = 'Elegí un destino'
  }
  if (f.origen && f.destino === f.origen) e.destino = 'El destino tiene que ser distinto del origen'
  if (aeropuertos) {
    const ciudad = (iata: string) => aeropuertos.find((a) => a.codigo_iata === iata)?.ciudad
    if (f.origen && !ciudad(f.origen)) e.origen = 'No conocemos ese aeropuerto'
    if (f.destino && !ciudad(f.destino)) e.destino = 'No conocemos ese aeropuerto'
    else if (!e.destino && f.origen && f.destino && ciudad(f.origen) === ciudad(f.destino)) {
      e.destino = 'Origen y destino están en la misma ciudad'
    }
  }
  if (!f.ida) e.ida = 'Elegí la fecha'
  else if (f.ida < hoy) e.ida = 'La fecha no puede ser en el pasado'
  if (f.hasta && f.ida && f.hasta < f.ida) {
    e.hasta = f.vuelta === null ? 'No puede ser antes de "Desde"' : 'No puede ser antes de la ida'
  }
  if (f.vuelta !== null) {
    if (!f.vuelta) e.vuelta = 'Elegí la fecha de vuelta'
    else if (f.ida && f.vuelta < f.ida) e.vuelta = 'La vuelta no puede ser antes de la ida'
    if (f.vueltaHasta && f.vuelta && f.vueltaHasta < f.vuelta) e.vueltaHasta = 'No puede ser antes de la vuelta'
  }
  if (f.clase !== 'economy' && f.clase !== 'primera') e.clase = 'Elegí Economy o Primera'
  if (!Number.isInteger(f.pasajeros) || f.pasajeros < 1 || f.pasajeros > MAX_PASAJEROS) {
    e.pasajeros = `Entre 1 y ${MAX_PASAJEROS} pasajeros`
  }
  const precio = validarPrecio(f.precioMin, f.precioMax)
  if (precio) e.precio = precio
  return e
}

/** Lee la búsqueda de la URL. `null` si no hay búsqueda. No valida: eso lo hace `validarBusqueda`. */
export function leerFiltros(p: URLSearchParams): Filtros | null {
  if (!p.has('ida')) return null
  const fecha = (clave: string) => {
    const v = p.get(clave) ?? ''
    return fechaValida(v) ? v : ''
  }
  const monto = (clave: string) => {
    const v = p.get(clave)
    return v === null || v === '' ? null : Number(v)
  }
  const idaYVuelta = p.has('vuelta')
  return {
    origen: (p.get('origen') ?? '').toUpperCase(),
    destino: (p.get('destino') ?? '').toUpperCase(),
    ida: fecha('ida'),
    hasta: fecha('hasta'),
    vuelta: idaYVuelta ? fecha('vuelta') : null,
    vueltaHasta: idaYVuelta ? fecha('vueltaHasta') : '',
    pasajeros: Number(p.get('pasajeros') ?? 1),
    // Un valor desconocido se conserva para que validarBusqueda lo marque (no se cambia en silencio).
    clase: (p.get('clase') ?? 'economy') as Clase,
    precioMin: monto('precioMin'),
    precioMax: monto('precioMax'),
  }
}

/** Filtros → query string. Nunca incluye `idaId`: una búsqueda nueva empieza de cero. */
export function aParams(f: Filtros): URLSearchParams {
  const p = new URLSearchParams()
  if (f.origen) p.set('origen', f.origen)
  if (f.destino) p.set('destino', f.destino)
  p.set('ida', f.ida)
  if (f.hasta) p.set('hasta', f.hasta)
  if (f.vuelta !== null) {
    p.set('vuelta', f.vuelta)
    if (f.vueltaHasta) p.set('vueltaHasta', f.vueltaHasta)
  }
  p.set('pasajeros', String(f.pasajeros))
  p.set('clase', f.clase)
  if (f.precioMin !== null) p.set('precioMin', String(f.precioMin))
  if (f.precioMax !== null) p.set('precioMax', String(f.precioMax))
  return p
}
