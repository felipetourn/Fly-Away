import type { ReactNode } from 'react'

export default function Proximamente({ titulo, children }: { titulo: string; children?: ReactNode }) {
  return (
    <main className="mx-auto max-w-[88rem] px-4 py-16">
      <h1 className="text-3xl font-extrabold text-marino">{titulo}</h1>
      <p className="mt-2 text-slate-500">Próximamente.</p>
      {children && <div className="mt-6">{children}</div>}
    </main>
  )
}
