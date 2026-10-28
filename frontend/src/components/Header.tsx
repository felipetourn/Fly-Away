import { Link, NavLink, useLocation } from 'react-router-dom'
import { iniciales, MENU } from '../lib/auth'
import { useSesion } from '../lib/sesion'

const navLink = ({ isActive }: { isActive: boolean }) =>
  `relative shrink-0 rounded-full px-2 py-2 whitespace-nowrap sm:px-3 ${
    isActive
      ? 'text-marino after:absolute after:inset-x-3 after:-bottom-[22px] after:h-[3px] after:rounded-full after:bg-naranja'
      : 'text-slate-500 hover:text-marino'
  }`

export default function Header() {
  const { usuario } = useSesion()
  const { pathname, search } = useLocation()
  // Iniciar sesión o registrarse desde el header vuelve a la página actual (destinoTrasLogin).
  const desde = { desde: pathname + search }
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white">
      <div className="flex h-20 items-center justify-between gap-3 px-4 md:px-8">
        <Link to="/" aria-label="Fly Away, inicio" className="shrink-0">
          <img src="/logoMain.svg" alt="" className="h-9 sm:hidden" />
          <img src="/titulo.svg" alt="" className="hidden h-8 sm:block md:h-10" />
        </Link>
        <nav className="flex h-full min-w-0 items-center gap-1 text-xs font-semibold sm:text-sm md:gap-2">
          {/* En pantallas angostas los enlaces scrollean de costado; el alto completo deja ver el subrayado. */}
          <div className="flex h-full min-w-0 items-center gap-1 overflow-x-auto [scrollbar-width:none] md:gap-2">
            {MENU[usuario?.rol ?? 'pasajero'].map(({ to, texto }) => (
              <NavLink key={to} to={to} end={to === '/'} className={navLink}>
                {texto}
              </NavLink>
            ))}
          </div>
          <span className="mx-1 h-6 w-px shrink-0 bg-slate-200" aria-hidden="true" />
          {usuario ? (
            <Link
              to="/perfil"
              title="Mi perfil"
              aria-label="Mi perfil"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-linear-to-br from-naranja to-ambar text-sm font-bold text-white shadow ring-2 ring-white"
            >
              {iniciales(usuario)}
            </Link>
          ) : (
            <>
              <Link to="/login" state={desde} className="rounded-full px-2 py-2 text-marino hover:bg-slate-100 sm:px-3">
                <span className="sm:hidden">Ingresar</span>
                <span className="hidden sm:inline">Iniciar sesión</span>
              </Link>
              <span className="hidden text-slate-300 sm:inline" aria-hidden="true">
                |
              </span>
              <Link
                to="/registro"
                state={desde}
                className="ml-2 hidden rounded-full bg-marino px-4 py-2 text-white hover:bg-cielo sm:inline-block"
              >
                Registrarse
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}
