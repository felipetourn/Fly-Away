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

// Opciones del header según el rol; sin sesión se muestran las del pasajero.
// Solo resuelve navegación: el permiso real lo valida cada endpoint del backend.
export const MENU: Record<Usuario['rol'], { to: string; texto: string }[]> = {
  pasajero: [
    { to: '/', texto: 'Vuelos' },
    { to: '/reservas', texto: 'Reservas' },
  ],
  empleado_mostrador: [
    { to: '/', texto: 'Vuelos' },
    { to: '/empleado/reservas', texto: 'Reservas' },
  ],
  administrador: [
    { to: '/', texto: 'Vuelos' },
    { to: '/admin/reservas', texto: 'Reservas' },
    { to: '/admin/vuelos', texto: 'Gestión de vuelos' },
  ],
}
