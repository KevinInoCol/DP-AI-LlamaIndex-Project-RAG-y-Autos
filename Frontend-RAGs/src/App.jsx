import { useEffect, useMemo, useState } from 'react'
import { fetchSplitters, fetchLoaders } from './api'
import Sidebar from './components/Sidebar'
import SplitterView from './components/SplitterView'
import LoaderView from './components/LoaderView'

const TAB_INFO = {
  splitters: {
    title: '🧩 Text Splitters Visualizer',
    subtitle: 'Coloca un documento y observa cómo lo divide en chunks cada técnica de LlamaIndex.',
  },
  loaders: {
    title: '📄 Document Loaders Visualizer',
    subtitle: 'Sube un archivo y compara cómo extrae el texto cada Reader — de la peor a la mejor opción.',
  },
}

export default function App() {
  const [activeTab, setActiveTab] = useState('loaders')
  const [splitters, setSplitters] = useState([])
  const [loaders, setLoaders] = useState([])
  const [selSplitter, setSelSplitter] = useState(null)
  const [selLoader, setSelLoader] = useState(null)
  const [error, setError] = useState(null)

  // Cargar ambos catálogos al iniciar.
  useEffect(() => {
    fetchSplitters()
      .then((list) => {
        setSplitters(list)
        if (list.length) setSelSplitter(list[0].key)
      })
      .catch((e) => setError(e.message))
    fetchLoaders()
      .then((list) => {
        setLoaders(list)
        if (list.length) setSelLoader(list[0].key)
      })
      .catch((e) => setError(e.message))
  }, [])

  const isLoaders = activeTab === 'loaders'

  // Seleccionar un ítem también decide qué panel se muestra en el área principal.
  function handleSelectLoader(key) {
    setSelLoader(key)
    setActiveTab('loaders')
  }
  function handleSelectSplitter(key) {
    setSelSplitter(key)
    setActiveTab('splitters')
  }

  const selectedSplitter = useMemo(
    () => splitters.find((s) => s.key === selSplitter) || null,
    [splitters, selSplitter],
  )
  const selectedLoader = useMemo(
    () => loaders.find((l) => l.key === selLoader) || null,
    [loaders, selLoader],
  )

  const info = TAB_INFO[activeTab]

  return (
    <div className="app">
      <Sidebar
        loaders={loaders}
        splitters={splitters}
        selLoader={selLoader}
        selSplitter={selSplitter}
        activeTab={activeTab}
        onSelectLoader={handleSelectLoader}
        onSelectSplitter={handleSelectSplitter}
      />

      <main className="main">
        <header className="topbar">
          <h1>{info.title}</h1>
          <p className="subtitle">{info.subtitle}</p>
        </header>

        {error && <div className="error">⚠️ {error}</div>}

        {isLoaders ? (
          <LoaderView selected={selectedLoader} />
        ) : (
          <SplitterView selected={selectedSplitter} loader={selectedLoader} />
        )}
      </main>
    </div>
  )
}
