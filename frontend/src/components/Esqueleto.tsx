/** Bloque gris que late mientras llegan los datos. El tamaño va por `className`. */
export function Esqueleto({ className }: { className: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-xl bg-slate-200/70 ${className}`} />
}

/** Página genérica mientras se recupera la sesión (todavía no se sabe qué pantalla toca). */
export function EsqueletoPagina({ angosta = false }: { angosta?: boolean }) {
  return (
    <main
      role="status"
      aria-label="Cargando"
      aria-busy="true"
      className={`mx-auto px-4 py-16 ${angosta ? 'max-w-md' : 'max-w-[88rem]'}`}
    >
      <Esqueleto className="h-9 w-64 max-w-full" />
      <Esqueleto className="mt-3 h-4 w-80 max-w-full" />
      <Esqueleto className="mt-8 h-64 w-full rounded-2xl" />
    </main>
  )
}
