export interface Usuario {
  id: string
  email: string
  nombre: string
  apellido: string
  rol: 'administrador' | 'empleado_mostrador' | 'pasajero'
}

export const CLAVE_TOKEN = 'access'
export const CLAVE_REFRESH = 'refresh'

export function iniciales(u: Usuario): string {
  return `${u.nombre.charAt(0)}${u.apellido.charAt(0)}`.toUpperCase()
}

export function inicioPorRol(rol: Usuario['rol']): string {
  if (rol === 'administrador') return '/admin'
  if (rol === 'empleado_mostrador') return '/mostrador'
  return '/'
}
