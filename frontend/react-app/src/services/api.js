const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export async function apiFetch(path, opts = {}) {
  const url = BASE + path
  const res = await fetch(url, opts)
  if (!res.ok) {
    const txt = await res.text().catch(() => null)
    const err = new Error(`HTTP ${res.status} ${txt || res.statusText}`)
    err.status = res.status
    throw err
  }
  // try parse json but fall back to text
  const ctype = res.headers.get('content-type') || ''
  if (ctype.includes('application/json')) return res.json()
  return res.text()
}

export default apiFetch
