// Single ES module API client for frontend
const API_BASE = (import.meta.env.VITE_API_BASE) || 'http://localhost:8000'

async function uploadResume(file) {
  const fd = new FormData()
  fd.append('file', file)
  const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd })
  if (!res.ok) {
    const txt = await res.text().catch(() => null)
    throw new Error(`Upload failed: ${res.status} ${txt || res.statusText}`)
  }
  return res.json()
}

async function getQuestions(upload_id) {
  const url = new URL(`${API_BASE}/questions`)
  if (upload_id) url.searchParams.set('upload_id', upload_id)
  const res = await fetch(url.toString())
  if (!res.ok) {
    const txt = await res.text().catch(() => null)
    throw new Error(`Failed fetching questions: ${res.status} ${txt || res.statusText}`)
  }
  return res.json()
}

async function submitAnswers(upload_id, answers) {
  const res = await fetch(`${API_BASE}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ upload_id, answers }),
  })
  if (!res.ok) {
    const txt = await res.text().catch(() => null)
    throw new Error(`Submit failed: ${res.status} ${txt || res.statusText}`)
  }
  return res.json()
}

async function getReport(upload_id) {
  const url = new URL(`${API_BASE}/report`)
  if (upload_id) url.searchParams.set('upload_id', upload_id)
  const res = await fetch(url.toString())
  if (!res.ok) {
    const txt = await res.text().catch(() => null)
    throw new Error(`Failed fetching report: ${res.status} ${txt || res.statusText}`)
  }
  return res.json()
}

const api = { uploadResume, getQuestions, submitAnswers, getReport }

export default api
