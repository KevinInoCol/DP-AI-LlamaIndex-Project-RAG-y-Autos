// Menú lateral con AMBAS secciones desplegadas a la vez:
//   📄 Document Loaders   (ordenados de peor a mejor, con estrellas)
//   ✂️ Text Splitters
// La selección de cada sección queda siempre resaltada, así se ve de un vistazo
// qué loader y qué splitter están activos. El indicador "● viendo" marca qué
// panel se está mostrando en el área principal.

function stars(q) {
  return '★'.repeat(q) + '☆'.repeat(4 - q)
}

function MenuItem({ item, selected, onSelect, showQuality }) {
  return (
    <button
      className={`menu-item ${selected ? 'active' : ''}`}
      onClick={() => onSelect(item.key)}
    >
      <span className="menu-name">{item.name}</span>
      <span className="menu-tags">
        {showQuality && item.quality && (
          <span className="menu-stars">{stars(item.quality)}</span>
        )}
        {item.requires_api_key && (
          <span className="menu-key" title="Requiere API Key">🔑</span>
        )}
      </span>
    </button>
  )
}

function Section({ title, items, selectedKey, onSelect, active, showQuality }) {
  return (
    <div className={`menu-section ${active ? 'section-active' : ''}`}>
      <div className="section-title">
        <span>{title}</span>
        {active && <span className="viewing">● viendo</span>}
      </div>
      {items.length === 0 ? (
        <div className="menu-empty">Cargando…</div>
      ) : (
        items.map((it) => (
          <MenuItem
            key={it.key}
            item={it}
            selected={it.key === selectedKey}
            onSelect={onSelect}
            showQuality={showQuality}
          />
        ))
      )}
    </div>
  )
}

export default function Sidebar({
  loaders,
  splitters,
  selLoader,
  selSplitter,
  activeTab,
  onSelectLoader,
  onSelectSplitter,
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="logo">🦙</span>
        <div>
          <div className="brand-title">RAG Toolkit</div>
          <div className="brand-sub">LlamaIndex</div>
        </div>
      </div>

      <Section
        title="📄 Document Loaders"
        items={loaders}
        selectedKey={selLoader}
        onSelect={onSelectLoader}
        active={activeTab === 'loaders'}
        showQuality
      />

      <Section
        title="✂️ Text Splitters"
        items={splitters}
        selectedKey={selSplitter}
        onSelect={onSelectSplitter}
        active={activeTab === 'splitters'}
      />

      <div className="sidebar-foot">
        🔑 = requiere API Key · ★ = calidad del loader
      </div>
    </aside>
  )
}
