import { useEffect, useState } from 'react'
import { getPlanActionPromptIndex, getPlanActionPromptBody } from '../../api/liveApi'
import type { ActionPromptIndex, ActionPromptReference, ActionPromptEvidence } from '../../api/types'
import { PreparedRequestInspector } from './PreparedRequestInspector'

export function ActionPromptInspector({ worldId, actionId }: { worldId: string; actionId: string }) {
  return <ScopedInspector key={`${worldId}:${actionId}`} worldId={worldId} actionId={actionId} />
}
function ScopedInspector({ worldId, actionId }: { worldId: string; actionId: string }) {
  const [open, setOpen] = useState(false)
  return <details onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>The Prompt</summary>
    {open && <PromptIndex worldId={worldId} actionId={actionId} />}
  </details>
}
function PromptIndex({ worldId, actionId }: { worldId: string; actionId: string }) {
  const [state, setState] = useState<{ index?: ActionPromptIndex; error?: boolean }>({})
  const [selected, setSelected] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    getPlanActionPromptIndex(worldId, actionId, controller.signal).then(index => {
      if (!active) return
      if (index.schema !== 'dmb_plan_action_prompt_index_v1' || index.world_id !== worldId
        || index.action_id !== actionId || !Array.isArray(index.references)
        || index.references.length > 512
        || new Set(index.references.map(ref => ref.provider_attempt_id)).size !== index.references.length
        || index.references.some(ref => ref.owner_kind !== 'plan_action' || ref.world_id !== worldId || ref.action_id !== actionId)) throw new Error('binding')
      setState({ index })
    }).catch(() => { if (active) setState({ error: true }) })
    return () => { active = false; controller.abort() }
  }, [worldId, actionId])
  if (state.error) return <p role="alert">The saved request is unavailable.</p>
  if (!state.index) return <p role="status">Loading captured requests…</p>
  const refs = state.index.references
  const reference = refs.find(ref => ref.provider_attempt_id === selected) ?? refs.at(-1)
  return <div className="buddy-prompt">
    <p>Exact prepared request at authorization. Authorization alone does not prove the request was sent.</p>
    {reference ? <>
      <label>Model call <select value={reference.provider_attempt_id} onChange={event => setSelected(event.target.value)}>
        {refs.map((ref, index) => <option key={ref.provider_attempt_id} value={ref.provider_attempt_id}>{index + 1} · {ref.model}</option>)}
      </select></label>
      <PromptBody key={JSON.stringify(reference)} worldId={worldId} actionId={actionId} reference={reference} />
    </> : <p>No complete request was captured for this action. It cannot be reconstructed from current context.</p>}
  </div>
}
function PromptBody({ worldId, actionId, reference }: { worldId: string; actionId: string; reference: ActionPromptReference }) {
  const [state, setState] = useState<{ evidence?: ActionPromptEvidence; error?: boolean }>({})
  useEffect(() => {
    let active = true
    const controller = new AbortController()
    getPlanActionPromptBody(worldId, actionId, reference.provider_attempt_id, controller.signal).then(evidence => {
      if (!active) return
      if (evidence.schema !== 'dmb_plan_action_prompt_evidence_v1' || evidence.world_id !== worldId
        || evidence.action_id !== actionId || Object.keys(reference).some(key =>
          evidence.reference[key as keyof ActionPromptReference] !== reference[key as keyof ActionPromptReference])) throw new Error('binding')
      const body = JSON.parse(evidence.payload_json)
      if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('envelope')
      setState({ evidence })
    }).catch(() => { if (active) setState({ error: true }) })
    return () => { active = false; controller.abort() }
  }, [worldId, actionId, reference])
  if (state.error) return <p role="alert">This captured request is unavailable. No reconstruction is shown.</p>
  if (!state.evidence) return <p role="status">Loading captured request…</p>
  return <>
    <PreparedRequestInspector payloadJson={state.evidence.payload_json} />
    <details><summary>Capture identity</summary><p>{reference.provider} · {reference.model} · {reference.api_mode} · {reference.serializer_version}</p>
      <p>{reference.payload_utf8_bytes.toLocaleString()} UTF-8 bytes · SHA-256 {reference.payload_sha256}</p>
      <p>Provider attempt {reference.provider_attempt_id}</p></details>
  </>
}
