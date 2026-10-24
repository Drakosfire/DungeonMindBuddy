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
function format(value: unknown, raw: boolean): string {
  if (typeof value !== 'string') return JSON.stringify(value, null, 2)
  if (!raw) {
    try {
      const parsed: unknown = JSON.parse(value)
      if (parsed !== null && typeof parsed === 'object') return JSON.stringify(parsed, null, 2)
    } catch { /* Ordinary prompt prose is displayed verbatim. */ }
  }
  return value
}

/** Presentation of an actual captured request; callers own identity and authorization. */
export function PreparedRequestInspector({ payloadJson, previousPayloadJson }: { payloadJson: string; previousPayloadJson?: string }) {
  const [selected, setSelected] = useState<string | null>(null)
  const [raw, setRaw] = useState(false)
  const body = JSON.parse(payloadJson) as Record<string, unknown>
  const parts = components(body)
  const part = parts.find(item => item.pointer === selected)
  const previousParts = previousPayloadJson ? components(JSON.parse(previousPayloadJson)) : []
  const changes = previousPayloadJson ? [...new Set([...previousParts.map(item => item.pointer), ...parts.map(item => item.pointer)])].flatMap(pointer => {
    const before = previousParts.find(item => item.pointer === pointer)
    const after = parts.find(item => item.pointer === pointer)
    if (before && after && JSON.stringify(before.value) === JSON.stringify(after.value)) return []
    return [{ pointer, before, after, kind: !before ? 'Added' : !after ? 'Removed' : 'Changed' }]
  }) : []
  return <>
    {previousPayloadJson && <section aria-label="Changes since previous model call" className="buddy-prompt__changes">
      <h5>Changes since previous captured call</h5>
      <p>Compared by request component and message position. Green: added · red: removed · gold: changed.</p>
      {!changes.length && <p>No request components changed.</p>}
      {changes.map(change => <details key={change.pointer} className={`buddy-prompt__change buddy-prompt__change--${change.kind.toLowerCase()}`}>
        <summary>{change.kind} · {change.after?.label ?? change.before?.label} · {change.pointer}</summary>
        {change.before && <div className="buddy-prompt__removed"><h6>Before</h6><pre>{format(change.before.value, false)}</pre></div>}
        {change.after && <div className="buddy-prompt__added"><h6>Now</h6><pre>{format(change.after.value, false)}</pre></div>}
      </details>)}
    </section>}
    <div className="buddy-prompt__toolbar"><button type="button" onClick={() => setSelected(null)}>Show full request</button>
      <label><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} /> Exact JSON bytes</label></div>
    <div className="buddy-prompt__layout">
      <nav aria-label="Request components">{parts.map(item => <button key={item.pointer} type="button" aria-pressed={selected === item.pointer}
        onClick={() => setSelected(item.pointer)}>{item.label}<small>{item.pointer}</small></button>)}</nav>
      <section aria-label="Captured request"><h5>{part ? part.label : 'Full composed request'}</h5>
        <pre tabIndex={0}>{part ? format(part.value, raw) : raw ? payloadJson : JSON.stringify(body, null, 2)}</pre>
      </section>
    </div>
  </>
}
