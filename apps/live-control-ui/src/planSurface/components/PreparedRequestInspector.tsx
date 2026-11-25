import './BuddyEvidence.css'
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
  const messages = parts.filter(item => item.pointer.startsWith('/input/') || item.pointer.startsWith('/messages/')
    || ((item.pointer === '/input' || item.pointer === '/messages') && typeof item.value === 'string'))
  const systemMessages = messages.filter(item => item.value !== null && typeof item.value === 'object'
    && !Array.isArray(item.value) && 'role' in item.value && item.value.role === 'system')
  const otherMessages = messages.filter(item => !systemMessages.includes(item))
  const system = parts.find(item => item.pointer === '/instructions')
  const jevInput = parts.filter(item => item.pointer === '/state' || item.pointer === '/questions')
  const inputText = (value: unknown) => {
    if (value && typeof value === 'object' && !Array.isArray(value) && 'content' in value) {
      const message = value as Record<string, unknown>
      const details = Object.fromEntries(Object.entries(message).filter(([key]) => key !== 'role' && key !== 'content'))
      if (Object.keys(details).length) return format({ content: message.content, ...details }, false)
      return format(message.content, false)
    }
    return format(value, false)
  }
  return <div className="buddy-prompt">
    <section aria-label="Captured request" className="buddy-prompt__readable">
      {system && <section><h5>System instructions</h5><pre tabIndex={0}>{inputText(system.value)}</pre></section>}
      {systemMessages.map(item => <section key={item.pointer}><h5>{item.label}</h5><pre tabIndex={0}>{inputText(item.value)}</pre></section>)}
      {otherMessages.map(item => <section key={item.pointer}><h5>{item.label}</h5><pre tabIndex={0}>{inputText(item.value)}</pre></section>)}
      {jevInput.map(item => <section key={item.pointer}><h5>{item.pointer === '/state' ? 'State' : 'Questions'}</h5><pre tabIndex={0}>{inputText(item.value)}</pre></section>)}
      {!system && messages.length === 0 && jevInput.length === 0 && <section><h5>Captured input</h5><pre tabIndex={0}>{format(body, false)}</pre></section>}
    </section>
    <details className="buddy-prompt__disclosure">
      <summary>Request details and exact JSON</summary>
      <p>Captured request configuration and tool definitions.</p>
      <div className="buddy-prompt__toolbar"><button type="button" onClick={() => setSelected(null)}>Show full request</button>
        <label><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} /> Exact JSON bytes</label></div>
      <div className="buddy-prompt__layout">
        <nav aria-label="Request components">{parts.map(item => <button key={item.pointer} type="button" aria-pressed={selected === item.pointer}
          onClick={() => setSelected(item.pointer)}>{item.label}<small>{item.pointer}</small></button>)}</nav>
        <section aria-label="Request details"><h5>{part ? part.label : 'Full composed request'}</h5>
          <pre tabIndex={0}>{part ? format(part.value, raw) : raw ? payloadJson : format(body, false)}</pre>
        </section>
      </div>
    </details>
    {previousPayloadJson && <details aria-label="Changes since previous model call" className="buddy-prompt__changes buddy-prompt__disclosure">
      <summary>Changes since previous captured call</summary>
      {changes.map(change => <details key={change.pointer} className={`buddy-prompt__disclosure buddy-prompt__change buddy-prompt__change--${change.kind.toLowerCase()}`}>
        <summary>{change.kind} · {change.after?.label ?? change.before?.label} · {change.pointer}</summary>
        {change.before && <div className="buddy-prompt__removed"><h6>Before</h6><pre>{format(change.before.value, raw)}</pre></div>}
        {change.after && <div className="buddy-prompt__added"><h6>Now</h6><pre>{format(change.after.value, raw)}</pre></div>}
      </details>)}
    </details>}
  </div>
}
