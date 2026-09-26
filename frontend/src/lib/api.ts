const API_URL = import.meta.env.VITE_API_URL

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access')
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...init.headers,
    },
  })
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`)
  return res.json()
}
