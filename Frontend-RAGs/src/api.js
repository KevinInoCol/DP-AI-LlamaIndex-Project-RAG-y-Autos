// Cliente del backend FastAPI. En desarrollo usamos el proxy /api de Vite.
const BASE = '/api'

export async function fetchSplitters() {
  const res = await fetch(`${BASE}/splitters`)
  if (!res.ok) throw new Error('No se pudo cargar el catálogo de splitters')
  const data = await res.json()
  return data.splitters
}

export async function splitText({ splitter, text, params }) {
  const res = await fetch(`${BASE}/split`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ splitter, text, params }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Error al dividir el texto')
  }
  return res.json()
}

export async function fetchLoaders() {
  const res = await fetch(`${BASE}/loaders`)
  if (!res.ok) throw new Error('No se pudo cargar el catálogo de loaders')
  const data = await res.json()
  return data.loaders
}

export async function loadDocument({ loader, file }) {
  const form = new FormData()
  form.append('loader', loader)
  form.append('file', file)
  const res = await fetch(`${BASE}/load`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Error al cargar el documento')
  }
  return res.json()
}

export async function extractFile(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/extract`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'No se pudo extraer el archivo')
  }
  return res.json()
}
