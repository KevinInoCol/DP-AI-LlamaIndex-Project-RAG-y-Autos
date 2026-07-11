// Muestra los chunks resultantes como tarjetas + estadísticas globales.

const COLORS = [
  '#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
]

export default function ChunkViewer({ result, loading }) {
  if (loading) {
    return <div className="viewer-empty">Procesando el documento…</div>
  }
  if (!result) {
    return (
      <div className="viewer-empty">
        Los chunks aparecerán aquí después de dividir el texto.
      </div>
    )
  }
  if (result.num_chunks === 0) {
    return <div className="viewer-empty">No se generaron chunks (¿texto vacío?).</div>
  }

  const { stats, chunks } = result

  return (
    <section>
      <div className="stats">
        <Stat label="Chunks" value={stats.total_chunks} />
        <Stat label="Tokens totales" value={stats.total_tokens.toLocaleString()} />
        <Stat label="Tokens/chunk (prom.)" value={stats.avg_tokens} />
        <Stat label="Caracteres/chunk (prom.)" value={stats.avg_chars} />
      </div>

      <div className="chunks">
        {chunks.map((c) => {
          const color = COLORS[c.index % COLORS.length]
          return (
            <div key={c.index} className="chunk" style={{ borderLeftColor: color }}>
              <div className="chunk-head">
                <span className="chunk-num" style={{ background: color }}>
                  #{c.index + 1}
                </span>
                <span className="chunk-meta">
                  {c.token_count} tokens · {c.char_count} caracteres
                </span>
              </div>
              <pre className="chunk-text">{c.text}</pre>
              {c.window && (
                <details className="chunk-window">
                  <summary>Ver ventana de contexto</summary>
                  <pre className="chunk-text">{c.window}</pre>
                </details>
              )}
            </div>
          )
        })}
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
