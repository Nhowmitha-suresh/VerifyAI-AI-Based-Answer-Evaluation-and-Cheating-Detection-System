const API_BASE = (import.meta.env.VITE_API_BASE) || 'http://localhost:8000'

async function uploadResumeFile(file){
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd })
  if(!res.ok) throw new Error('upload failed')
  return res.json()
}

async function getQuestions(upload_id){
  const url = new URL(`${API_BASE}/questions`)
  if(upload_id) url.searchParams.set('upload_id', upload_id)
  const res = await fetch(url.toString())
  if(!res.ok) throw new Error('questions fetch failed')
  return res.json()
}

async function submitAnswers(upload_id, answers){
  const res = await fetch(`${API_BASE}/submit`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ upload_id, answers }) })
  if(!res.ok) throw new Error('submit failed')
  return res.json()
}

async function getReport(upload_id){
  const url = new URL(`${API_BASE}/report`)
  if(upload_id) url.searchParams.set('upload_id', upload_id)
  const res = await fetch(url.toString())
  if(!res.ok) throw new Error('report fetch failed')
  return res.json()
}

export default { uploadResumeFile, getQuestions, submitAnswers, getReport }
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
