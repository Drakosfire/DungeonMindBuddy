import { useState } from 'react'
import type { AgentConversationTurnLifecycleV1 } from '../../api/types'
import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'
import { useBuddyTurnInspection } from './BuddyTurnInspection'
import { BuddyContextTraceLoader } from './BuddyContextTraceLoader'

function activity(event: BuddyTraceObservation): string {
  switch (event.kind) {
    case 'source_passage':
    case 'source_passage_reuse': return `Checked the receipts: ${event.source_name?.trim() || 'source name unavailable'}.`
    case 'graph_tool': return `Back from the World graph · ${event.result.outcome}.`
    case 'provider_call': return event.outcome === 'authorized' ? 'Model call cleared for takeoff…'
      : event.outcome === 'response_received' ? 'A model response just landed.' : `Model call · ${event.outcome}.`
    case 'prompt_reference': return 'Notes packed for the next model call.'
    case 'context_snapshot': return event.snapshot_kind === 'provider_input' ? 'Laying out the notes…'
      : event.snapshot_kind === 'provider_response' ? 'A response landed, ready for checking.'
      : event.snapshot_kind === 'validated_answer' ? 'The reply is assembled.'
      : event.snapshot_kind === 'compaction_input' ? 'Taking stock of the notes…'
      : event.snapshot_kind === 'compaction_output' ? 'The notes after a tidy-up.' : 'A captured snapshot of the notes.'
    case 'context_decision': return event.action === 'retrieved' && event.policy_version === 'selected_exact_related_authored_pages_v1'
      ? 'Another page joins the reading pile.' : `Tidying the notes · ${event.action}.`
    case 'failure': return event.phase === 'trace_capture' ? 'Some trace details are missing.' : 'Hit a snag—open the report.'
  }
}

/** Must live inside the exact turn inspection owner; no additional polling owner. */
export function BuddyActivity({ worldId, conversationId, turnId, lifecycle }: { worldId: string; conversationId: string; turnId: string; lifecycle: AgentConversationTurnLifecycleV1 }) {
  const [open, setOpen] = useState(false)
  const [technical, setTechnical] = useState(false)
  const binding = {worldId, conversationId, turnId}
  // Running work is observed even while collapsed; terminal traces load on demand.
  const inspection = useBuddyTurnInspection(binding, open || lifecycle === 'accepted' || lifecycle === 'running')
  const trace = inspection.data?.attempts.at(-1)
  const last = trace?.observations.at(-1)
  const failed = lifecycle === 'failed' || lifecycle === 'interrupted' || trace?.terminal_status === 'failed' || trace?.terminal_status === 'interrupted'
  const label = inspection.running ? last ? activity(last) : 'Getting the notes together…'
    : failed ? 'Reply error report' : 'How this reply came together'
  return <details className="buddy-activity" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary><span role="status" aria-live="polite">{label}</span></summary>
    {open && <div className="buddy-activity__body">
      {inspection.error && <p role="alert">{inspection.error} <button type="button" onClick={inspection.refresh}>Refresh activity</button></p>}
      {!trace ? <p>{inspection.running ? 'Waiting for recorded activity…' : 'No captured activity is available yet.'}</p> : <>
        <p>Attempt {trace.attempt} · {trace.terminal_status ?? 'in progress'} · recorded activity</p>
        {failed && !trace.observations.some(event => event.kind === 'failure' && event.phase !== 'trace_capture') && <p>The specific cause was not recorded for this attempt.</p>}
        <ol>{trace.observations.slice(-12).map(event => <li key={event.sequence}>
          <time>{(event.elapsed_ms / 1000).toFixed(1)}s</time> · {activity(event)}
          {event.kind === 'failure' && <span> · {event.code}{event.stage ? ` · ${event.stage}` : ''}</span>}
        </li>)}</ol>
        {trace.observations.length > 12 && <p>Latest 12 observations. The full trace is below.</p>}
      </>}
      <details onToggle={event => setTechnical(event.currentTarget.open)}><summary>Prompts and technical details</summary>
        {technical && <BuddyContextTraceLoader {...binding} enabled />}
      </details>
    </div>}
  </details>
}
