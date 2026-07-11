// Muestra los Document(s) extraídos por un loader + estadísticas y metadata.

export default function DocViewer({ result, loading }) {
  if (loading) {
    return <div className="viewer-empty">Extrayendo el texto del archivo…</div>
  }
  if (!result) {
    return (
      <div className="viewer-empty">
        El texto extraído aparecerá aquí después de procesar el archivo.
      </div>
    )
  }
  if (result.num_documents === 0) {
    return <div className="viewer-empty">No se extrajo texto (¿PDF escaneado o vacío?).</div>
  }

  const { stats, documents } = result

  return (
    <section>
      <div className="stats">
        <Stat label="Documentos" value={stats.total_documents} />
        <Stat label="Caracteres totales" value={stats.total_chars.toLocaleString()} />
        <Stat label="Caracteres/doc (prom.)" value={stats.avg_chars} />
      </div>

      <div className="chunks">
        {documents.map((d, i) => (
          <div key={i} className="chunk" style={{ borderLeftColor: '#0ea5e9' }}>
            <div className="chunk-head">
              <span className="chunk-num" style={{ background: '#0ea5e9' }}>
                Doc #{i + 1}
              </span>
              <span className="chunk-meta">{d.text.length} caracteres</span>
            </div>

            {Object.keys(d.metadata || {}).length > 0 && (
              <div className="metadata">
                {Object.entries(d.metadata).map(([k, v]) => (
                  <span key={k} className="meta-tag">
                    <b>{k}:</b> {String(v)}
                  </span>
                ))}
              </div>
            )}

            <pre className="chunk-text">{d.text || '(sin texto)'}</pre>
          </div>
        ))}
      </div>
    </section>
  )
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
