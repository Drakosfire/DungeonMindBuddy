import './BuddyActivity.css'
import { nativeRetrievalActivity } from './nativeRetrievalActivity'
import { useState } from 'react'
import type { AgentConversationTurnLifecycleV1 } from '../../api/types'
import type { BuddyTraceObservation } from '../../api/buddyContextTraceTypes'
import { useBuddyTurnInspection } from './BuddyTurnInspection'
import { BuddyContextTraceLoader } from './BuddyContextTraceLoader'

/** Usage updates for one identified response are not another model arrival.
 * Keep the first receipt in place; the full trace still owns every observation.
 */
export function activityObservations(observations: readonly BuddyTraceObservation[]): BuddyTraceObservation[] {
  const received = new Set<string>()
  return observations.filter(event => {
    if (event.kind !== 'provider_call' || event.outcome !== 'response_received' || !event.provider_attempt_id) return true
    const key = JSON.stringify([event.provider_attempt_id, event.provider, event.model])
    if (received.has(key)) return false
    received.add(key)
    return true
  })
}

function activity(event: BuddyTraceObservation): string {
  switch (event.kind) {
    case 'authored_graph_reference_v1': {
      const recorded=event.execution_event;
      switch(recorded.kind){
        case 'build_authored_references_captured_v1':return 'Your Graph references are on the reading list.';
        case 'build_authored_reference_authorized_v1':return 'Opening the object you picked…';
        case 'build_authored_reference_read_v1':return recorded.outcome==='read'?'Checked the object and its source receipts.':recorded.outcome==='read_partial'?'That object read came back incomplete.':'The object is missing complete source support.';
        case 'build_authored_provider_inclusion_v1':return 'Graph context packed for the writer.';
      }
    }
    case 'source_passage':
    case 'source_passage_reuse': return `Checked the receipts: ${event.source_name?.trim() || 'source name unavailable'}.`
    case 'graph_tool': {
      const request = event.request;
      const focus = request.operation === 'search' ? `“${request.query_text}”`
        : request.operation === 'object' || request.operation === 'support'
          ? event.result.nodes.find(node => node.node_id === request.target_node_id)?.label ?? request.target_node_id
          : request.operation === 'neighborhood' ? request.seed_node_ids.join(', ')
          : request.observation_ids.join(', ');
      return `Graph ${request.operation}: ${focus} · ${event.result.outcome}.`;
    }
    case 'provider_call': return event.outcome === 'authorized' ? 'Model call cleared for takeoff…'
      : event.outcome === 'response_received' ? 'A model response just landed.' : `Model call · ${event.outcome}.`
    case 'prompt_reference': return 'Notes packed for the next model call.'
    case 'context_snapshot': return event.snapshot_kind === 'provider_input' ? 'Laying out the notes…'
      : event.snapshot_kind === 'provider_response' ? 'Response captured for inspection.'
      : event.snapshot_kind === 'validated_answer' ? 'The reply is assembled.'
      : event.snapshot_kind === 'compaction_input' ? 'Taking stock of the notes…'
      : event.snapshot_kind === 'compaction_output' ? 'The notes after a tidy-up.' : 'A captured snapshot of the notes.'
    case 'context_decision': if (nativeRetrievalActivity(event)) return nativeRetrievalActivity(event)!; if(event.policy_version==='reviewed_author_action_v1')return 'Following your reviewed step.'; return event.action === 'retrieved' && event.policy_version === 'selected_exact_related_authored_pages_v1'
      ? 'Another page joins the reading pile.' : `Tidying the notes · ${event.action}.`
    case 'failure': return event.phase === 'trace_capture' ? 'Some trace details are missing.' : 'Hit a snag—open the report.'
  }
}

/** Must live inside the exact turn inspection owner; no additional polling owner. */
export function BuddyActivity({ worldId, conversationId, turnId, lifecycle }: { worldId: string; conversationId: string; turnId: string; lifecycle: AgentConversationTurnLifecycleV1 }) {
  const [open, setOpen] = useState(false)
  const binding = {worldId, conversationId, turnId}
  // Running work is observed even while collapsed; terminal traces load on demand.
  const inspection = useBuddyTurnInspection(binding, open || lifecycle === 'accepted' || lifecycle === 'running')
  const trace = inspection.data?.attempts.at(-1)
  const observations = activityObservations(trace?.observations ?? [])
  const last = observations.at(-1)
  const focus = [...observations].reverse().find(event => nativeRetrievalActivity(event) !== null || event.kind === 'graph_tool' || event.kind === 'source_passage'
    || event.kind === 'source_passage_reuse' || event.kind === 'authored_graph_reference_v1')
  const progress = last && focus && last.kind !== 'failure'
    && (last.kind === 'context_snapshot' && last.snapshot_kind !== 'validated_answer'
      || last.kind === 'prompt_reference' && last.provider === 'typesafe'
      || last.kind === 'provider_call' && last.provider === 'typesafe') ? focus : last
  const failed = lifecycle === 'failed' || lifecycle === 'interrupted' || trace?.terminal_status === 'failed' || trace?.terminal_status === 'interrupted'
  const label = inspection.running ? progress ? activity(progress) : 'Getting the notes together…'
    : failed ? 'Reply error report' : 'How this reply came together'
  return <details className="buddy-activity" data-running={inspection.running} onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>
      {inspection.running && <svg className="buddy-activity__bubble" viewBox="0 0 32 28" width="28" height="25" aria-hidden="true" focusable="false">
        <path d="M8 20c-4-1-6-4-6-8C2 6 8 2 16 2s14 4 14 10-6 10-14 10h-3" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <circle cx="8" cy="23" r="2" fill="none" stroke="currentColor" strokeWidth="1.4"/>
        <circle cx="4" cy="27" r="1" fill="currentColor"/>
        {[10,16,22].map(cx=><circle key={cx} className="buddy-activity__dot" cx={cx} cy="12" r="1.7" fill="currentColor"/>)}
      </svg>}
      <span role="status" aria-live="polite">{label}</span>
    </summary>
    {open && <div className="buddy-activity__body">
      <BuddyContextTraceLoader {...binding} enabled />
    </div>}
  </details>
}
