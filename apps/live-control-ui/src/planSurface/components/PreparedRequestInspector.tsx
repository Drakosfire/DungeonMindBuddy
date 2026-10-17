import { useState } from 'react'
type Component = { pointer: string; label: string; value: unknown }
const pointerPart = (key: string) => key.replace(/~/g, '~0').replace(/\//g, '~1')
function components(body: Record<string, unknown>): Component[] {
  return Object.entries(body).flatMap(([key, value]) => {
    if (['input', 'messages', 'tools'].includes(key) && Array.isArray(value)) {
      return value.map((item, i) => ({ pointer: `/${pointerPart(key)}/${i}`,
        label: `${key === 'tools' ? 'Tool' : 'Message'} ${i + 1}${item?.role ? ` · ${item.role}` : item?.type ? ` · ${item.type}` : ''}`,
        value: item }))
    }
    return [{ pointer: `/${pointerPart(key)}`, label: key === 'instructions' ? 'System instructions' : key, value }]
  })
}
const format = (value: unknown) => typeof value === 'string' ? value : JSON.stringify(value, null, 2)

/** Presentation of an actual captured request; callers own identity and authorization. */
export function PreparedRequestInspector({ payloadJson }: { payloadJson: string }) {
  const [selected, setSelected] = useState<string | null>(null)
  const [raw, setRaw] = useState(false)
  const body = JSON.parse(payloadJson) as Record<string, unknown>
  const parts = components(body)
  const part = parts.find(item => item.pointer === selected)
  return <>
    <div className="buddy-prompt__toolbar"><button type="button" onClick={() => setSelected(null)}>Show full request</button>
      <label><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} /> Exact JSON bytes</label></div>
    <div className="buddy-prompt__layout">
      <nav aria-label="Request components">{parts.map(item => <button key={item.pointer} type="button" aria-pressed={selected === item.pointer}
        onClick={() => setSelected(item.pointer)}>{item.label}<small>{item.pointer}</small></button>)}</nav>
      <section aria-label="Captured request"><h5>{part ? part.label : 'Full composed request'}</h5>
        <pre tabIndex={0}>{part ? format(part.value) : raw ? payloadJson : JSON.stringify(body, null, 2)}</pre>
      </section>
    </div>
  </>
}
