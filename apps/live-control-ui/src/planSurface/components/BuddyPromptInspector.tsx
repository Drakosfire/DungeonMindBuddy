import { useEffect, useId, useState, type ReactNode } from 'react'
import { getWorldAgentTurnPrompt } from '../../api/liveApi'
import type { BuddyPromptEvidence, BuddyTracePromptReference, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'

export function ResponseEvidenceTabs({ evidence, prompt }: { evidence: ReactNode; prompt: ReactNode }) {
  const [tab, setTab] = useState<'evidence' | 'prompt'>('evidence')
  const id = useId()
  return <section className="buddy-context-trace" aria-label="Response evidence">
    <div role="tablist" aria-label="Response inspection" className="buddy-context-trace__tabs">
      {([['evidence', 'Evidence Trail'], ['prompt', 'The Prompt']] as const).map(([key, label]) =>
        <button key={key} type="button" role="tab" id={`${id}-${key}`} aria-controls={`${id}-panel`}
          aria-selected={tab === key} onClick={() => setTab(key)}>{label}</button>)}
    </div>
    <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${tab}`}>
      {tab === 'evidence' ? evidence : prompt}
    </div>
  </section>
}

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

export function BuddyPromptInspector({ trace }: { trace: BuddyTurnContextTrace | null }) {
  // A new identity remount clears private payloads synchronously, before effects.
  return trace ? <ScopedPromptInspector key={`${trace.world_id}:${trace.conversation_id}:${trace.turn_id}:${trace.trace_id}`} trace={trace} />
    : <p>No complete request was captured for this response.</p>
}
function ScopedPromptInspector({ trace }: { trace: BuddyTurnContextTrace }) {
  const refs = trace.observations.filter((item): item is BuddyTracePromptReference => item.kind === 'prompt_reference')
  const calls = trace.observations.filter(item => item.kind === 'provider_call' && item.outcome === 'authorized' && item.provider_attempt_id)
  const callIds = [...new Set([...calls.map(item => item.kind === 'provider_call' ? item.provider_attempt_id! : ''), ...refs.map(item => item.provider_attempt_id)])]
  const [selection, setSelection] = useState<string | null>(null)
  const callId = selection ?? callIds.at(-1) ?? ''
  const reference = refs.find(item => item.provider_attempt_id === callId)
  return <div className="buddy-prompt">
    <p>Exact prepared request at the dispatch gate. Authorization alone does not mean the request was sent. Credentials and HTTP headers are outside this capture.</p>
    {callIds.length > 0 && <label>Model call <select value={callId} onChange={event => setSelection(event.target.value)}>
      {callIds.map((id, index) => {
        const call = refs.find(item => item.provider_attempt_id === id) ?? calls.find(item => item.kind === 'provider_call' && item.provider_attempt_id === id)
        return <option key={id} value={id}>{index + 1} · {call && 'model' in call ? call.model : id}</option>
      })}</select></label>}
    {reference ? <CapturedPrompt key={`${callId}:${reference.evidence_id}:${reference.payload_sha256}`} trace={trace} reference={reference} />
      : <p>No complete request was captured for this call. It cannot be reconstructed from current context.</p>}
  </div>
}
function CapturedPrompt({ trace, reference }: { trace: BuddyTurnContextTrace; reference: BuddyTracePromptReference }) {
  const [state, setState] = useState<{ evidence?: BuddyPromptEvidence; error?: string }>({})
  const [selected, setSelected] = useState<string | null>(null)
  const [raw, setRaw] = useState(false)
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    getWorldAgentTurnPrompt(trace.world_id, trace.turn_id, trace.trace_id, reference.provider_attempt_id, controller.signal)
      .then(evidence => {
        if (!active) return
        if (evidence.schema !== 'dmb_agent_prompt_evidence_v1' || evidence.world_id !== trace.world_id
          || evidence.conversation_id !== trace.conversation_id || evidence.turn_id !== trace.turn_id
          || evidence.trace_id !== trace.trace_id || evidence.attempt !== trace.attempt
          || evidence.reference.provider_attempt_id !== reference.provider_attempt_id
          || evidence.reference.evidence_id !== reference.evidence_id
          || evidence.reference.payload_sha256 !== reference.payload_sha256
          || evidence.reference.payload_utf8_bytes !== reference.payload_utf8_bytes) throw new Error('binding')
        const body = JSON.parse(evidence.payload_json)
        if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('envelope')
        setState({ evidence })
      }).catch(() => { if (active) setState({ error: 'This captured request is unavailable. No reconstructed request is shown.' }) })
    return () => { active = false; controller.abort() }
  }, [trace.world_id, trace.conversation_id, trace.turn_id, trace.trace_id, trace.attempt, reference.provider_attempt_id, reference.evidence_id, reference.payload_sha256, reference.payload_utf8_bytes])
  if (state.error) return <p role="alert">{state.error}</p>
  if (!state.evidence) return <p role="status">Loading captured request…</p>
  const evidence = state.evidence
  const body = JSON.parse(evidence.payload_json) as Record<string, unknown>
  const parts = components(body)
  const part = parts.find(item => item.pointer === selected)
  return <>
    <div className="buddy-prompt__toolbar"><button type="button" onClick={() => setSelected(null)}>Show full request</button>
      <label><input type="checkbox" checked={raw} onChange={event => setRaw(event.target.checked)} /> Exact JSON bytes</label></div>
    <div className="buddy-prompt__layout">
      <nav aria-label="Request components">{parts.map(item => <button key={item.pointer} type="button" aria-pressed={selected === item.pointer}
        onClick={() => setSelected(item.pointer)}>{item.label}<small>{item.pointer}</small></button>)}</nav>
      <section aria-label="Captured request"><h5>{part ? part.label : 'Full composed request'}</h5>
        <pre tabIndex={0}>{part ? format(part.value) : raw ? evidence.payload_json : JSON.stringify(body, null, 2)}</pre>
      </section>
    </div>
    <details><summary>Capture identity</summary><p>{reference.provider} · {reference.model} · {reference.api_mode} · {reference.serializer_version}</p>
      <p>{reference.payload_utf8_bytes.toLocaleString()} UTF-8 bytes · SHA-256 {reference.payload_sha256}</p>
      <p>Provider attempt {reference.provider_attempt_id}</p></details>
  </>
}
