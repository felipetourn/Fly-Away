export interface Usuario {
  id: string
  email: string
  nombre: string
  apellido: string
  rol: 'administrador' | 'empleado_mostrador' | 'pasajero'
}

// ponytail: sesión mock. Con backend: login = POST /auth/token/ y usuarioActual = api('/auth/yo/') (async).
const USUARIO_DEMO: Usuario = {
  id: 'demo',
  email: 'felipe@flyaway.com',
  nombre: 'Felipe',
  apellido: 'Tourn',
  rol: 'pasajero',
}

/** Misma clave que usa api.ts para el JWT. */
export const CLAVE_TOKEN = 'access'

export function usuarioActual(): Usuario | null {
  return localStorage.getItem(CLAVE_TOKEN) ? USUARIO_DEMO : null
}

export function iniciales(u: Usuario): string {
  return `${u.nombre.charAt(0)}${u.apellido.charAt(0)}`.toUpperCase()
}
