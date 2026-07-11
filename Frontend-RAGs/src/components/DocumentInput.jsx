import { useRef } from 'react'

// Entrada del documento: pegar texto en un textarea O subir un archivo.
export default function DocumentInput({ text, onChangeText, onFile, onRun, loading }) {
  const fileRef = useRef(null)

  const chars = text.length
  const words = text.trim() ? text.trim().split(/\s+/).length : 0

  return (
    <section className="panel">
      <div className="input-head">
        <h2>📄 Documento</h2>
        <div className="input-actions">
          <button className="btn-ghost" onClick={() => fileRef.current?.click()}>
            📎 Subir archivo
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".txt,.md,.pdf,.py,.js,.ts,.java,.go,.cpp,.html,.json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onFile(f)
              e.target.value = ''
            }}
          />
          <button className="btn-ghost" onClick={() => onChangeText('')}>
            🗑️ Limpiar
          </button>
        </div>
      </div>

      <textarea
        className="doc-textarea"
        value={text}
        onChange={(e) => onChangeText(e.target.value)}
        placeholder="Pega aquí tu texto o sube un archivo (.txt, .md, .pdf, código…)"
        rows={10}
      />

      <div className="input-foot">
        <span className="counter">
          {chars.toLocaleString()} caracteres · {words.toLocaleString()} palabras
        </span>
        <button className="btn-run" onClick={onRun} disabled={loading || !text.trim()}>
          {loading ? '⏳ Dividiendo…' : '✂️ Dividir texto'}
        </button>
      </div>
    </section>
  )
}
