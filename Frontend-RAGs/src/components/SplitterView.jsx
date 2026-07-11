import { useEffect, useState } from 'react'
import { splitText, extractFile, loadDocument } from '../api'
import DocumentInput from './DocumentInput'
import ParamControls from './ParamControls'
import ChunkViewer from './ChunkViewer'

const SAMPLE = `LlamaIndex es un framework para construir aplicaciones RAG.
El chunking (o segmentación) es un paso clave: divide los documentos en
fragmentos más pequeños llamados "nodes".

Existen varias técnicas. El SentenceSplitter intenta no romper oraciones.
El TokenTextSplitter corta por número de tokens. Los splitters semánticos
usan embeddings para detectar cambios de tema y cortar en el punto óptimo.

Elegir el splitter correcto mejora mucho la calidad de la recuperación.`

// Pestaña de Text Splitters (chunking): texto -> nodes.
// La extracción de archivos reutiliza el Document Loader seleccionado en la
// otra pestaña (prop `loader`), encadenando el pipeline: Loader -> Splitter.
export default function SplitterView({ selected, loader }) {
  const [text, setText] = useState(SAMPLE)
  const [params, setParams] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Al cambiar de splitter, resetear parámetros a sus valores por defecto.
  useEffect(() => {
    if (!selected) return
    const defaults = {}
    for (const p of selected.params) defaults[p.name] = p.default
    setParams(defaults)
    setResult(null)
    setError(null)
  }, [selected])

  async function handleSplit() {
    if (!selected || !text.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await splitText({ splitter: selected.key, text, params })
      setResult(data)
    } catch (e) {
      setError(e.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  // ¿El loader seleccionado acepta este tipo de archivo?
  function loaderAcceptsFile(file) {
    if (!loader) return false
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    return loader.accepts?.includes(ext)
  }

  async function handleFile(file) {
    setError(null)
    try {
      if (loaderAcceptsFile(file)) {
        // Pipeline real: extraer con el Document Loader elegido en la otra pestaña.
        const data = await loadDocument({ loader: loader.key, file })
        setText(data.documents.map((d) => d.text).join('\n\n'))
      } else {
        // Fallback para archivos que el loader no soporta (.txt, .md, código…).
        const data = await extractFile(file)
        setText(data.text)
      }
    } catch (e) {
      setError(e.message)
    }
  }

  if (!selected) return null

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
          <p className="desc">{selected.description}</p>
        </div>

        <ParamControls
          params={selected.params}
          values={params}
          onChange={(name, value) => setParams((p) => ({ ...p, [name]: value }))}
        />
      </section>

      {loader && (
        <div className="pipeline">
          <span className="pipe-step">
            📄 Al subir un archivo se extrae con <b>{loader.name}</b>
          </span>
          <span className="pipe-arrow">→</span>
          <span className="pipe-step">✂️ luego se divide con <b>{selected.name}</b></span>
          <span className="pipe-hint">(cambia el loader en la pestaña “Document Loaders”)</span>
        </div>
      )}

      <DocumentInput
        text={text}
        onChangeText={setText}
        onFile={handleFile}
        onRun={handleSplit}
        loading={loading}
      />

      {error && <div className="error">⚠️ {error}</div>}

      <ChunkViewer result={result} loading={loading} />
    </>
  )
}
