import { CLAVE_REFRESH, CLAVE_TOKEN } from './auth.ts'

export class ApiError extends Error {
  readonly status: number
  readonly data: unknown

  constructor(status: number, data: unknown) {
    super(mensajeError(data, status))
    this.status = status
    this.data = data
    this.name = 'ApiError'
  }
}

function mensajeError(data: unknown, status: number): string {
  // La API siempre responde JSON: un texto es la página de error de Django o del hosting, no un mensaje para mostrar.
  if (typeof data === 'string') return 'No pudimos conectar con el servidor. Probá de nuevo en unos minutos.'
  return primerMensaje(data) ?? `Error ${status}`
}

// DRF anida los errores como el pedido ({ pasajeros: [{}, { dni_pasajero: ['…'] }] }): el primer texto que aparezca.
function primerMensaje(valor: unknown): string | undefined {
  if (typeof valor === 'string') return valor
  if (!valor || typeof valor !== 'object') return undefined
  for (const hijo of Object.values(valor)) {
    const mensaje = primerMensaje(hijo)
    if (mensaje) return mensaje
  }
  return undefined
}

let renovacionEnCurso: Promise<string | null> | null = null

function renovarAccessToken(): Promise<string | null> {
  if (!renovacionEnCurso) {
    renovacionEnCurso = (async () => {
      const refresh = localStorage.getItem(CLAVE_REFRESH)
      if (!refresh) return null

      const response = await fetch(`${import.meta.env.VITE_API_URL}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (localStorage.getItem(CLAVE_REFRESH) !== refresh) return null
      if (!response.ok) {
        localStorage.removeItem(CLAVE_TOKEN)
        localStorage.removeItem(CLAVE_REFRESH)
        return null
      }

      const tokens = (await response.json()) as { access: string; refresh?: string }
      localStorage.setItem(CLAVE_TOKEN, tokens.access)
      if (tokens.refresh) localStorage.setItem(CLAVE_REFRESH, tokens.refresh)
      return tokens.access
    })().finally(() => {
      renovacionEnCurso = null
    })
  }
  return renovacionEnCurso
}

async function solicitar(path: string, init: RequestInit): Promise<Response> {
  const enviar = (token: string | null) => {
    const headers = new Headers(init.headers)
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
    if (token) headers.set('Authorization', `Bearer ${token}`)
    return fetch(`${import.meta.env.VITE_API_URL}${path}`, { ...init, headers })
  }

  let res = await enviar(localStorage.getItem(CLAVE_TOKEN))
  if (
    res.status === 401 &&
    !path.endsWith('/token/refresh/') &&
    localStorage.getItem(CLAVE_REFRESH)
  ) {
    const access = await renovarAccessToken()
    if (access) {
      res = await enviar(access)
      if (res.status === 401) {
        localStorage.removeItem(CLAVE_TOKEN)
        localStorage.removeItem(CLAVE_REFRESH)
      }
    }
  }

  if (!res.ok) {
    const body = await res.text()
    let data: unknown = body
    try {
      data = JSON.parse(body)
    } catch {
      // Respuestas no JSON (página de error de Django o del hosting): ApiError muestra un mensaje fijo.
    }
    throw new ApiError(res.status, data)
  }
  return res
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await solicitar(path, init)
  return res.json()
}

export async function apiBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const res = await solicitar(path, init)
  return res.blob()
}
