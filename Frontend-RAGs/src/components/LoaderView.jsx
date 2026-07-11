import { useEffect, useRef, useState } from 'react'
import { loadDocument } from '../api'
import DocViewer from './DocViewer'

// Pestaña de Document Loaders (extracción): archivo -> Document(s).
export default function LoaderView({ selected }) {
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef(null)

  // Al cambiar de loader, limpiar el resultado anterior.
  useEffect(() => {
    setResult(null)
    setError(null)
  }, [selected])

  async function handleLoad() {
    if (!selected || !file) return
    setLoading(true)
    setError(null)
    try {
      const data = await loadDocument({ loader: selected.key, file })
      setResult(data)
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  if (!selected) return null

  const stars = '★'.repeat(selected.quality) + '☆'.repeat(4 - selected.quality)

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>
            {selected.name}
            <span className={`badge ${selected.requires_api_key ? 'badge-api' : 'badge-free'}`}>
              {selected.requires_api_key ? '🔵 Con API Key' : '🟢 Sin API Key'}
            </span>
          </h2>
          <div className="loader-meta">
            <span className="quality" title={`Calidad ${selected.quality}/4`}>{stars}</span>
            <span className="engine">⚙️ Motor: {selected.engine}</span>
            <span className="accepts">📁 {selected.accepts.join(' · ')}</span>
          </div>
          <p className="desc">{selected.description}</p>
        </div>
      </section>

      <section className="panel">
        <div className="input-head">
          <h2>📄 Archivo</h2>
          <div className="input-actions">
            <button className="btn-ghost" onClick={() => fileRef.current?.click()}>
              📎 Elegir archivo
            </button>
            <input
              ref={fileRef}
              type="file"
              accept={selected.accepts.join(',')}
              style={{ display: 'none' }}
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) {
                  setFile(f)
                  setResult(null)
                }
                e.target.value = ''
              }}
            />
          </div>
        </div>

        <div className={`filedrop ${file ? 'has-file' : ''}`}>
          {file ? (
            <span>
              📎 <strong>{file.name}</strong> · {(file.size / 1024).toFixed(1)} KB
            </span>
          ) : (
            <span>Selecciona un archivo para extraer su texto ({selected.accepts.join(', ')})</span>
          )}
        </div>

        <div className="input-foot">
          <span className="counter">
            {selected.requires_api_key
              ? 'Requiere LLAMA_CLOUD_API_KEY en el backend'
              : 'Extracción local, sin API key'}
          </span>
          <button className="btn-run" onClick={handleLoad} disabled={loading || !file}>
            {loading ? '⏳ Extrayendo…' : '📥 Extraer texto'}
          </button>
        </div>
      </section>

      {error && <div className="error">⚠️ {error}</div>}

      <DocViewer result={result} loading={loading} />
    </>
  )
}
