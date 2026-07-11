// Controles dinámicos de parámetros según el splitter seleccionado.

export default function ParamControls({ params, values, onChange }) {
  if (!params || params.length === 0) return null

  return (
    <div className="params">
      {params.map((p) => (
        <div key={p.name} className="param">
          <label>{p.label}</label>
          {p.type === 'select' ? (
            <select
              value={values[p.name] ?? p.default}
              onChange={(e) => onChange(p.name, e.target.value)}
            >
              {p.options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="number"
              value={values[p.name] ?? p.default}
              min={p.min}
              max={p.max}
              step={p.step}
              onChange={(e) =>
                onChange(
                  p.name,
                  p.type === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value, 10),
                )
              }
            />
          )}
        </div>
      ))}
    </div>
  )
}
