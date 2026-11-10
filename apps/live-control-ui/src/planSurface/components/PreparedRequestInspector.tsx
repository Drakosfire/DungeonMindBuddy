import './BuddyContextTrace.css'
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
/** Decode message content for display only; captured strings and bytes stay untouched. */
function readable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(readable)
  if (value !== null && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => {
    if (key === 'content' && typeof item === 'string') {
      try {
        const parsed: unknown = JSON.parse(item)
        if (parsed !== null && typeof parsed === 'object') return [key, readable(parsed)]
      } catch { /* Ordinary message prose remains text. */ }
    }
    return [key, readable(item)]
  }))
  return value
}
function format(value: unknown, raw: boolean): string {
  if (typeof value === 'string') {
    if (raw) return value
    try {
      const parsed: unknown = JSON.parse(value)
      if (parsed !== null && typeof parsed === 'object') return JSON.stringify(readable(parsed), null, 2)
    } catch { /* Ordinary prompt prose is displayed verbatim. */ }
    return value
  }
  return JSON.stringify(raw ? value : readable(value), null, 2)
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
  return <div className="buddy-prompt">
    <p>Input message numbers and roles belong to this model request, not separate chat turns. Readable view decodes JSON message content; Exact JSON bytes preserves the captured request.</p>
    {previousPayloadJson && <section aria-label="Changes since previous model call" className="buddy-prompt__changes">
      <h5>Changes since previous captured call</h5>
      <p>Compared by request field and input-message position. Calls may use different models or formats; removed fields do not mean erased conversation or model memory. Green: added · red: removed · gold: changed.</p>
      {!changes.length && <p>No request components changed.</p>}
      {changes.map(change => <details key={change.pointer} className={`buddy-prompt__disclosure buddy-prompt__change buddy-prompt__change--${change.kind.toLowerCase()}`}>
        <summary>{change.kind} · {change.after?.label ?? change.before?.label} · {change.pointer}<span className="buddy-prompt__collapse" aria-hidden="true">Collapse</span></summary>
        {change.before && <div className="buddy-prompt__removed"><h6>Before</h6><pre>{format(change.before.value, raw)}</pre></div>}
        {change.after && <div className="buddy-prompt__added"><h6>Now</h6><pre>{format(change.after.value, raw)}</pre></div>}
      </details>)}
    </section>}
    <div className="buddy-prompt__toolbar"><button type="button" onClick={() => setSelected(null)}>Show full request</button>
      <label><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} /> Exact JSON bytes</label></div>
    <div className="buddy-prompt__layout">
      <nav aria-label="Request components">{parts.map(item => <button key={item.pointer} type="button" aria-pressed={selected === item.pointer}
        onClick={() => setSelected(item.pointer)}>{item.label}<small>{item.pointer}</small></button>)}</nav>
      <section aria-label="Captured request"><h5>{part ? part.label : 'Full composed request'}</h5>
        <pre tabIndex={0}>{part ? format(part.value, raw) : raw ? payloadJson : format(body, false)}</pre>
      </section>
    </div>
  </div>
}
