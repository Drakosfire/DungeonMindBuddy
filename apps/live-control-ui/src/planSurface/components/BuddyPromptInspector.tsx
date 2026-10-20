import './BuddyContextTrace.css'
import { useEffect, useState } from 'react'
import { PreparedRequestInspector } from './PreparedRequestInspector'
import { getWorldAgentTurnPrompt } from '../../api/liveApi'
import type { BuddyPromptEvidence, BuddyTracePromptReference, BuddyTurnContextTrace } from '../../api/buddyContextTraceTypes'

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
  return <>
    <PreparedRequestInspector payloadJson={evidence.payload_json} />
    <details><summary>Capture identity</summary><p>{reference.provider} · {reference.model} · {reference.api_mode} · {reference.serializer_version}</p>
      <p>{reference.payload_utf8_bytes.toLocaleString()} UTF-8 bytes · SHA-256 {reference.payload_sha256}</p>
      <p>Provider attempt {reference.provider_attempt_id}</p></details>
  </>
}
